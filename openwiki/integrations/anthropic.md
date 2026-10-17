---
type: integration
title: Anthropic API Integration
description: Details how the system fetches Claude model metadata and pricing from Anthropic's API and pricing page to generate anthropic-models.json.
tags: [anthropic, api, integration, models, pricing]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-17T08:58:08.450Z
sources:
  - id: openwiki-source-23fb3ed4bd0ff9d6e2dfb273
    resource: repo://scripts/generate_anthropic_models.py
generated: { by: "openwiki/0.7.2", at: "2026-10-17T08:58:08.450Z" }
---
The Anthropic API integration is implemented in `scripts/generate_anthropic_models.py`. It fetches the list of available Claude models from the Anthropic Models API and combines it with pricing data scraped from the official Claude pricing page to produce `anthropic-models.json`, which is used throughout the system for cost calculations.

## API Models Endpoint
The integration retrieves model metadata by making authenticated requests to `https://api.anthropic.com/v1/models`. It uses:
- Header `x-api-key` with the API key from the execution environment
- Header `anthropic-version: 2023-06-01`
- Query parameter `limit: 1000` for pagination
It follows the `has_more` and `last_id` fields to iterate through all pages, filtering results to objects where `type == "model"`. The final model list is sorted by `id`.

## Pricing Page Scraping
Pricing data is obtained by requesting `https://platform.claude.com/docs/en/about-claude/pricing` with the header `Accept: text/markdown` to receive the page in Markdown format. The integration locates the first table whose header matches (after whitespace normalization):
```
| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |
```
Each subsequent row is parsed into six cells. The first cell is the model name as shown on the pricing page; the remaining five cells contain prices in formats like `$0.25 / MTok<sup>1</sup>`. Prices are extracted via regex `\$\s*([0-9]+(?:\.[0-9]+)?)\s*/\s*MTok` and converted to `float`. A `PricingError` is raised if the header is missing, a row has an incorrect number of columns, any price fails to parse, or any price is zero or negative.

## Model ID to Pricing Row Matching
The integration matches API model IDs to pricing table rows using a two-step process:
1. **Slugification**: Pricing page model names are converted to slugs via `slugify`: lowercase, replace spaces and periods with hyphens, remove non-alphanumeric/hyphen characters, collapse multiple hyphens, and trim leading/trailing hyphens.
2. **Alias Resolution**: Before attempting a direct slug match, the integration checks `anthropic-price-aliases.yaml` for alternative model ID mappings. Alias entries take precedence over slug matches.
For each pricing row, the resolved model IDs (from aliases or slug) are assigned the row's prices. If any API model ID from the fetch step lacks a price after processing all rows, the integration raises a `PricingError` listing the missing IDs and aborts without writing output (fail-closed behavior).

## Long-Context Tiers
Some pricing page rows include a suffix like `(for prompts over 200000 tokens)` in the model name cell. The integration extracts the threshold value using `\(\s*for prompts over ([0-9][0-9,]*) tokens\s*\)`. When present, the same prices are combined with the threshold as `threshold_input_tokens` for the matched model ID(s). Rows that do not map to any API model ID are ignored.

## Output and History
On successful completion, the integration writes a JSON object to `anthropic-models.json` mapping each model ID to an object containing:
- `input`, `cache_write_5m`, `cache_write_1h`, `cache_read`, `output` (all floats, dollars per million tokens)
- Optionally `threshold_input_tokens` (integer) for long-context variants
Additionally, it appends a JSON line to `history/anthropic-models.jsonl` containing the same data plus a `fetched_at` timestamp (ISO 8601, UTC). If any step fails, no output files are written and the existing `anthropic-models.json` remains unchanged, preserving the last known-good dataset.

## Operational Context
This integration is executed on a schedule by GitHub Actions (see workflows/generate-anthropic-models.md). It requires an `ANTHROPIC_API_KEY` secret in the workflow environment. The fail-closed design ensures that pricing anomalies (e.g., missing or zero prices) prevent corruption of downstream cost calculations rather than silently propagating bad data.
