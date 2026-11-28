---
type: process
title: Probe History and Reliability Scoring
description: Explains how probe results are collected (1-token completion), stored in per-model rolling 30-day JSONL history files, and used to compute the own_uptime malus that adjusts model scores based on local probe success rate.
tags: ["probe", "history", "scoring", "reliability"]
sources:
  - id: openwiki-source-11968c67bba9651b9ac1c4e5
    resource: repo://scripts/probe.py
  - id: openwiki-source-f3047b157e385d6464b26dbd
    resource: repo://scripts/scoring.py
generated: { by: "openwiki/0.9.0", at: "2026-11-28T13:48:21.508Z" }
verified:
  - by: openwiki/0.9.0
    at: 2026-11-28T13:48:21.508Z
---

OpenRouter models are probed with a minimal completion request to measure local success rate and latency. The outcomes are stored in a per-model history file and used to compute an *own_uptime* factor that acts as a malus on the overall score.

## Probe collection

The `probe_model` function sends a single completion request with `max_tokens=1` and the prompt `"ping"` to the OpenRouter API for a given model ID. The function records whether the request succeeded (`success: true/false`) and the latency in milliseconds. Probing happens for every candidate model, including hardallowlisted models.

## History storage

Probe results are appended to a JSONL file located in the `history/` directory. The `HISTORY_DIR` constant resolves to `<repo_root>/history`. The filename is derived from the model ID by replacing `/` and `:` with `__` to ensure filesystem safety (for example, `google/gemma-4-26b-a4b-it:free` becomes `google__gemma-4-26b-a4b-it__free.jsonl`). Each line in the file is a JSON object containing:
- `timestamp`: ISO 8601 string with `Z` suffix (UTC)
- `success`: boolean indicating probe outcome
- `latency_ms`: integer latency in milliseconds

The history is limited to a rolling window of 30 days (`HISTORY_WINDOW_DAYS = 30`). When a new probe result is recorded via `record_probe`, all existing entries are re-read, the new entry is appended, entries older than the cutoff (current timestamp minus 30 days) are discarded, and the file is rewritten with the trimmed set. `read_history` returns the list of entries for a given model ID, or an empty list if no history file exists.

## Uptime calculation

The `compute_uptime` function derives the own_uptime malus from the history:
- If fewer than `MIN_SAMPLES_FOR_UPTIME` (currently 3) probes are available, returns a neutral value of `NEUTRAL_UPTIME` (0.5). New models are not penalized.
- Otherwise, returns the ratio of successful probes to total probes in the 30-day window.

The related `compute_latency_p50` function computes the p50 latency from successful probes only, returning `None` when no successful probes exist.

## Score integration

In `compute_score`, the base score is a weighted sum of:
- OpenRouter-reported uptime (`or_uptime`), weight 0.6
- Normalized latency (derived from OpenRouter-reported latency, capped at `LATENCY_CAP_MS` = 5000 ms), weight 0.3
- Capability score (based on context length relative to the maximum observed in the candidate pool), weight 0.1

The base score is then multiplied by the own_uptime factor, applying a malus that reduces the score for models with poor local probe success rate. An own_uptime of 0.0 zeroes the score; 0.5 halves it; 1.0 leaves it unchanged.

Optional post-probe filters (`passes_post_probe_filters`) can additionally skip models whose own_uptime or latency p50 fall below configured thresholds, but both thresholds are currently unset in all threshold profiles.
