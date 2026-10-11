"""Generate anthropic-models.json: fetch models, scrape pricing, join, fail closed.

Fails closed (non-zero exit, no output written) on any of:
  - a model with no price after the join
  - the pricing table not found, or its column schema changed
  - a price of 0, or a price that doesn't parse

This keeps the last-known-good anthropic-models.json committed whenever the
scrape breaks, instead of publishing a file with missing or zeroed prices.
"""
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
import yaml

REPO_ROOT = Path(__file__).parent.parent
OUTPUT_PATH = REPO_ROOT / "anthropic-models.json"
HISTORY_PATH = REPO_ROOT / "history" / "anthropic-models.jsonl"
ALIASES_PATH = REPO_ROOT / "anthropic-price-aliases.yaml"

MODELS_API_URL = "https://api.anthropic.com/v1/models"
PRICING_URL = "https://platform.claude.com/docs/en/about-claude/pricing"

# The documented table header, matched with whitespace normalized so markdown
# column-padding doesn't matter.
TABLE_HEADER = (
    "| Model | Base input tokens | 5m cache writes | 1h cache writes "
    "| Cache hits and refreshes | Output tokens |"
)
PRICE_FIELDS = ["input", "cache_write_5m", "cache_write_1h", "cache_read", "output"]

PRICE_RE = re.compile(r"\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*MTok")


class PricingError(RuntimeError):
    """The pricing page couldn't be parsed, or a price is missing/invalid."""


def _normalize_ws(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip())


def fetch_models(api_key: str) -> list[dict]:
    """Fetch every page of /v1/models, filtered to type == 'model'."""
    models: list[dict] = []
    after_id = None
    with httpx.Client(timeout=30) as client:
        while True:
            params = {"limit": 1000}
            if after_id:
                params["after_id"] = after_id
            resp = client.get(
                MODELS_API_URL,
                headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
                params=params,
            )
            resp.raise_for_status()
            data = resp.json()
            models.extend(m for m in data.get("data", []) if m.get("type") == "model")
            if not data.get("has_more"):
                break
            after_id = data.get("last_id")
            if not after_id:
                break
    models.sort(key=lambda m: m["id"])
    return models


def fetch_pricing_page(url: str = PRICING_URL) -> str:
    # Without this header the docs site answers with the HTML page, which has no markdown table.
    resp = httpx.get(url, headers={"Accept": "text/markdown"}, timeout=30, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def slugify(name: str) -> str:
    """'Claude Opus 5.5' -> 'claude-opus-5-5'."""
    slug = name.strip().lower()
    slug = re.sub(r"[.\s]+", "-", slug)
    slug = re.sub(r"[^a-z0-9-]", "", slug)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def parse_price(raw: str, *, model_name: str, column: str) -> float:
    """Parse a cell like '$0.25 / MTok<sup>1</sup>' into 0.25. Fails closed on anything else."""
    match = PRICE_RE.search(raw)
    if not match:
        raise PricingError(f"unparseable price for {model_name!r} column {column!r}: {raw!r}")
    value = float(match.group(1))
    if value <= 0:
        raise PricingError(f"zero/invalid price for {model_name!r} column {column!r}: {raw!r}")
    return value


def parse_pricing_table(markdown: str) -> dict[str, dict[str, float]]:
    """Parse the pricing markdown table into {page_model_name: {input, cache_write_5m, ...}}.

    Raises PricingError if the documented header isn't found, a row's column
    count doesn't match, or any price cell fails to parse.
    """
    lines = markdown.splitlines()
    header_idx = None
    for i, line in enumerate(lines):
        if _normalize_ws(line) == TABLE_HEADER:
            header_idx = i
            break
    if header_idx is None:
        raise PricingError(f"pricing table header not found (expected: {TABLE_HEADER!r})")

    table: dict[str, dict[str, float]] = {}
    for line in lines[header_idx + 2:]:  # +2 skips the '|---|---|...' alignment row
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) != 6:
            raise PricingError(f"pricing row has {len(cells)} columns, expected 6: {line!r}")
        name, *prices = cells
        table[name] = {
            field: parse_price(price, model_name=name, column=field)
            for field, price in zip(PRICE_FIELDS, prices)
        }
    if not table:
        raise PricingError("pricing table header found but it has no rows")
    return table


def load_aliases(path: Path = ALIASES_PATH) -> dict[str, list[str]]:
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("aliases", {}) or {}


def join_prices(
    model_ids: list[str],
    pricing_table: dict[str, dict[str, float]],
    aliases: dict[str, list[str]],
) -> dict[str, dict[str, float]]:
    """Join pricing-page rows onto API model ids by slugify, falling back to the alias table.

    Alias entries take priority over a direct slug match. Raises PricingError
    listing every model id left unpriced - this is the core fail-closed case:
    a silently unpriced model corrupts every savedCents figure downstream.
    """
    priced: dict[str, dict[str, float]] = {}
    for page_name, prices in pricing_table.items():
        slug = slugify(page_name)
        if slug in aliases:
            for model_id in aliases[slug]:
                priced.setdefault(model_id, prices)
        elif slug in model_ids:
            priced.setdefault(slug, prices)

    missing = [m for m in model_ids if m not in priced]
    if missing:
        raise PricingError(f"no price found for model id(s): {missing}")
    return priced


def generate(
    *,
    api_key: str,
    fetch_models_fn,
    fetch_pricing_fn,
    aliases: dict[str, list[str]],
    now: str,
    output_path: Path = OUTPUT_PATH,
    history_path: Path = HISTORY_PATH,
) -> list[dict]:
    models = fetch_models_fn(api_key)
    pricing_table = parse_pricing_table(fetch_pricing_fn())
    prices = join_prices([m["id"] for m in models], pricing_table, aliases)

    for model in models:
        model["pricing"] = prices[model["id"]]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(models, f, indent=2)
        f.write("\n")

    history_path.parent.mkdir(parents=True, exist_ok=True)
    entry = {"timestamp": now, "models": models}
    with open(history_path, "a") as f:
        f.write(json.dumps(entry, separators=(",", ":")) + "\n")

    return models


def main() -> int:
    api_key = os.environ["ANTHROPIC_API_KEY"]
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    aliases = load_aliases()
    try:
        generate(
            api_key=api_key,
            fetch_models_fn=fetch_models,
            fetch_pricing_fn=fetch_pricing_page,
            aliases=aliases,
            now=now,
        )
    except PricingError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
