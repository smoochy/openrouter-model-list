---
type: Reference
title: Source Map
description: "Maps repository documentation to implementation source files, key symbols, tests, output artifacts, and data files so contributors can navigate from docs to code and back."
tags: [reference, source-map, architecture, workflows, configuration, operations]
sources:
  - id: openwiki-source-e082dc1d961398caa2e27f47
    resource: repo://.github/workflows/openwiki-update.yaml
  - id: openwiki-source-cc9c2e48d2340a266da2a1aa
    resource: repo://.github/workflows/update-anthropic-models.yml
  - id: openwiki-source-c98bff360638db4f2aa27c80
    resource: repo://.github/workflows/update-models.yml
  - id: openwiki-source-4dab8009ad11ecde31efe1bd
    resource: repo://anthropic-models.json
  - id: openwiki-source-8c8637d5c45f55218d1c3e2c
    resource: repo://anthropic-price-aliases.yaml
  - id: openwiki-source-7d5f69b071aa52e8ef9e8a4f
    resource: repo://history/nvidia__nemotron-3.5-lightning__free.jsonl
  - id: openwiki-source-7e04a6f89135965340679759
    resource: repo://models-mengram.json
  - id: openwiki-source-485cf2e58e69a12dcb5aa656
    resource: repo://models-openwiki.json
  - id: openwiki-source-9b20ebe8f326f32ddab0d3ca
    resource: repo://models-yt-summarizer.json
  - id: openwiki-source-05ccef8d4cf1698187f20464
    resource: repo://pyproject.toml
  - id: openwiki-source-678af2bf704a9375a5423843
    resource: repo://scripts/endpoint_stats.py
  - id: openwiki-source-d62a846da6fa0f2e25b94fa4
    resource: repo://scripts/filters.py
  - id: openwiki-source-23fb3ed4bd0ff9d6e2dfb273
    resource: repo://scripts/generate_anthropic_models.py
  - id: openwiki-source-d8b85b547cd70ae9d19deeea
    resource: repo://scripts/generate_models.py
  - id: openwiki-source-f53424678e8568c6002e83f4
    resource: repo://scripts/openrouter_client.py
  - id: openwiki-source-11968c67bba9651b9ac1c4e5
    resource: repo://scripts/probe.py
  - id: openwiki-source-f3047b157e385d6464b26dbd
    resource: repo://scripts/scoring.py
  - id: openwiki-source-a53118abdd8a4e93bbeab156
    resource: repo://scripts/thresholds.py
  - id: openwiki-source-7995d21acf8700126d80f174
    resource: repo://tests/test_endpoint_stats.py
  - id: openwiki-source-11756fcad787f7e58e819924
    resource: repo://tests/test_filters.py
  - id: openwiki-source-be6bab7433c898a5f9d67d2a
    resource: repo://tests/test_generate_models.py
  - id: openwiki-source-b7007795c3a21049a8bd9592
    resource: repo://tests/test_openrouter_client.py
  - id: openwiki-source-f458453933e262b3bc658561
    resource: repo://tests/test_probe.py
  - id: openwiki-source-0e65ceef13e4b6b565a83f82
    resource: repo://tests/test_scoring.py
  - id: openwiki-source-3408766c6be85dd20e112827
    resource: repo://tests/test_thresholds.py
  - id: openwiki-source-efe52f802136ea4316cd0f90
    resource: repo://thresholds-mengram.yaml
  - id: openwiki-source-f0ff834cf56ce15024d0ede4
    resource: repo://thresholds-openwiki.yaml
  - id: openwiki-source-95e171e2045483fa0c961258
    resource: repo://thresholds-yt-summarizer.yaml
generated: { by: "openwiki/0.9.0", at: "2026-11-14T11:53:54.399Z" }
verified:
  - by: openwiki/0.9.0
    at: 2026-11-14T11:53:54.399Z
---

# Source Map

This page maps the repository's source code structure to help contributors navigate from documentation to implementation. It highlights key files, symbols, tests, output artifacts, and data files for the openrouter-model-list pipeline.

## Architecture & Pipeline

| Concept | Source Files | Key Symbols | Tests |
|---------|--------------|-------------|-------|
| Main orchestrator | `scripts/generate_models.py` | `generate()`, `resolve_profile()`, `PROFILES`, `SCHEMA_VERSION` | `tests/test_generate_models.py::test_generate_writes_models_json_sorted_by_score`, `test_generate_writes_probe_history`, `test_generate_includes_own_uptime_and_sanity_ok` |
| Free model filter | `scripts/filters.py::is_free` | `is_free()` | `tests/test_filters.py::test_is_free` |
| Threshold filtering | `scripts/filters.py::filter_candidates` | `filter_candidates()`, `parse_param_count()`, `supports_structured_output()`, `supports_tools()` | `tests/test_filters.py::test_filter_candidates_*` |
| Parameter parsing | `scripts/filters.py` | `PARAM_RE`, `parse_param_count()` | `tests/test_filters.py::test_parse_param_count_*` |
| Endpoint stats fetch | `scripts/endpoint_stats.py` | `fetch_endpoint_stats()`, `ENDPOINTS_URL_TEMPLATE` | `tests/test_endpoint_stats.py::test_fetch_endpoint_stats_*` |
| Probe execution | `scripts/probe.py` | `probe_model()`, `record_probe()`, `read_history()`, `HISTORY_DIR`, `HISTORY_WINDOW_DAYS` | `tests/test_probe.py::test_probe_model`, `test_record_probe`, `test_read_history` |
| Uptime scoring | `scripts/scoring.py::compute_uptime` | `compute_uptime()`, `NEUTRAL_UPTIME` | `tests/test_scoring.py::test_compute_uptime_*` |
| Weighted scoring | `scripts/scoring.py::compute_score` | `compute_score()`, `UPTIME_WEIGHT`, `LATENCY_WEIGHT`, `CAPABILITY_WEIGHT`, `LATENCY_CAP_MS` | `tests/test_scoring.py::test_compute_score_*` |
| Post-probe filters | `scripts/scoring.py::passes_post_probe_filters` | `passes_post_probe_filters()` | `tests/test_scoring.py::test_passes_post_probe_filters` |
| Threshold loading | `scripts/thresholds.py` | `load_thresholds()`, `DEFAULTS` | `tests/test_thresholds.py::test_load_thresholds_*` |
| OpenRouter catalog fetch | `scripts/openrouter_client.py` | `fetch_models()`, `MODELS_URL` | `tests/test_openrouter_client.py::test_fetch_models` |
| Anthropic model list | `scripts/generate_anthropic_models.py` | `generate()`, `fetch_models()`, `fetch_pricing_page()`, `parse_pricing_table()`, `join_prices()`, `join_long_context()` | — |

## Data & Control Flow

`generate_models.py` is the main orchestrator. For a given profile it:

1. Loads thresholds from the profile's YAML file via `load_thresholds()` (`scripts/thresholds.py`).
2. Fetches the OpenRouter catalog via `fetch_models()` (`scripts/openrouter_client.py`).
3. Filters free models with `filter_candidates()` (`scripts/filters.py`), applying a hard `min_param_b` floor (models without a parseable size token are excluded unless allowlisted), buffered `min_context_length` and `min_max_output_tokens`, and optional `require_structured_output`/`require_tools` checks. Allowlisted models bypass the size/context/output floors but still must pass capability checks; hardallowlisted models bypass everything. If buffering shrinks the pool below `min_candidate_pool`, `buffer_pct` relaxes step-wise toward 0.
4. For each candidate, fetches OpenRouter endpoint stats via `fetch_endpoint_stats()` (`scripts/endpoint_stats.py`); missing stats fall back to `NEUTRAL_UPTIME` and `latency_ms: null`.
5. Probes each model with `probe_model()` (`scripts/probe.py`) — one minimal completion request returning `{success, latency_ms}`.
6. Records each probe via `record_probe()` to `history/<model>.jsonl`, trimmed to a rolling `HISTORY_WINDOW_DAYS` (30 days) window.
7. Reads history via `read_history()`, computes `own_uptime` via `compute_uptime()` (`scripts/scoring.py`).
8. Applies `passes_post_probe_filters()` (`scripts/scoring.py`) using OpenRouter endpoint uptime/latency.
9. Scores survivors with `compute_score()` — weighted uptime (0.6), latency (0.3), relative context (0.1), multiplied by `own_uptime`.
10. Writes `{generated_at, schema_version, models[]}` sorted by score descending.

The Anthropic path (`scripts/generate_anthropic_models.py`) fetches paginated models from `https://api.anthropic.com/v1/models`, scrapes the pricing page at `https://platform.claude.com/docs/en/about-claude/pricing`, joins prices by slug/alias table, and fails closed (non-zero exit, no output write) on any missing or invalid price — preserving the last-known-good committed file.

## Configuration

| Concept | Source Files | Key Symbols |
|---------|--------------|-------------|
| mengram thresholds | `thresholds-mengram.yaml` | `min_param_b: 28`, `min_context_length: 40000`, `min_max_output_tokens: 8000`, `buffer_pct: 5`, `require_structured_output: true`, `allowlist: [openrouter/owl-alpha]`, `min_candidate_pool: 3` |
| yt-summarizer thresholds | `thresholds-yt-summarizer.yaml` | `min_param_b: 14`, `min_context_length: 32000`, `min_max_output_tokens: 2000`, `buffer_pct: 5`, `require_structured_output: false`, `allowlist: [meta-llama/llama-4-scout:free, openrouter/owl-alpha, qwen/qwen3-32b:free]`, `min_candidate_pool: 3` |
| openwiki thresholds | `thresholds-openwiki.yaml` | `min_param_b: 70`, `min_context_length: 128000`, `min_max_output_tokens: 16000`, `buffer_pct: 5`, `require_structured_output: false`, `require_tools: true`, `allowlist: [thinkingmachines/inkling:free, poolside/laguna-s-2.1:free, cohere/north-mini-code:free, nvidia/nemotron-3.5-lightning:free, google/gemma-4-31b-it:free, google/gemma-4-26b-a4b-it:free, nvidia/nemotron-3.5-super-vl:free]`, `min_candidate_pool: 2` |
| Profile registry | `scripts/generate_models.py` | `PROFILES` dict mapping profile name to `{thresholds_path, output_path}` |
| Anthropic price aliases | `anthropic-price-aliases.yaml` | `aliases` map used by `load_aliases()` when slug matching fails |

## Outputs & Data

| Artifact | Generated By | Schema |
|----------|--------------|--------|
| `models-mengram.json` | `generate_models.py --profile mengram` | `generated_at`, `schema_version: 2`, `models[] {id, score, context_length, max_output_tokens, uptime, latency_ms, own_uptime, sanity_ok}` |
| `models-yt-summarizer.json` | `generate_models.py --profile yt-summarizer` | Same schema |
| `models-openwiki.json` | `generate_models.py --profile openwiki` | Same schema |
| `anthropic-models.json` | `scripts/generate_anthropic_models.py` | Array of `{id, display_name, type, created_at, line, max_input_tokens, max_tokens, capabilities, ...}` sorted by `id` |
| `history/*.jsonl` | `probe.py::record_probe` | Rolling 30-day: `{timestamp, success, latency_ms}` per line |
| `history/anthropic-models.jsonl` | `generate_anthropic_models.py` | `{timestamp, models[]}` appended per run |

## Workflows

| Workflow | File | Schedule | Key Steps |
|----------|------|----------|-----------|
| Daily model lists | `.github/workflows/update-models.yml` | `0 3 * * *` (daily 03:00 UTC) | Checkout → uv sync → generate 3 profiles → PR to `automation/update-models` → merge attempt |
| Daily Anthropic | `.github/workflows/update-anthropic-models.yml` | `15 3 * * *` (daily 03:15 UTC) | Fetch Anthropic API → normalize → PR to `automation/update-anthropic-models` → merge attempt |
| Bi-weekly OpenWiki | `.github/workflows/openwiki-update.yaml` | `0 5 * * 6` (Sat 05:00 UTC) + parity gate | Gate: ISO week parity → Checkout → Node.js setup → Install openwiki → Fetch ALL sanity_ok models → Loop through candidates → Create PR |

All three workflows use the `update-model-lists` concurrency group with `cancel-in-progress: false`, authenticate via `GITHUB_TOKEN` for GitHub operations, and rely on API-key secrets (`OPENROUTER_API_KEY`, `ANTHROPIC_API_KEY`, `LANGSMITH_API_KEY`) for external service access.

## Testing

| Test File | Coverage |
|-----------|----------|
| `tests/test_filters.py` | `parse_param_count`, `is_free`, `supports_structured_output`, `supports_tools`, `filter_candidates` (buffer relaxation, allowlist, hardallowlist, feature requirements) |
| `tests/test_endpoint_stats.py` | `fetch_endpoint_stats` (success, no free endpoints, HTTP error, missing p50) |
| `tests/test_probe.py` | `probe_model`, `record_probe` (trimming), `read_history` |
| `tests/test_scoring.py` | `compute_uptime`, `compute_latency_p50`, `passes_post_probe_filters`, `compute_score` (weights, caps, malus) |
| `tests/test_thresholds.py` | `load_thresholds` (defaults, override, missing keys) |
| `tests/test_openrouter_client.py` | `fetch_models` (success, HTTP error) |
| `tests/test_generate_models.py` | Integration: `generate()` with mocked deps, profile resolution, output schema, probe history, warnings |

## Quick Commands

```bash
# Run single profile generation
uv run python scripts/generate_models.py --profile mengram
uv run python scripts/generate_models.py --profile yt-summarizer
uv run python scripts/generate_models.py --profile openwiki

# Run Anthropic model list generation
uv run python scripts/generate_anthropic_models.py

# Run all tests
uv run pytest

# Run focused test modules
uv run pytest tests/test_filters.py -v
uv run pytest tests/test_scoring.py -v
uv run pytest tests/test_generate_models.py -v
```
