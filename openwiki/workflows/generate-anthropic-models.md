---
type: "Reference"
title: "Generate anthropic models"
openwiki_generated: true
verified:
  - by: openwiki/0.9.0
    at: 2026-11-14T11:53:54.399Z
sources:
  - id: openwiki-source-23fb3ed4bd0ff9d6e2dfb273
    resource: repo://scripts/generate_anthropic_models.py
generated: { by: "openwiki/0.9.0", at: "2026-11-14T11:53:54.399Z" }
---


The `generate_anthropic_models.py` script produces `anthropic-models.json` by combining live model metadata from the Anthropic API with pricing information scraped from the public Claude pricing page. The workflow follows a fail-closed design: if any model lacks a valid price after joining, the script exits with a non-zero status and writes no output, preserving the last known good output.

## Process Overview

1. **Fetch Models** – Calls `GET https://api.anthropic.com/v1/models` with pagination (`limit: 1000`, `after_id` cursor) and filters to objects where `"type": "model"`. Results are sorted by `id`.
2. **Fetch Pricing** – Retrieves `https://platform.claude.com/docs/en/about-claude/pricing` with an `Accept: text/markdown` header so the docs site returns Markdown instead of HTML.
3. **Parse Pricing Table** – Locates the table by its exact normalized header (`| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |`). Each row is parsed into five price fields (`input`, `cache_write_5m`, `cache_write_1h`, `cache_read`, `output`) in USD per million tokens. Prices must be positive and parsable; otherwise a `PricingError` is raised.
4. **Alias Resolution** – Reads `anthropic-price-aliases.yaml` to map pricing table rows (via slugified names) to API model IDs. Alias matches take precedence over direct slug matches. This covers dated model IDs (e.g. `claude-haiku-4-5-20251001`) and split pricing rows (e.g. Claude Haiku 5.5 "up to" vs "over" 100,000 tokens).
5. **Join Prices** – For each model ID from the API, attempts to find a price entry via slug or alias. If any model ID remains unmatched, the script raises `PricingError` listing the missing models — the core fail-closed case.
6. **Long‑Context Tiers** – Detects rows containing a threshold pattern like `(for prompts over N tokens)` and attaches a `pricing_long_context` object (`threshold_input_tokens` plus the same five price fields) to matching models. Tier rows that map to no API model ID are ignored.
7. **Output** – Writes the enriched model list as a bare JSON array (pretty‑printed, indent=2) to `anthropic-models.json` and appends a compact JSONL entry to `history/anthropic-models.jsonl` containing a UTC timestamp and the full model array. On failure, neither file is written or modified.

## Key Characteristics

- **Fail‑Closed** – On any pricing problem (missing table, schema change, unparseable price, zero/negative price, or unmatched model) the script prints an error to stderr, returns exit code 1, and writes nothing: `anthropic-models.json` and `history/anthropic-models.jsonl` are both left untouched. This prevents propagating corrupted pricing data to downstream consumers.
- **History** – Each successful run appends a compact JSON line to `history/anthropic-models.jsonl`, enabling audit and rollback.
- **CLI Entrypoint** – Executed via `uv run scripts/generate_anthropic_models.py` (or `python scripts/generate_anthropic_models.py`); requires the `ANTHROPIC_API_KEY` environment variable, read via `os.environ["ANTHROPIC_API_KEY"]`.
- **Deterministic Output** – Model list is sorted by `id` before joining, ensuring diff‑friendly updates.
- **Bare Array** – Output is a bare array of model objects, not the `{generated_at, schema_version, models}` wrapper used by other model lists, to avoid breaking the existing consumer (`smoochy/yt-transcript-distiller`).

## Related Files

- `scripts/generate_anthropic_models.py` – Implementation of the workflow.
- `anthropic-price-aliases.yaml` – Manual overrides for mapping pricing table rows to model IDs.
- `anthropic-models.json` – The latest known‑good output (committed to the repository).
- `history/anthropic-models.jsonl` – Append‑only log of successful generations.
- `.github/workflows/update-anthropic-models.yml` – Scheduled GitHub Actions workflow (daily 03:15 UTC) that runs the script and commits changes.
