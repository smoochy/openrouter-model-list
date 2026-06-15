"""Filter the OpenRouter model catalog down to mengram-suitable free models."""
import re
import sys

PARAM_RE = re.compile(r"(\d+(?:\.\d+)?)b", re.IGNORECASE)


def parse_param_count(model_id: str) -> float | None:
    """Extract parameter count in billions from a model id/slug.

    Returns None if no size token (e.g. "32b") is found, such as for
    "openrouter/owl-alpha".
    """
    match = PARAM_RE.search(model_id)
    if not match:
        return None
    return float(match.group(1))


def is_free(model: dict) -> bool:
    pricing = model.get("pricing", {})
    return pricing.get("prompt") == "0" and pricing.get("completion") == "0"


def supports_structured_output(model: dict) -> bool:
    params = model.get("supported_parameters", [])
    return "response_format" in params or "structured_outputs" in params


def filter_candidates(models: list[dict], thresholds: dict) -> list[dict]:
    """Filter free models by suitability thresholds.

    min_param_b is a fixed floor (never buffered) — models whose id doesn't
    encode a parseable size are excluded, unless listed in `allowlist`.
    min_context_length and min_max_output_tokens get buffer_pct applied; if
    the resulting pool (including allowlisted models) is smaller than
    min_candidate_pool, buffer_pct is reduced step-wise (by 1) toward 0. A
    missing/null max_completion_tokens is treated as unknown, not zero, and
    doesn't by itself fail the output-token check. Models in `allowlist`
    bypass min_param_b and the context/output thresholds, but still must
    pass require_structured_output (if enabled) — if they don't, they're
    excluded and a warning is logged to stderr. Models in `hardallowlist`
    bypass min_param_b, the context/output thresholds, and
    require_structured_output entirely.
    """
    free = [m for m in models if is_free(m)]

    hardallowlist = set(thresholds.get("hardallowlist", []))
    allowlist = set(thresholds.get("allowlist", []))

    hard_allowed = [m for m in free if m["id"] in hardallowlist]

    soft_allowed = []
    for m in free:
        if m["id"] not in allowlist:
            continue
        if thresholds["require_structured_output"] and not supports_structured_output(m):
            print(
                f"warning: allowlisted model {m['id']} excluded: missing structured-output support",
                file=sys.stderr,
            )
            continue
        soft_allowed.append(m)

    allowed = hard_allowed + soft_allowed
    remaining = [m for m in free if m["id"] not in hardallowlist and m["id"] not in allowlist]

    sized = []
    for m in remaining:
        params_b = parse_param_count(m["id"])
        if params_b is None or params_b < thresholds["min_param_b"]:
            continue
        sized.append(m)

    buffer_pct = thresholds["buffer_pct"]
    min_pool = thresholds["min_candidate_pool"]

    while True:
        min_ctx = thresholds["min_context_length"] * (1 + buffer_pct / 100)
        min_out = thresholds["min_max_output_tokens"] * (1 + buffer_pct / 100)

        candidates = []
        for m in sized:
            if m.get("context_length", 0) < min_ctx:
                continue
            max_out = m.get("top_provider", {}).get("max_completion_tokens")
            if max_out is not None and max_out < min_out:
                continue
            if thresholds["require_structured_output"] and not supports_structured_output(m):
                continue
            candidates.append(m)

        if len(allowed) + len(candidates) >= min_pool or buffer_pct <= 0:
            return allowed + candidates

        buffer_pct -= 1
