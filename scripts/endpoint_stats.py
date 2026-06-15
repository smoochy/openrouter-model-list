"""Fetch OpenRouter's aggregated uptime/latency stats for a model's free endpoints."""
import httpx

ENDPOINTS_URL_TEMPLATE = "https://openrouter.ai/api/v1/models/{model_id}/endpoints"


def fetch_endpoint_stats(api_key: str, model_id: str) -> dict | None:
    """Fetch and average uptime/latency across a model's free endpoints.

    model_id is "author/slug" (e.g. "google/gemma-4-31b-it:free"); the
    ":free" suffix is part of the slug and passed through as-is.

    Returns {"uptime": float (0-1), "latency_p50": float | None}, averaged
    over endpoints where pricing.prompt == "0" and pricing.completion == "0".

    Returns None if the request fails, or if no free endpoints are present.
    """
    url = ENDPOINTS_URL_TEMPLATE.format(model_id=model_id)
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
