---
type: integration
title: OpenRouter API Integration
description: Describes how the system fetches the OpenRouter model catalog, endpoint statistics, and performs 1-token sanity probes via the OpenAI-compatible API, including error handling and missing free endpoint behavior.
tags: [openrouter, api, models, endpoint-stats, probing]
sources:
  - id: openwiki-source-678af2bf704a9375a5423843
    resource: repo://scripts/endpoint_stats.py
  - id: openwiki-source-d8b85b547cd70ae9d19deeea
    resource: repo://scripts/generate_models.py
  - id: openwiki-source-f53424678e8568c6002e83f4
    resource: repo://scripts/openrouter_client.py
  - id: openwiki-source-11968c67bba9651b9ac1c4e5
    resource: repo://scripts/probe.py
  - id: openwiki-source-f3047b157e385d6464b26dbd
    resource: repo://scripts/scoring.py
verified:
  - by: openwiki/0.9.0
    at: 2026-11-14T11:53:54.399Z
generated: { by: "openwiki/0.9.0", at: "2026-11-14T11:53:54.399Z" }
---

# OpenRouter API Integration

## Model Catalog Fetching

The system retrieves the list of available models from OpenRouter using the `/models` endpoint. This is implemented in `scripts/openrouter_client.py`:

```python
def fetch_models(api_key: str) -> list[dict]:
    response = httpx.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]
```

The caller (`scripts/generate_models.py`) resolves the API key from the `OPENROUTER_API_KEY` environment variable and passes it to `fetch_models`. The function returns the `data` array from the response, a list of model objects each containing at least an `id` field (e.g., `"google/gemma-4-31b-it:free"`).

## Endpoint Statistics Fetching

For each candidate model, the system fetches aggregated uptime and latency statistics from OpenRouter's `/models/{model_id}/endpoints` endpoint. This is implemented in `scripts/endpoint_stats.py`:

```python
def fetch_endpoint_stats(api_key: str, model_id: str) -> dict | None:
    url = f"https://openrouter.ai/api/v1/models/{model_id}/endpoints"
    try:
        response = httpx.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )
        response.raise_for_status()
    except httpx.HTTPError:
        return None

    endpoints = (response.json().get("data") or {}).get("endpoints", [])
    free = [
        e for e in endpoints
        if (e.get("pricing") or {}).get("prompt") == "0"
        and (e.get("pricing") or {}).get("completion") == "0"
    ]
    if not free:
        return None

    uptimes = [(e.get("uptime_last_1d") or 0) / 100 for e in free]
    latencies = [
        (e.get("latency_last_30m") or {})["p50"]
        for e in free
        if (e.get("latency_last_30m") or {}).get("p50") is not None
    ]

    return {
        "uptime": sum(uptimes) / len(uptimes),
        "latency_p50": sum(latencies) / len(latencies) if latencies else None,
    }
```

The `model_id` is passed through as-is, including the `:free` suffix (e.g., `"google/gemma-4-31b-it:free"`).

The function returns a dictionary with:
- `uptime`: average uptime over the last day (as a float between 0 and 1) across all free endpoints for the model. The raw `uptime_last_1d` value is divided by 100.
- `latency_p50`: average 50th percentile latency over the last 30 minutes (in milliseconds) across free endpoints, or `None` if no latency data is available.

Free endpoints are those where both `pricing.prompt` and `pricing.completion` equal `"0"`. If the HTTP request fails or no free endpoints are found, the function returns `None`.

## Error Handling

Both API functions use `httpx` with a 30-second timeout and call `response.raise_for_status()` to convert HTTP error responses (4xx/5xx) into exceptions, but they handle failures differently:

- In `fetch_models`, exceptions are not caught and propagate up, halting the model generation process. An HTTP 429 (rate limit) or other error stops the run.
- In `fetch_endpoint_stats`, any `httpx.HTTPError` (including network errors, timeouts, and HTTP status errors) is caught and results in a `None` return value. The caller treats `None` as "no stats available" and substitutes neutral values.

The system does not implement explicit rate limit handling (e.g., `Retry-After` headers) beyond the built-in timeout and exception mechanisms.

## Probing Models (OpenAI-compatible API)

Beyond the OpenRouter-specific endpoints, the system uses OpenRouter's OpenAI-compatible chat completions API to perform sanity probes on candidate models. The orchestrator (`scripts/generate_models.py`) configures an `openai.OpenAI` client with:

```python
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
```

The probe function in `scripts/probe.py` sends a minimal chat request to verify model responsiveness:

```python
def probe_model(client, model_id: str) -> dict:
    start = time.monotonic()
    try:
        client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        success = True
    except Exception:
        success = False
    latency_ms = int((time.monotonic() - start) * 1000)
    return {"success": success, "latency_ms": latency_ms}
```

The probe sends a single-user message `"ping"` with `max_tokens=1` — a 1-token completion request. Any exception (network error, model unavailable, authentication failure, etc.) results in `success: False`; otherwise `success: True`. The returned dictionary always includes `latency_ms`, measured wall-clock time in milliseconds.

Probe results are recorded to a per-model JSONL file under `history/` (a 30-day rolling window), and the local success rate feeds into the model's `own_uptime` malus in scoring. See [Probe History and Reliability Scoring](../operations/probe-history.md).

## Missing Free Endpoints

When `fetch_endpoint_stats` returns `None` (request failure or no free endpoints), `generate_models.py` logs a warning and substitutes neutral values: `uptime = 0.5` (`NEUTRAL_UPTIME`) and `latency_p50 = None`. The model is still probed and scored, but without OpenRouter-reported uptime/latency contributions.
