---
type: integration
title: OpenRouter API Integration
description: Describes how the system fetches model catalogs, endpoint statistics, and handles errors when interacting with the OpenRouter API.
tags: [openrouter, api, models, endpoint-stats]
sources:
  - id: openwiki-source-678af2bf704a9375a5423843
    resource: repo://scripts/endpoint_stats.py
  - id: openwiki-source-d8b85b547cd70ae9d19deeea
    resource: repo://scripts/generate_models.py
  - id: openwiki-source-f53424678e8568c6002e83f4
    resource: repo://scripts/openrouter_client.py
generated: { by: "openwiki/0.7.2", at: "2026-10-17T08:58:08.450Z" }
verified:
  - by: openwiki/0.7.2
    at: 2026-10-31T10:41:37.317Z
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

The function requires an OpenRouter API key provided via the `OPENROUTER_API_KEY` environment variable. It returns a list of model objects, each containing at least an `id` field (e.g., `"google/gemma-4-31b-it:free"`). This function is called by `scripts/generate_models.py` during the model generation process.

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

The function returns a dictionary with:
- `uptime`: average uptime over the last day (as a float between 0 and 1) across all free endpoints for the model.
- `latency_p50`: average 50th percentile latency over the last 30 minutes (in milliseconds) across free endpoints, or `None` if no latency data is available.

If the request fails or no free endpoints are found, the function returns `None`. In the model generation script, a `None` result triggers a warning and causes the system to use neutral uptime and latency values.

## Error Handling and Rate Limits

Both API functions use `httpx` with a 30-second timeout and call `response.raise_for_status()` to convert HTTP error responses (4xx/5xx) into exceptions.

- In `fetch_models`, exceptions are not caught and will propagate up, halting the model generation process.
- In `fetch_endpoint_stats`, any `httpx.HTTPError` (including network errors, timeouts, and HTTP status errors) is caught and results in a `None` return value.

The system does not implement explicit rate limit handling (e.g., retry-after headers) beyond the built-in timeout and exception mechanisms. HTTP 429 responses will raise an exception in `fetch_models` or be caught and treated as a failure in `fetch_endpoint_stats`.

## Probing Models (OpenAI-compatible API)

Beyond the OpenRouter-specific endpoints, the system uses OpenRouter's OpenAI-compatible chat completions API to perform sanity probes on candidate models. This is done via an `openai.OpenAI` client configured with:

```python
client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
```

The probe function (defined in `scripts/probe.py`) sends a minimal chat request to verify model responsiveness. This leverages OpenRouter's compatibility with the OpenAI API rather than a proprietary endpoint.

## Environment Configuration

The OpenRouter API key must be supplied via the `OPENROUTER_API_KEY` environment variable. Both the model fetching and endpoint statistics functions depend on this key for authentication.
