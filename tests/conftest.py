def make_model(
    id,
    context_length=100000,
    max_completion_tokens=10000,
    supported_parameters=None,
    free=True,
):
    pricing = {"prompt": "0", "completion": "0"} if free else {
        "prompt": "0.000001",
        "completion": "0.000002",
    }
    return {
        "id": id,
        "context_length": context_length,
        "top_provider": {"max_completion_tokens": max_completion_tokens},
        "supported_parameters": (
            supported_parameters if supported_parameters is not None else ["response_format"]
        ),
        "pricing": pricing,
    }
