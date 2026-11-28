---
type: Configuration
title: Profiles & Thresholds Configuration
description: "Per-profile threshold configuration for the three model generation profiles (mengram, yt-summarizer, openwiki). Documents the shared threshold schema, defaults, profile-specific values, allowlist/hardallowlist behavior, and candidate-pool relaxation."
tags: ["configuration", "profiles", "thresholds", "mengram", "yt-summarizer", "openwiki"]
sources:
  - id: openwiki-source-d62a846da6fa0f2e25b94fa4
    resource: repo://scripts/filters.py
  - id: openwiki-source-a53118abdd8a4e93bbeab156
    resource: repo://scripts/thresholds.py
  - id: openwiki-source-efe52f802136ea4316cd0f90
    resource: repo://thresholds-mengram.yaml
  - id: openwiki-source-f0ff834cf56ce15024d0ede4
    resource: repo://thresholds-openwiki.yaml
  - id: openwiki-source-95e171e2045483fa0c961258
    resource: repo://thresholds-yt-summarizer.yaml
generated: { by: "openwiki/0.9.0", at: "2026-11-28T13:48:21.508Z" }
verified:
  - by: openwiki/0.9.0
    at: 2026-11-28T13:48:21.508Z
---

# Profiles & Thresholds Configuration

This repository uses **profiles** to generate different model lists for different use cases. Each profile has:
- A `thresholds-<profile>.yaml` file defining filtering criteria
- An output `models-<profile>.json` file
- A profile entry in `scripts/generate_models.py::PROFILES`

## Profile Definitions

```python
# scripts/generate_models.py::PROFILES
PROFILES = {
    "mengram": {
        "thresholds_path": REPO_ROOT / "thresholds-mengram.yaml",
        "output_path": REPO_ROOT / "models-mengram.json",
    },
    "yt-summarizer": {
        "thresholds_path": REPO_ROOT / "thresholds-yt-summarizer.yaml",
        "output_path": REPO_ROOT / "models-yt-summarizer.json",
    },
    "openwiki": {
        "thresholds_path": REPO_ROOT / "thresholds-openwiki.yaml",
        "output_path": REPO_ROOT / "models-openwiki.json",
    },
}
```

Run a specific profile:
```bash
python scripts/generate_models.py --profile mengram
python scripts/generate_models.py --profile yt-summarizer
python scripts/generate_models.py --profile openwiki
```

## Threshold Schema

All thresholds files share the same schema. `scripts/thresholds.py::load_thresholds` loads the YAML and falls back to `DEFAULTS` for missing keys:

```yaml
# Hard floor — no buffer applied. Models whose parameter count can't be
# determined from their OpenRouter id are excluded unless in allowlist
# or hardallowlist.
min_param_b: <int>

# Soft thresholds — buffer_pct is added on top before filtering.
min_context_length: <int>
min_max_output_tokens: <int>
buffer_pct: <int>          # percentage buffer, relaxed toward 0 if pool too small

# Feature requirements
require_structured_output: <bool>  # needs response_format or structured_outputs in supported_parameters
require_tools: <bool>              # needs tools or tool_choice in supported_parameters

# Post-probe filters (using OpenRouter aggregated endpoint stats)
min_uptime: <float|null>           # e.g., 0.95; null/empty to disable
max_latency_ms: <int|null>         # e.g., 3000; null/empty to disable

# If buffering shrinks the candidate pool below this, relax buffer_pct
# step-wise toward 0 until pool is large enough (min_param_b stays fixed).
min_candidate_pool: <int>

# Model IDs always included, bypassing min_param_b and context/output thresholds.
# Still must pass require_structured_output (if enabled) — excluded with warning if not.
# Still must pass require_tools (if enabled). Still probed and scored normally.
allowlist: [<model_id>, ...]

# Model IDs always included, bypassing min_param_b, context/output thresholds,
# AND require_structured_output and require_tools entirely. Still probed
# and scored normally.
hardallowlist: [<model_id>, ...]
```

**Defaults** (from `scripts/thresholds.py::DEFAULTS`):
```python
{
    "min_param_b": 28,
    "min_context_length": 40000,
    "min_max_output_tokens": 8000,
    "buffer_pct": 5,
    "require_structured_output": True,
    "require_tools": False,
    "min_uptime": None,
    "max_latency_ms": None,
    "min_candidate_pool": 3,
    "allowlist": [],
    "hardallowlist": [],
}
```

All eleven keys are applied for every profile even if a YAML omits them; missing keys inherit the defaults above.

## Profile: mengram

**Output:** `models-mengram.json`  
**Use case:** [mengram](https://github.com/alibaizhanov/mengram) knowledge extraction  
**Requirements:** Structured output, large context, large output, substantial model size

```yaml
# thresholds-mengram.yaml
min_param_b: 28
min_context_length: 40000
min_max_output_tokens: 8000
buffer_pct: 5
require_structured_output: true
require_tools: false
min_uptime:
max_latency_ms:
min_candidate_pool: 3
allowlist:
  - openrouter/owl-alpha
hardallowlist: []
```

**Key points:**
- `min_param_b: 28` — Hard floor, no buffer. Models without parseable size (e.g., `openrouter/owl-alpha`) excluded unless allowlisted.
- `require_structured_output: true` — Must have `response_format` or `structured_outputs` in `supported_parameters`.
- `allowlist: [openrouter/owl-alpha]` — Bypasses param floor and context/output thresholds, but still needs structured output (excluded with warning if missing).
- `min_candidate_pool: 3` — If fewer than 3 candidates after buffering, relax `buffer_pct` toward 0.

<!-- openwiki: broken internal link [../thresholds-mengram.yaml] file "../thresholds-mengram.yaml" does not exist. Fix the href or restore the target, then delete this comment. -->
**Source:** [`thresholds-mengram.yaml`](../thresholds-mengram.yaml)

## Profile: yt-summarizer

**Output:** `models-yt-summarizer.json`  
**Use case:** [yt-transcript-distiller](https://github.com/smoochy/yt-transcript-distiller) — YouTube transcript summarization  
**Requirements:** Large context for long transcripts, plain text output (no structured output needed)

```yaml
# thresholds-yt-summarizer.yaml
min_param_b: 14
min_context_length: 32000
min_max_output_tokens: 2000
buffer_pct: 5
require_structured_output: false
require_tools: false
min_uptime:
max_latency_ms:
min_candidate_pool: 3
allowlist:
  - meta-llama/llama-4-scout:free
  - openrouter/owl-alpha
  - qwen/qwen3-32b:free
hardallowlist: []
```

**Key points:**
- Lower `min_param_b: 14` — Smaller models acceptable for summarization.
- `require_structured_output: false` — Plain text generation is fine.
- Allowlist includes 3 models that may not meet param/context thresholds but are known-good for summarization.

<!-- openwiki: broken internal link [../thresholds-yt-summarizer.yaml] file "../thresholds-yt-summarizer.yaml" does not exist. Fix the href or restore the target, then delete this comment. -->
**Source:** [`thresholds-yt-summarizer.yaml`](../thresholds-yt-summarizer.yaml)

## Profile: openwiki

**Output:** `models-openwiki.json`  
**Use case:** [OpenWiki](https://github.com/smoochy/openwiki) agentic repository documentation generator  
**Requirements:** Tool-calling for agent loop, very large context (reads many files per synthesis), high output ceiling (writes whole wiki pages)

```yaml
# thresholds-openwiki.yaml
min_param_b: 70
min_context_length: 128000
min_max_output_tokens: 16000
buffer_pct: 5
require_structured_output: false
require_tools: true
min_uptime:
max_latency_ms:
min_candidate_pool: 2
allowlist:
  - thinkingmachines/inkling:free
  - poolside/laguna-s-2.1:free
  - cohere/north-mini-code:free
  - nvidia/nemotron-3.5-lightning:free
  # Free tool-capable models no openwiki run has tried yet.
  - google/gemma-4-31b-it:free
  - google/gemma-4-26b-a4b-it:free
  - nvidia/nemotron-3.5-super-vl:free
hardallowlist: []
```

**Key points:**
- Highest `min_param_b: 70` — Needs large models for complex agentic tasks.
- Highest `min_context_length: 128000` — Reads many source files per step.
- Highest `min_max_output_tokens: 16000` — Writes entire wiki pages in one shot.
- `require_tools: true` — Must support `tools`/`tool_choice` for agent loop.
- `require_structured_output: false` — Tool-calling is the key feature, not structured output.
- Smallest `min_candidate_pool: 2` — Fewer models expected to meet this bar.
- `allowlist` includes 7 free models that don't encode size in their ID (so would be dropped by `min_param_b: 70`) but meet context/output/tool thresholds per catalog metadata. These diversify providers beyond just Nvidia Nemotron models. The list includes `thinkingmachines/inkling:free`, `poolside/laguna-s-2.1:free`, `cohere/north-mini-code:free`, `nvidia/nemotron-3.5-lightning:free`, plus `google/gemma-4-31b-it:free`, `google/gemma-4-26b-a4b-it:free`, and `nvidia/nemotron-3.5-super-vl:free` — free tool-capable models no openwiki run has tried yet.

<!-- openwiki: broken internal link [../thresholds-openwiki.yaml] file "../thresholds-openwiki.yaml" does not exist. Fix the href or restore the target, then delete this comment. -->
**Source:** [`thresholds-openwiki.yaml`](../thresholds-openwiki.yaml)

## Comparison Table

| Threshold | mengram | yt-summarizer | openwiki |
|-----------|---------|---------------|----------|
| `min_param_b` | 28 | 14 | **70** |
| `min_context_length` | 40,000 | 32,000 | **128,000** |
| `min_max_output_tokens` | 8,000 | 2,000 | **16,000** |
| `buffer_pct` | 5 | 5 | 5 |
| `require_structured_output` | **true** | false | false |
| `require_tools` | false | false | **true** |
| `min_candidate_pool` | 3 | 3 | 2 |
| `allowlist` | owl-alpha | llama-4-scout, owl-alpha, qwen3-32b | inkling, laguna-s-2.1, north-mini-code, nemotron-3.5-lightning |
| `hardallowlist` | (none) | (none) | (none) |

## Filter Pipeline & Candidate-Pool Relaxation

`scripts/filters.py::filter_candidates` applies thresholds in this order:

1. **Free-only** — models with non-zero prompt or completion pricing are dropped.
2. **Hardallowlist** — models listed there bypass `min_param_b`, context/output thresholds, `require_structured_output`, and `require_tools`. No warning if they fail feature checks.
3. **Allowlist** — models listed there bypass `min_param_b` and context/output thresholds, but still must pass `require_structured_output` (warning to stderr if not) and `require_tools` (warning to stderr if not).
4. **Parameter floor** — remaining models must parse a size token (`N[bB]`) from their ID and meet `min_param_b`. `min_param_b` is a fixed floor: never buffered, never relaxed toward 0.
5. **Soft thresholds with buffer** — `min_context_length` and `min_max_output_tokens` are multiplied by `(1 + buffer_pct / 100)`. A missing/null `max_completion_tokens` is treated as unknown, not zero, and does not by itself fail the output-token check. Remaining models must also pass `require_structured_output` and `require_tools`.
6. **Pool relaxation** — if `len(allowlisted) + len(candidates) < min_candidate_pool`, `buffer_pct` is reduced by 1 (toward 0) and the soft-threshold check repeats. `min_param_b` stays fixed throughout.
7. **Post-probe filters** — `min_uptime` / `max_latency_ms` are applied after probing, using OpenRouter aggregated endpoint stats (see [Model Generation Workflow](../workflows/generate-models.md)).

`scripts/filters.py::parse_param_count` extracts parameter count in billions from the model ID:
- `"qwen/qwen3-32b:free"` → 32.0
- `"google/gemma-4-31b-it:free"` → 31.0
- `"meta-llama/llama-4-scout:free"` → None (no `Nb` pattern)
- `"openrouter/owl-alpha"` → None

Models with `None` param count are excluded by `min_param_b` unless in `allowlist` or `hardallowlist`.

## Allowlist vs Hardallowlist

| Aspect | `allowlist` | `hardallowlist` |
|--------|-------------|-----------------|
| Bypasses `min_param_b` | ✅ | ✅ |
| Bypasses context/output thresholds | ✅ | ✅ |
| Bypasses `require_structured_output` | ❌ (still required) | ✅ |
| Bypasses `require_tools` | ❌ (still required) | ✅ |
| Warning if excluded | ✅ (logs to stderr) | ❌ |
| Still probed & scored | ✅ | ✅ |

**Use `allowlist`** for models known to be suitable that don't encode size in their ID but DO support required features.

**Use `hardallowlist`** for models known to be suitable that don't report required features via the catalog API (e.g., structured output support not advertised but actually works).

## Post-Probe Filters

Currently **disabled** in all profiles (both values empty):

```yaml
min_uptime:
max_latency_ms:
```

If enabled, these filter AFTER probing using OpenRouter's aggregated endpoint stats:
- `min_uptime: 0.95` → exclude models with <95% uptime (averaged across free endpoints)
- `max_latency_ms: 3000` → exclude models with p50 latency >3s

These would further reduce the candidate pool after scoring.

## Adding a New Profile

1. Create `thresholds-<name>.yaml` with desired thresholds
2. Add entry to `PROFILES` dict in `scripts/generate_models.py`:
   ```python
   "new-profile": {
       "thresholds_path": REPO_ROOT / "thresholds-new-profile.yaml",
       "output_path": REPO_ROOT / "models-new-profile.json",
   },
   ```
3. Run locally to test: `python scripts/generate_models.py --profile new-profile`

## Related Pages

- [Model Generation Workflow](../workflows/generate-models.md) — How thresholds are applied in the pipeline
- [Architecture Overview](../architecture/overview.md) — High-level system design
- [Source Map](../source-map.md) — File-to-concept mapping
