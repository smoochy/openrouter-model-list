"""Load thresholds-mengram.yaml with defaults for missing keys."""
from pathlib import Path

import yaml

DEFAULT_THRESHOLDS_PATH = Path(__file__).parent.parent / "thresholds-mengram.yaml"

DEFAULTS = {
    "min_param_b": 28,
    "min_context_length": 40000,
    "min_max_output_tokens": 8000,
    "buffer_pct": 5,
    "require_structured_output": True,
    "require_tools": False,
    "min_uptime": None,
    "max_latency_ms": None,
    "min_candidate_pool": 3,
    "allowlist": [],
    "hardallowlist": [],
}


def load_thresholds(path: Path = DEFAULT_THRESHOLDS_PATH) -> dict:
    with open(path) as f:
        data = yaml.safe_load(f) or {}

    return {key: data.get(key, default) for key, default in DEFAULTS.items()}
