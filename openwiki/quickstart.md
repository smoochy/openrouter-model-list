---
type: Quickstart
title: Quickstart
description: Get started with the repository for consumers and contributors. Provides an overview of the model lists, how to use them, and how to run the generation locally.
tags: [openrouter, llm, models, automation, github-actions, mengram, yt-summarizer, openwiki, anthropic]
verified:
  - by: openwiki/0.5.2
    at: 2026-09-19T09:07:56.091Z
sources:
  - id: openwiki-source-cc9c2e48d2340a266da2a1aa
    resource: repo://.github/workflows/update-anthropic-models.yml
  - id: openwiki-source-c98bff360638db4f2aa27c80
    resource: repo://.github/workflows/update-models.yml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
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
generated: { by: "openwiki/0.5.2", at: "2026-09-19T09:07:56.091Z" }
---

# Quickstart

This repository publishes **daily-refreshed, scored lists of free OpenRouter models** for different use cases. A scheduled GitHub Actions workflow fetches the OpenRouter catalog, filters free models by capability thresholds, probes each candidate, scores them by uptime/latency/capability, and publishes ranked JSON lists.

Consumers point their `model_list_url` at the file matching their requirements; the workflow keeps it current without manual upkeep.

## Quick Links

- [Architecture Overview](architecture/overview.md) — High-level system design and data flow
- [Model Generation Workflow](workflows/generate-models.md) — End-to-end generation pipeline
- [Profiles & Thresholds](configuration/profiles.md) — Per-profile thresholds and model lists
- [GitHub Actions](operations/github-actions.md) — Scheduled workflows and manual triggers
- [Source Map](source-map.md) — Source code map linking docs to implementation
- [Testing Overview](testing/overview.md) — Testing strategy for the repository

## Available Model Lists

| File | Use Case | Key Requirements |
|------|----------|------------------|
| [`models-mengram.json`](https://raw.githubusercontent.com/smoochy/openrouter-model-list/main/models-mengram.json) | [mengram](https://github.com/alibaizhanov/mengram) knowledge extraction | Structured output (`response_format`), ≥40k context, ≥28B params |
| [`models-yt-summarizer.json`](https://raw.githubusercontent.com/smoochy/openrouter-model-list/main/models-yt-summarizer.json) | [yt-transcript-distiller](https://github.com/smoochy/yt-transcript-distiller) YouTube transcript summarization | ≥32k context, plain text (no structured output required), ≥14B params |
| [`models-openwiki.json`](https://raw.githubusercontent.com/smoochy/openrouter-model-list/main/models-openwiki.json) | [OpenWiki](https://github.com/smoochy/openwiki) agentic repo documentation | Tool-calling, ≥128k context, ≥16k output, ≥70B params |
| [`anthropic-models.json`](https://raw.githubusercontent.com/smoochy/openrouter-model-list/main/anthropic-models.json) | Anthropic model selector (yt-transcript-distiller) | Current Anthropic Claude models from Anthropic API |

Each file is independently generated with its own `thresholds-*.yaml` configuration. Point your `model_list_url` at the file matching your use case.

## How It Works (High Level)

1. **Fetch** — Fetch all OpenRouter models, keep only free ones (`pricing.prompt == "0"` and `pricing.completion == "0"`)
2. **Filter** — Apply profile-specific thresholds from `thresholds-*.yaml` (parameter count floor, context length, output tokens, structured output, tool-calling, allowlists)
3. **Fetch endpoint stats** — Query OpenRouter's `/endpoints` API for each candidate's free endpoints, average `uptime_last_1d` and `latency_last_30m.p50`
4. **Probe** — Send a 1-token completion request to each candidate; record `{timestamp, success, latency_ms}` to `history/<model>.jsonl` (30-day rolling window)
5. **Score & rank** — Score = `(0.6×uptime + 0.3×latency_norm + 0.1×capability_norm) × own_uptime` (own uptime is a malus from 30-day probe history; new models default to 0.5 malus until 3+ probes). Sort descending and write output JSON.

## Quick Start for Consumers

Point your application's `model_list_url` at the appropriate raw GitHub URL:

```json
{
  "model_list_url": "https://raw.githubusercontent.com/smoochy/openrouter-model-list/main/models-mengram.json"
}
```

Replace `models-mengram.json` with the file matching your use case (e.g., `models-yt-summarizer.json`, `models-openwiki.json`, or `anthropic-models.json`).

The file updates daily via GitHub Actions. No manual upkeep required.

## Quick Start for Contributors

1. Clone the repo
2. Install dependencies: `uv sync` (or `pip install -e .[dev]`)
3. Set `OPENROUTER_API_KEY` environment variable
4. Run generation for a profile:
   ```bash
   uv run python scripts/generate_models.py --profile mengram
   # or
   uv run python scripts/generate_models.py --profile yt-summarizer
   # or
   uv run python scripts/generate_models.py --profile openwiki
   ```
5. Run tests: `uv run pytest`

## Repository Structure

```
├── models-mengram.json           # Output: mengram profile
├── models-yt-summarizer.json     # Output: yt-summarizer profile
├── models-openwiki.json          # Output: openwiki profile
├── anthropic-models.json         # Output: weekly Anthropic model fetch
├── thresholds-mengram.yaml       # Thresholds for mengram profile
├── thresholds-yt-summarizer.yaml # Thresholds for yt-summarizer profile
├── thresholds-openwiki.yaml      # Thresholds for openwiki profile
├── scripts/
│   ├── generate_models.py        # Main generation entry point
│   ├── filters.py                # Filter free models by thresholds
│   ├── scoring.py                # Scoring: uptime, latency, capability, own-uptime
│   ├── probe.py                  # Probe models, record 30-day history
│   ├── endpoint_stats.py         # Fetch OpenRouter endpoint uptime/latency
│   ├── openrouter_client.py      # Fetch OpenRouter model catalog
│   └── thresholds.py             # Load thresholds YAML with defaults
├── thresholds-*.yaml             # Profile thresholds (see Profiles)
├── models-*.json                 # Generated model lists (see Available Model Lists)
├── history/                      # 30-day rolling probe history (JSONL per model)
├── tests/                        # Unit tests for all pipeline stages
└── .github/workflows/            # Scheduled GitHub Actions workflows
```

## Scheduled Workflows

| Workflow | Schedule | Output Files | Notes |
|----------|----------|--------------|-------|
| `update-models.yml` | Daily 03:00 UTC | `models-mengram.json`, `models-yt-summarizer.json`, `models-openwiki.json`, `history/` | Runs all 3 profiles |
| `update-anthropic-models.yml` | Weekly Tuesday 03:15 UTC | `anthropic-models.json`, `history/anthropic-models.jsonl` | Fetches from Anthropic API |

Both workflows support `workflow_dispatch` for manual triggers and create pull requests with auto-merge attempt.

## Output Format

All three OpenRouter model lists share the same schema (`schema_version: 2`):

```json
{
  "generated_at": "2026-06-14T03:00:00Z",
  "schema_version": 2,
  "models": [
    {
      "id": "nvidia/nemotron-3-super-120b-a12b:free",
      "score": 0.8123,
      "context_length": 131072,
      "max_output_tokens": 32768,
      "uptime": 1.0,
      "latency_ms": 842,
      "own_uptime": 1.0,
      "sanity_ok": true
    }
  ]
}
```

- `uptime` — OpenRouter's aggregated `uptime_last_1d`, averaged across free endpoints (0-1). Falls back to 0.5 (neutral) if no free endpoint stats are available.
- `latency_ms` — OpenRouter's aggregated `latency_last_30m.p50`, averaged across free endpoints (ms). `null` if unavailable.
- `own_uptime` — Our 30-day rolling sanity-probe success rate (0-1), used as a malus multiplier on the score. Defaults to 0.5 for new models with fewer than 3 probes.
- `sanity_ok` — Whether today's 1-token sanity probe succeeded.
- `schema_version` increments whenever a field is added, removed, or changes meaning.

## Probe History

Each candidate model has a rolling 30-day probe history at `history/<safe-model-id>.jsonl`, one JSON object per probe (`{timestamp, success, latency_ms}`). This history feeds `own_uptime`, a malus multiplier applied to the OpenRouter-derived score. The optional `min_uptime` / `max_latency_ms` post-probe filters apply to OpenRouter's aggregated endpoint stats, not this history.

## Configuration

All tuning happens in the per-profile `thresholds-*.yaml` files:

```yaml
# Example: thresholds-mengram.yaml
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

Key fields:
- `min_param_b` — Hard floor (no buffer). Models without a parseable size token in their ID are excluded unless in `allowlist`/`hardallowlist`.
- `min_context_length` / `min_max_output_tokens` — Buffered by `buffer_pct`. If too few models pass, buffer shrinks toward 0 until `min_candidate_pool` is met.
- `require_structured_output` — Requires `response_format` or `structured_outputs` in model's `supported_parameters`.
- `require_tools` — Requires `tools` or `tool_choice` in model's `supported_parameters` (used by openwiki profile).
- `allowlist` — Model IDs that bypass `min_param_b` and context/output thresholds, but still must pass `require_structured_output` (if enabled) and `require_tools` (if enabled).
- `hardallowlist` — Model IDs that bypass all checks including `require_structured_output` and `require_tools`.

Edit the file and either wait for the next scheduled run or trigger `workflow_dispatch` manually.
