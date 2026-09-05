---
type: Quickstart
title: Quickstart
description: Get started with the repository for consumers and contributors. Provides an overview of the model lists, how to use them, and how to run the generation locally.
tags: [openrouter, llm, models, automation, github-actions, mengram, yt-summarizer, openwiki, anthropic]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-05T08:44:41.032Z
sources:
  - id: openwiki-source-c98bff360638db4f2aa27c80
    resource: repo://.github/workflows/update-models.yml
  - id: openwiki-source-23775c3de52f3ab95a13cb8b
    resource: repo://README.md
generated: { by: "openwiki/0.5.0", at: "2026-09-05T08:44:41.032Z" }
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
├── tests/                        # Unit tests for filters, scoring, probes, etc.
├── .github/workflows/            # GitHub Actions workflows
└── openwiki/                     # This wiki
```
