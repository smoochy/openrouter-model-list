---
type: workflow
title: Anthropic Model List Generation Workflow
description: Explains how the Anthropic model list is generated, including fetching from the Anthropic API, normalizing, and outputting the JSON.
tags: [anthropic, models, generation, workflow]
sources:
  - id: openwiki-source-23fb3ed4bd0ff9d6e2dfb273
    resource: repo://scripts/generate_anthropic_models.py
generated: { by: "openwiki/0.7.2", at: "2026-10-17T08:58:08.450Z" }
---

The `generate_anthropic_models.py` script produces `anthropic-models.json` by combining live model metadata from the Anthropic API with pricing information scraped from the public Claude pricing page. The workflow follows a fail-closed design: if any model lacks a valid price after joining, the script exits with a non-zero status and preserves the last known good output.

## Process Overview

1. **Fetch Models** – Calls `GET https://api.anthropic.com/v1/models` (with pagination) and filters to objects where `"type": "model"`.
2. **Fetch Pricing** – Retrieves `https://platform.claude.com/docs/en/about-claude/pricing` with an `Accept: text/markdown` header to obtain the Markdown pricing table.
3. **Parse Pricing Table** – Locates the table by its exact normalized header (`| Model | Base input tokens | 5m cache writes | 1h cache writes | Cache hits and refreshes | Output tokens |`). Each row is parsed into five price fields (input, cache_write_5m, cache_write_1h, cache_read, output) in USD per million tokens. Prices must be positive and parsable; otherwise a `PricingError` is raised.
4. **Alias Resolution** – Reads `anthropic-price-aliases.yaml` to map pricing table rows (via slugified names) to API model IDs. Alias matches take precedence over direct slug matches.
5. **Join Prices** – For each model ID from the API, attempts to find a price entry via slug or alias. If any model ID remains unmatched, the script fails with a list of missing models.
6. **Long‑Context Tiers** – Detects rows containing a suffix like `(for prompts over 200,000 tokens)` and attaches a `pricing_long_context` object (including the threshold and the same five price fields) to matching models.
7. **Output** – Writes the enriched model list to `anthropic-models.json` (pretty‑printed with indent=2) and appends a JSONL entry to `history/anthropic-models.jsonl` containing a UTC timestamp and the full model array.

## Key Characteristics

- **Fail‑Closed** – On any pricing problem (missing table, schema change, unparseable price, zero/negative price, or unmatched model) the script prints an error to stderr, returns exit code 1, and leaves `anthropic-models.json` untouched. This prevents propagating corrupted pricing data to downstream consumers.
- **History** – Each successful run appends a compact JSON line to `history/anthropic-models.jsonl`, enabling audit and rollback.
- **CLI Entrypoint** – Executed via `python scripts/generate_anthropic_models.py`; requires the `ANTHROPIC_API_KEY` environment variable.
- **Deterministic Output** – Model list is sorted by `id` before joining, ensuring diff‑friendly updates.

## Related Files

- `scripts/generate_anthropic_models.py` – Implementation of the workflow.
- `anthropic-price-aliases.yaml` – Manual overrides for mapping pricing table rows to model IDs.
- `anthropic-models.json` – The latest known‑good output (committed to the repository).
- `history/anthropic-models.jsonl` – Append‑only log of successful generations.
