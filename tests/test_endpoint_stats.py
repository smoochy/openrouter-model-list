import httpx
import respx

from endpoint_stats import fetch_endpoint_stats


@respx.mock
def test_fetch_endpoint_stats_averages_free_endpoints():
    url = "https://openrouter.ai/api/v1/models/google/gemma-4-31b-it:free/endpoints"
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "endpoints": [
                {
                    "pricing": {"prompt": "0", "completion": "0"},
                    "uptime_last_1d": 100,
                    "latency_last_30m": {"p50": 1000},
                },
                {
                    "pricing": {"prompt": "0", "completion": "0"},
                    "uptime_last_1d": 80,
                    "latency_last_30m": {"p50": 2000},
                },
                {
                    "pricing": {"prompt": "0.001", "completion": "0.002"},
                    "uptime_last_1d": 50,
                    "latency_last_30m": {"p50": 100},
                },
            ]
        }
    }))

    result = fetch_endpoint_stats("test-key", "google/gemma-4-31b-it:free")

    assert result == {"uptime": 0.9, "latency_p50": 1500.0}


@respx.mock
def test_fetch_endpoint_stats_returns_none_when_no_free_endpoints():
    url = "https://openrouter.ai/api/v1/models/paid/model/endpoints"
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "endpoints": [
                {
                    "pricing": {"prompt": "0.001", "completion": "0.002"},
                    "uptime_last_1d": 99,
                    "latency_last_30m": {"p50": 100},
                },
            ]
        }
    }))

    assert fetch_endpoint_stats("test-key", "paid/model") is None


@respx.mock
def test_fetch_endpoint_stats_returns_none_on_http_error():
    url = "https://openrouter.ai/api/v1/models/bad/model:free/endpoints"
    respx.get(url).mock(return_value=httpx.Response(500))

    assert fetch_endpoint_stats("test-key", "bad/model:free") is None


@respx.mock
def test_fetch_endpoint_stats_sends_bearer_auth():
    url = "https://openrouter.ai/api/v1/models/a/b:free/endpoints"
    route = respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "endpoints": [
                {
                    "pricing": {"prompt": "0", "completion": "0"},
                    "uptime_last_1d": 100,
                    "latency_last_30m": {"p50": 100},
                },
            ]
        }
    }))

    fetch_endpoint_stats("test-key", "a/b:free")

    assert route.calls.last.request.headers["authorization"] == "Bearer test-key"


@respx.mock
def test_fetch_endpoint_stats_handles_missing_latency_field():
    url = "https://openrouter.ai/api/v1/models/a/b:free/endpoints"
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "endpoints": [
                {
                    "pricing": {"prompt": "0", "completion": "0"},
                    "uptime_last_1d": 100,
                    "latency_last_30m": {},
                },
            ]
        }
    }))

    result = fetch_endpoint_stats("test-key", "a/b:free")

    assert result == {"uptime": 1.0, "latency_p50": None}


@respx.mock
def test_fetch_endpoint_stats_handles_null_latency_field():
    url = "https://openrouter.ai/api/v1/models/a/b:free/endpoints"
    respx.get(url).mock(return_value=httpx.Response(200, json={
        "data": {
            "endpoints": [
                {
                    "pricing": {"prompt": "0", "completion": "0"},
                    "uptime_last_1d": None,
                    "latency_last_30m": None,
                },
            ]
        }
    }))

    result = fetch_endpoint_stats("test-key", "a/b:free")

    assert result == {"uptime": 0.0, "latency_p50": None}
