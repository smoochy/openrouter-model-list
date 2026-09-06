---
type: concept
title: Testing Overview
description: Explain the testing strategy for the repository, including unit tests for filters, scoring, probing, and end-to-end workflows.
tags: ["testing", "unit-tests", "integration", "workflow"]
verified:
  - by: openwiki/0.5.0
    at: 2026-09-05T08:44:41.032Z
sources:
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
generated: { by: "openwiki/0.5.0", at: "2026-09-05T08:44:41.032Z" }
---

The OpenWiki project employs a comprehensive testing strategy to ensure correctness and reliability across its modules. Tests are organized in the `tests/` directory and cover unit-level functionality for individual components as well as integrated workflows that exercise end-to-end model generation processes.

## Unit Test Coverage

### Filters (`test_filters.py`)
Validates the candidate filtering logic that selects models based on:
- Parameter count parsing (extracting `b` suffixes)
- Free model detection via pricing fields
- Structured output and tool call support detection
- Application of thresholds including:
  - Parameter floors (`min_param_b`)
  - Free model requirements
  - Allowlist enforcement with warning logs
  - Tool and structured output requirements

### Endpoint Statistics (`test_endpoint_stats.py`)
Tests the `fetch_endpoint_stats` function which queries OpenRouter for per-model endpoint data:
- Averages uptake and latency across free endpoints only
- Handles missing latency fields gracefully
- Returns `None` when no free endpoints exist or on HTTP errors
- Verifies Bearer token authentication in requests

### OpenRouter Client (`test_openrouter_client.py`)
Covers the `fetch_models` function that retrieves the global model catalog:
- Confirms successful extraction of model IDs from API responses
- Validates Bearer token header injection
- Ensures proper error propagation on non-200 responses

### Probe Logic (`test_probe.py`)
Tests model probing functionality including:
- Success/failure detection with latency measurement
- JSONL history recording with automatic 30-day trimming
- Safe filename generation for history files (special character handling)
- Round-trip consistency between recording and reading history

### Scoring (`test_scoring.py`)
Validates the scoring algorithm that ranks models:
- Uptime computation from probe history (ratio with minimum sample threshold)
- Latency P50 calculation using only successful probes
- Score components:
  - Capability score (normalized context length)
  - Uptime weight (highest impact factor)
  - Own-uptime malus (linear scaling)
- Post-probe filter enforcement (minimum uptime, maximum latency)

### Thresholds (`test_thresholds.py`)
Ensures proper loading and default application for profile configuration files:
- Full field parsing from YAML
- Default value application for missing keys (e.g., `require_structured_output: true`)
- Type conversion (booleans, integers, nulls)
- Allowlist and hardallowlist array handling

## Integration and Workflow Tests

### Model Generation (`test_generate_models.py`)
End-to-end validation of the core workflow via the `generate` function:
- Profile resolution (`mengram`, `yt-summarizer`) mapping to correct threshold/output paths
- Catalog filtering through multiple stages:
  1. Static thresholds (parameter floors, context lengths)
  2. Endpoint statistics uptake/latency
  3. Live probing (success/failure)
  4. Post-probe filters
- Score-based sorting of final model list
- History directory population with JSONL probe records
- Schema version output and file writing verification
- Warning logging for missing endpoint stats
- Sanity check flag assignment (`sanity_ok`) based on probe success
- Own uptime initialization (`NEUTRAL_UPTIME`) for new models

## Testing Practices

- **Isolation**: Unit tests use mocking (`respx`, `pytest-mock`) to avoid external API calls
- **Fixtures**: Shared helpers like `make_model` in `conftest.py` reduce duplication
- **Determinism**: Fixed timestamps and controlled inputs ensure reproducible results
- **Error Handling**: Explicit tests for HTTP failures, missing fields, and edge cases
- **Output Validation**: Tests verify both return values and side effects (file writes, history logs)

## Running Tests

Execute the test suite with:
```bash
pytest
```

Individual test files can be run directly:
```bash
pytest tests/test_filters.py
```

Tests are configured in `pyproject.toml` and leverage pytest's discovery and reporting capabilities.
