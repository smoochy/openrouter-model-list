---
type: Reference
title: Source Map
description: "Maps the openrouter-model-list repository's source code structure, highlighting key files, symbols, and tests for contributors."
resource: /openwiki/source-map.md
tags: [reference, source-map, architecture, workflows, configuration, operations]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-17T08:58:08.450Z
sources:
  - id: openwiki-source-e082dc1d961398caa2e27f47
    resource: repo://.github/workflows/openwiki-update.yaml
  - id: openwiki-source-cc9c2e48d2340a266da2a1aa
    resource: repo://.github/workflows/update-anthropic-models.yml
  - id: openwiki-source-c98bff360638db4f2aa27c80
    resource: repo://.github/workflows/update-models.yml
  - id: openwiki-source-4dab8009ad11ecde31efe1bd
    resource: repo://anthropic-models.json
  - id: openwiki-source-7d5f69b071aa52e8ef9e8a4f
    resource: repo://history/nvidia__nemotron-3.5-lightning__free.jsonl
  - id: openwiki-source-7e04a6f89135965340679759
    resource: repo://models-mengram.json
  - id: openwiki-source-485cf2e58e69a12dcb5aa656
    resource: repo://models-openwiki.json
  - id: openwiki-source-9b20ebe8f326f32ddab0d3ca
    resource: repo://models-yt-summarizer.json
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
generated: { by: "openwiki/0.7.2", at: "2026-10-17T08:58:08.450Z" }
---

# Source Map

This page maps the repository's source code structure to help contributors navigate from documentation to implementation. It highlights key files, symbols, and tests for the openrouter-model-list pipeline.

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

## Configuration

| Concept | Source Files | Key Symbols |
|---------|--------------|-------------|
| mengram thresholds | `thresholds-mengram.yaml` | `min_param_b: 28`, `min_context_length: 40000`, `min_max_output_tokens: 8000`, `require_structured_output: true`, `allowlist: [openrouter/owl-alpha]` |
| yt-summarizer thresholds | `thresholds-yt-summarizer.yaml` | `min_param_b: 14`, `min_context_length: 32000`, `min_max_output_tokens: 2000`, `require_structured_output: false`, `allowlist: [meta-llama/llama-4-scout:free, openrouter/owl-alpha, qwen/qwen3-32b:free]` |
| openwiki thresholds | `thresholds-openwiki.yaml` | `min_param_b: 70`, `min_context_length: 128000`, `min_max_output_tokens: 16000`, `require_tools: true`, `min_candidate_pool: 2` |
| Profile registry | `scripts/generate_models.py` | `PROFILES` dict mapping profile name to `{thresholds_path, output_path}` |

## Outputs & Data

| Artifact | Generated By | Schema |
|----------|--------------|--------|
| `models-mengram.json` | `generate_models.py --profile mengram` | `generated_at`, `schema_version: 2`, `models[] {id, score, context_length, max_output_tokens, uptime, latency_ms, own_uptime, sanity_ok}` |
| `models-yt-summarizer.json` | `generate_models.py --profile yt-summarizer` | Same schema |
| `models-openwiki.json` | `generate_models.py --profile openwiki` | Same schema |
| `anthropic-models.json` | `scripts/generate_anthropic_models.py` | Array of `{id, display_name, type, created_at}` sorted by `id` |
| `history/*.jsonl` | `probe.py::record_probe` | Rolling 30-day: `{timestamp, success, latency_ms}` per line |

## Workflows

| Workflow | File | Schedule | Key Steps |
|----------|------|----------|-----------|
| Daily model lists | `.github/workflows/update-models.yml` | `0 3 * * *` (daily 03:00 UTC) | Checkout → uv sync → generate 3 profiles → PR to `automation/update-models` → merge attempt |
| Weekly Anthropic | `.github/workflows/update-anthropic-models.yml` | `15 3 * * *` (daily 03:15 UTC) | Fetch Anthropic API → normalize → PR to `automation/update-anthropic-models` → merge attempt |
| Bi-weekly OpenWiki | `.github/workflows/openwiki-update.yaml` | `0 5 * * 6` (Sat 05:00 UTC) + parity gate | Gate: ISO week parity → Checkout → Install openwiki → Fetch ALL sanity_ok models → Loop through candidates → Create PR |

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
