---
type: process
title: Probe History and Reliability Scoring
description: Explains how probe results are collected, stored in rolling-window history files, and used to compute the own_uptime malus that adjusts model scores based on local probe success rate.
tags: ["probe", "history", "scoring", "reliability"]
verified:
  - by: openwiki/0.7.2
    at: 2026-10-17T08:58:08.450Z
sources:
  - id: openwiki-source-11968c67bba9651b9ac1c4e5
    resource: repo://scripts/probe.py
  - id: openwiki-source-f3047b157e385d6464b26dbd
    resource: repo://scripts/scoring.py
generated: { by: "openwiki/0.7.2", at: "2026-10-17T08:58:08.450Z" }
---

OpenRouter models are probed daily with a minimal completion request to measure local success rate and latency. The outcomes are stored in a per-model history file and used to compute an *own_uptime* factor that acts as a malus on the overall score.

## Probe collection
Each day, the `probe_model` function sends a single completion request with `max_tokens=1` and the prompt `"ping"` to the OpenRouter API for a given model ID. The function records whether the request succeeded (`success: true/false`) and the latency in milliseconds.

## History storage
Probe results are appended to a JSONL file located in the `history/` directory. The filename is derived from the model ID by replacing `/` and `:` with `__` to ensure filesystem safety. Each line in the file is a JSON object containing:
- `timestamp`: ISO 8601 string with `Z` suffix (UTC)
- `success`: boolean indicating probe outcome
- `latency_ms`: integer latency in milliseconds

The history is limited to a rolling window of 30 days. When a new probe result is recorded, entries older than the cutoff (current timestamp minus 30 days) are discarded.

## Uptime calculation
The `compute_uptime` function derives the own_uptime malus from the history:
- If fewer than `MIN_SAMPLES_FOR_UPTIME` (currently 3) probes are available, returns a neutral value of `NEUTRAL_UPTIME` (0.5).
- Otherwise, returns the ratio of successful probes to total probes in the window.

## Score integration
In `compute_score`, the base score is a weighted sum of:
- OpenRouter-reported uptime (`or_uptime`)
- Normalized latency (derived from OpenRouter-reported latency, capped at `LATENCY_CAP_MS`)
- Capability score (based on context length relative to the maximum observed)

The base score is then multiplied by the own_uptime factor, applying a malus that reduces the score for models with poor local probe success rate.
