"""Fetch the OpenRouter model catalog."""
import httpx

MODELS_URL = "https://openrouter.ai/api/v1/models"


def fetch_models(api_key: str) -> list[dict]:
    response = httpx.get(
        MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["data"]
