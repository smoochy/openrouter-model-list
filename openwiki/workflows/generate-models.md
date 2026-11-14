---
type: Workflow
title: Model Generation Workflow
description: "End-to-end per-profile model generation pipeline: entry point in generate_models.py, OpenRouter catalog fetch, free model filtering, threshold application, endpoint stats fetch, sanity probing, 30-day history read, post-probe filters, weighted scoring, and output JSON writing."
resource: /openwiki/workflows/generate-models.md
tags: ["workflow", "generation", "pipeline", "filters", "scoring", "probing"]
sources:
  - id: openwiki-source-678af2bf704a9375a5423843
    resource: repo://scripts/endpoint_stats.py
  - id: openwiki-source-d62a846da6fa0f2e25b94fa4
    resource: repo://scripts/filters.py
  - id: openwiki-source-d8b85b547cd70ae9d19deeea
    resource: repo://scripts/generate_models.py
  - id: openwiki-source-11968c67bba9651b9ac1c4e5
    resource: repo://scripts/probe.py
  - id: openwiki-source-f3047b157e385d6464b26dbd
    resource: repo://scripts/scoring.py
  - id: openwiki-source-efe52f802136ea4316cd0f90
    resource: repo://thresholds-mengram.yaml
  - id: openwiki-source-f0ff834cf56ce15024d0ede4
    resource: repo://thresholds-openwiki.yaml
  - id: openwiki-source-95e171e2045483fa0c961258
    resource: repo://thresholds-yt-summarizer.yaml
verified:
  - by: openwiki/0.9.0
    at: 2026-11-14T11:53:54.399Z
generated: { by: "openwiki/0.9.0", at: "2026-11-14T11:53:54.399Z" }
---

# Model Generation Workflow

This page documents the **per-profile model generation pipeline** executed by `scripts/generate_models.py`. Each profile (`mengram`, `yt-summarizer`, `openwiki`) runs the same pipeline with different thresholds from `thresholds-*.yaml`.

## Pipeline Overview

```mermaid
sequenceDiagram
    participant GH as GitHub Actions
    participant GM as generate_models.py
    participant OR as OpenRouter API
    participant ES as endpoint_stats.py
    participant PR as probe.py
    participant SC as scoring.py
    participant FS as File System

    GH->>GM: python generate_models.py --profile mengram
    GM->>OR: GET /models (fetch catalog)
    OR-->>GM: All models
    GM->>GM: Filter free models (is_free)
    GM->>GM: Apply thresholds (filter_candidates)
    GM->>ES: fetch_endpoint_stats for each candidate
    ES->>OR: GET /models/{id}/endpoints
    OR-->>ES: Endpoint stats
    ES-->>GM: avg uptime, latency_p50
    GM->>PR: probe_model (1-token completion)
    PR->>OR: POST /chat/completions (ping)
    OR-->>PR: success/latency
    PR->>FS: Append to history/<model>.jsonl
    PR-->>GM: sanity result
    GM->>PR: read_history (30-day window)
    PR-->>GM: probe history
    GM->>GM: compute own_uptime
    GM->>SC: passes_post_probe_filters
    SC-->>GM: pass/fail
    GM->>SC: compute_score
    SC-->>GM: score
    GM->>FS: Write models-<profile>.json
```

**Caption:** Sequence diagram of the per-profile generation pipeline.

## Step-by-Step Walkthrough

### 1. Entry Point: `generate_models.py`

```python
# Called via CLI: python scripts/generate_models.py --profile <name>
profile = resolve_profile(args.profile)  # {"thresholds_path", "output_path"}
generate(
    thresholds_path=profile["thresholds_path"],
    history_dir=HISTORY_DIR,
    output_path=profile["output_path"],
    fetch_models_fn=fetch_models,
    fetch_endpoint_stats_fn=fetch_endpoint_stats,
    probe_model_fn=probe_model,
    llm_client=OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1"),
    now=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
)
```

Profiles are defined in `PROFILES`:
- `mengram` → `thresholds-mengram.yaml`, `models-mengram.json`
- `yt-summarizer` → `thresholds-yt-summarizer.yaml`, `models-yt-summarizer.json`
- `openwiki` → `thresholds-openwiki.yaml`, `models-openwiki.json`

An unknown profile raises `ValueError`. The CLI defaults to `mengram`. `OPENROUTER_API_KEY` is read from the environment (fatal if missing in `main()`).

**Source:** [`scripts/generate_models.py`](../../scripts/generate_models.py) lines 37-140

### 2. Fetch OpenRouter Catalog: `openrouter_client.py::fetch_models`

```python
def fetch_models(api_key: str) -> list[dict]:
    response = httpx.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]
```

Returns full model catalog with fields: `id`, `name`, `pricing`, `context_length`, `top_provider.max_completion_tokens`, `supported_parameters`, etc. HTTP errors propagate (raises).

**Source:** [`scripts/openrouter_client.py`](../../scripts/openrouter_client.py)

### 3. Filter Free Models: `filters.py::is_free`

```python
def is_free(model: dict) -> bool:
    pricing = model.get("pricing", {})
    return pricing.get("prompt") == "0" and pricing.get("completion") == "0"
```

A model is free only if **both** `pricing.prompt` and `pricing.completion` are exactly the string `"0"`.

**Source:** [`scripts/filters.py`](../../scripts/filters.py) lines 20-22

### 4. Apply Thresholds: `filters.py::filter_candidates`

This is the core filtering logic. Order of operations:

1. **Free filter** — Only models passing `is_free` proceed.
2. **Separate hardallowlist** — Models in `hardallowlist` bypass ALL thresholds (`min_param_b`, context/output, feature requirements). Still probed and scored normally.
3. **Process allowlist** — Models in `allowlist` bypass `min_param_b` and context/output thresholds, but MUST pass `require_structured_output` and `require_tools` (if enabled); excluded with a warning if not.
4. **Filter remaining by `min_param_b`** — Parse param count from model ID (e.g., `qwen/qwen3-32b:free` → 32). Models without parseable size are excluded; `min_param_b` is a fixed floor, never buffered.
5. **Apply buffered context/output thresholds** — `min_context_length * (1 + buffer_pct/100)`, `min_max_output_tokens * (1 + buffer_pct/100)`. Missing/null `max_completion_tokens` is treated as unknown, not zero.
6. **Apply feature requirements** — `require_structured_output` checks `supported_parameters` for `response_format` or `structured_outputs`; `require_tools` checks for `tools` or `tool_choice`.
7. **Relax buffer** — If `len(allowed) + len(candidates) < min_candidate_pool`, decrement `buffer_pct` by 1 and retry (down to 0). `min_param_b` NEVER relaxes.
8. **Return** `allowed + candidates`

**Source:** [`scripts/filters.py`](../../scripts/filters.py) lines 35-107

### 5. Fetch Endpoint Stats: `endpoint_stats.py::fetch_endpoint_stats`

```python
# For each candidate model:
url = f"https://openrouter.ai/api/v1/models/{model_id}/endpoints"
# GET with Authorization header
# Filter endpoints where pricing.prompt == "0" and pricing.completion == "0"
# Average uptime_last_1d (divide by 100) and latency_last_30m.p50 across free endpoints
```

Returns `{"uptime": float, "latency_p50": float|None}` or `None` if the request fails or no free endpoints are present. `uptime_last_1d` is a percentage divided by 100.

**Fallback:** If `None`, use `NEUTRAL_UPTIME = 0.5` and `latency_p50 = None`, with a warning logged to stderr.

**Source:** [`scripts/endpoint_stats.py`](../../scripts/endpoint_stats.py)

### 6. Probe Candidate: `probe.py::probe_model`

```python
def probe_model(client, model_id: str) -> dict:
    start = time.monotonic()
    try:
        client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        success = True
    except Exception:
        success = False
    latency_ms = int((time.monotonic() - start) * 1000)
    return {"success": success, "latency_ms": latency_ms}
```

Sends a minimal 1-token completion via the OpenAI client pointing at OpenRouter. On failure, logs a warning to stderr and sets `sanity_ok: false` in output. Probes happen even for hardallowlisted models.

**Source:** [`scripts/probe.py`](../../scripts/probe.py) lines 11-24

### 7. Record Probe History: `probe.py::record_probe`

```python
def record_probe(history_dir: Path, model_id: str, result: dict, timestamp: str):
    # Append to history/<safe_model_id>.jsonl
    # Trim entries older than 30 days (HISTORY_WINDOW_DAYS)
```

History file: `history/google__gemma-4-31b-it__free.jsonl` (slashes/colons → `__`)

Each line: `{"timestamp": "2026-01-15T03:00:00Z", "success": true, "latency_ms": 1234}`

Entries older than `HISTORY_WINDOW_DAYS` (30 days) are trimmed on every write.

**Source:** [`scripts/probe.py`](../../scripts/probe.py) lines 27-41

### 8. Compute Own Uptime: `scoring.py::compute_uptime`

```python
def compute_uptime(history: list[dict]) -> float:
    if len(history) < MIN_SAMPLES_FOR_UPTIME:  # 3
        return NEUTRAL_UPTIME  # 0.5
    successes = sum(1 for e in history if e["success"])
    return successes / len(history)
```

- **<3 probes** → neutral `0.5` (new models not penalized)
- **≥3 probes** → actual success rate (0.0–1.0)
- Used as multiplicative malus on final score

**Source:** [`scripts/scoring.py`](../../scripts/scoring.py) lines 12-16

### 9. Post-Probe Filters: `scoring.py::passes_post_probe_filters`

```python
def passes_post_probe_filters(uptime: float, latency_p50: float|None, thresholds: dict) -> bool:
    if thresholds.get("min_uptime") is not None and uptime < thresholds["min_uptime"]:
        return False
    if thresholds.get("max_latency_ms") is not None and latency_p50 is not None and latency_p50 > thresholds["max_latency_ms"]:
        return False
    return True
```

Optional filters applied **after** probing. Currently unused (both `min_uptime` and `max_latency_ms` are empty in all thresholds files). Models that fail are skipped entirely (not scored, not written).

**Source:** [`scripts/scoring.py`](../../scripts/scoring.py) lines 18-27

### 10. Score Candidates: `scoring.py::compute_score`

```python
# Weights
UPTIME_WEIGHT = 0.6
LATENCY_WEIGHT = 0.3
CAPABILITY_WEIGHT = 0.1
LATENCY_CAP_MS = 5000

def compute_score(model, or_uptime, or_latency_p50, max_context, own_uptime):
    latency_norm = 0.0 if or_latency_p50 is None else max(0.0, 1 - or_latency_p50 / LATENCY_CAP_MS)
    capability_norm = model["context_length"] / max_context if max_context > 0 else 0.0
    base = (UPTIME_WEIGHT * or_uptime + LATENCY_WEIGHT * latency_norm + CAPABILITY_WEIGHT * capability_norm)
    return base * own_uptime
```

**Score components:**
- **60% OpenRouter uptime** — Aggregated `uptime_last_1d` across free endpoints
- **30% Normalized latency** — `1 - (p50_latency / 5000ms)`, so <5s latency contributes positively
- **10% Capability** — Relative context length within candidate pool
- **Own uptime malus** — Multiplies base score by 30-day probe success rate (0.5 neutral for new models)

**Source:** [`scripts/scoring.py`](../../scripts/scoring.py) lines 39-66

### 11. Sort & Write Output: `generate_models.py`

```python
scored.sort(key=lambda m: m["score"], reverse=True)

output = {
    "generated_at": now,
    "schema_version": SCHEMA_VERSION,  # 2
    "models": scored,
}

with open(output_path, "w") as f:
    json.dump(output, f, indent=2)
    f.write("\n")
```

Output schema (v2):
```json
{
  "generated_at": "2026-01-15T03:00:00Z",
  "schema_version": 2,
  "models": [
    {
      "id": "google/gemma-4-31b-it:free",
      "score": 0.5234,
      "context_length": 32768,
      "max_output_tokens": 8192,
      "uptime": 0.98,
      "latency_ms": 1200,
      "own_uptime": 0.5,
      "sanity_ok": true
    }
  ]
}
```

**Source:** [`scripts/generate_models.py`](../../scripts/generate_models.py) lines 94-100

## Profile Differences

| Aspect | mengram | yt-summarizer | openwiki |
|--------|---------|---------------|----------|
| `min_param_b` | 28 | 14 | 70 |
| `min_context_length` | 40,000 | 32,000 | 128,000 |
| `min_max_output_tokens` | 8,000 | 2,000 | 16,000 |
| `require_structured_output` | true | false | false |
| `require_tools` | false | false | true |
| `buffer_pct` | 5 | 5 | 5 |
| `min_candidate_pool` | 3 | 3 | 2 |
| `allowlist` | `openrouter/owl-alpha` | `meta-llama/llama-4-scout:free`, `openrouter/owl-alpha`, `qwen/qwen3-32b:free` | `thinkingmachines/inkling:free`, `poolside/laguna-s-2.1:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3.5-lightning:free`, `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free`, `nvidia/nemotron-3.5-super-vl:free` |
| `hardallowlist` | (empty) | (empty) | (empty) |

See [Profiles & Thresholds](../configuration/profiles.md) for full threshold details.

## Error Handling & Warnings

- **No free endpoint stats** → Log warning, use neutral uptime (0.5), no latency score
- **Probe fails** → Log warning, record failure to history, `sanity_ok: false` in output
- **Allowlisted model missing structured output** → Log warning, exclude from candidates
- **Allowlisted model missing tool-calling** → Log warning, exclude from candidates
- **HTTP errors (catalog)** → `fetch_models` raises on failure
- **HTTP errors (endpoint stats)** → `fetch_endpoint_stats` returns `None`; neutral values used

All warnings printed to stderr (visible in GitHub Actions logs).

## Running Locally

```bash
# Install deps
uv sync  # or pip install -e .[dev]

# Set API key
export OPENROUTER_API_KEY="sk-or-..."

# Run for a profile
uv run python scripts/generate_models.py --profile mengram
uv run python scripts/generate_models.py --profile yt-summarizer
uv run python scripts/generate_models.py --profile openwiki

# Run tests
uv run pytest
```

## Related Pages

- [Architecture Overview](../architecture/overview.md) — High-level system design
- [Profiles & Thresholds](../configuration/profiles.md) — Threshold configuration details
- [GitHub Actions](../operations/github-actions.md) — Scheduled workflow execution
- [Source Map](../source-map.md) — File-to-concept mapping
