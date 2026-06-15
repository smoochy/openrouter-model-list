import httpx
import respx

from openrouter_client import MODELS_URL, fetch_models


@respx.mock
def test_fetch_models_returns_data_list():
    respx.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json={"data": [{"id": "a/b:free"}]})
    )

    result = fetch_models("test-key")

    assert result == [{"id": "a/b:free"}]


@respx.mock
def test_fetch_models_sends_bearer_auth():
    route = respx.get(MODELS_URL).mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    fetch_models("test-key")

    assert route.calls.last.request.headers["authorization"] == "Bearer test-key"


@respx.mock
def test_fetch_models_raises_on_http_error():
    respx.get(MODELS_URL).mock(return_value=httpx.Response(500))

    try:
        fetch_models("test-key")
        assert False, "expected HTTPStatusError"
    except httpx.HTTPStatusError:
        pass
