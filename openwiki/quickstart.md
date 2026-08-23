---
type: Quickstart
title: openrouter-model-list Wiki
description: Daily-refreshed, scored lists of free OpenRouter models for different use cases. A GitHub Actions workflow fetches the OpenRouter catalog, filters free models by capability thresholds, probes each candidate, scores them by uptime/latency/capability, and publishes ranked JSON lists.
resource: https://github.com/smoochy/openrouter-model-list
tags: [openrouter, llm, models, automation, github-actions, mengram]
---

# openrouter-model-list Wiki

This repository publishes **daily-refreshed, scored lists of free OpenRouter models** for different use cases. A scheduled GitHub Actions workflow fetches the OpenRouter catalog, filters free models by capability thresholds, probes each candidate, scores them by uptime/latency/capability, and publishes ranked JSON lists.

Consumers point their `model_list_url` at the file matching their requirements; the workflow keeps it current without manual upkeep.

## Quick Links

- [Architecture Overview](architecture/overview.md) — High-level system design and data flow
- [Model Generation Workflow](workflows/generate-models.md) — End-to-end generation pipeline
- [Profiles & Thresholds](configuration/profiles.md) — Per-profile thresholds and model lists
- [GitHub Actions](operations/github-actions.md) — Scheduled workflows and manual triggers
- [Source Map](source-map.md) — Source code map linking docs to implementation

## Available Model Lists

| File | Use Case | Key Requirements |
|------|----------|------------------|
| [`models-mengram.json`](../models-mengram.json) | [mengram](https://github.com/alibaizhanov/mengram) knowledge extraction | Structured output (`response_format`), ≥40k context, ≥28B params |
| [`models-yt-summarizer.json`](../models-yt-summarizer.json) | [yt-transcript-distiller](https://github.com/smoochy/yt-transcript-distiller) YouTube transcript summarization | ≥32k context, plain text (no structured output required), ≥14B params |
| [`models-openwiki.json`](../models-openwiki.json) | [OpenWiki](https://github.com/smoochy/openwiki) agentic repo documentation | Tool-calling, ≥128k context, ≥16k output, ≥70B params |
| [`anthropic-models.json`](../anthropic-models.json) | Anthropic model selector (yt-transcript-distiller) | Current Anthropic Claude models from Anthropic API |

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
├── tests/                        # Unit tests for filters, scoring, probes, etc.
├── .github/workflows/            # GitHub Actions workflows
└── openwiki/                     # This wiki
```

## Key Concepts

- **Profile** — A named configuration (`mengram`, `yt-summarizer`, `openwiki`) with its own thresholds file and output path. See [Profiles & Thresholds](configuration/profiles.md).
- **Thresholds** — Per-profile YAML defining hard floors (parameter count), soft thresholds with buffering (context, output tokens), feature requirements (structured output, tool-calling), allowlists, and post-probe filters.
- **Candidate pool** — Free models that pass threshold filtering. If too small, `buffer_pct` relaxes toward 0 until `min_candidate_pool` is met (but `min_param_b` never relaxes).
- **Allowlist / Hardallowlist** — Model IDs that bypass certain thresholds. Allowlist models still need structured output if required; hardallowlist models bypass everything except probing/scoring.
- **Probe history** — 30-day rolling JSONL per model at `history/<model>.jsonl` recording `{timestamp, success, latency_ms}`. Used for `own_uptime` malus.
- **Scoring** — Weighted: 60% OpenRouter uptime, 30% normalized latency (capped at 5s), 10% capability (context length relative to pool max), multiplied by own uptime malus.
- **Output schema** — `generated_at`, `schema_version`, `models[]` with `id`, `score`, `context_length`, `max_output_tokens`, `uptime`, `latency_ms`, `own_uptime`, `sanity_ok`.

## Next Steps

- Read [Architecture Overview](architecture/overview.md) for a deeper dive into the system design
- See [Model Generation Workflow](workflows/generate-models.md) for the end-to-end pipeline
- Review [Profiles & Thresholds](configuration/profiles.md) to understand or customize profiles
- Check [GitHub Actions](operations/github-actions.md) for scheduled/automated runs
- Browse [Source Map](source-map.md) to trace docs to implementation

---

*This wiki is generated and maintained by [OpenWiki](https://github.com/smoochy/openwiki). Do not hand-edit generated pages; update source code/docs and let OpenWiki regenerate.*