from thresholds import load_thresholds


def test_load_thresholds_reads_all_fields(tmp_path):
    path = tmp_path / "thresholds.yaml"
    path.write_text(
        "min_param_b: 28\n"
        "min_context_length: 40000\n"
        "min_max_output_tokens: 8000\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 3\n"
        "allowlist:\n"
        "  - openrouter/owl-alpha\n"
    )

    result = load_thresholds(path)

    assert result == {
        "min_param_b": 28,
        "min_context_length": 40000,
        "min_max_output_tokens": 8000,
        "buffer_pct": 5,
        "require_structured_output": True,
        "min_uptime": None,
        "max_latency_ms": None,
        "min_candidate_pool": 3,
        "allowlist": ["openrouter/owl-alpha"],
        "hardallowlist": [],
    }


def test_load_thresholds_applies_defaults_for_missing_keys(tmp_path):
    path = tmp_path / "thresholds.yaml"
    path.write_text("min_param_b: 16\n")

    result = load_thresholds(path)

    assert result["min_param_b"] == 16
    assert result["min_context_length"] == 40000
    assert result["min_max_output_tokens"] == 8000
    assert result["buffer_pct"] == 5
    assert result["require_structured_output"] is True
    assert result["min_uptime"] is None
    assert result["max_latency_ms"] is None
    assert result["min_candidate_pool"] == 3
    assert result["allowlist"] == []
    assert result["hardallowlist"] == []


def test_load_thresholds_with_uptime_and_latency_set(tmp_path):
    path = tmp_path / "thresholds.yaml"
    path.write_text("min_uptime: 0.9\nmax_latency_ms: 2000\n")

    result = load_thresholds(path)

    assert result["min_uptime"] == 0.9
    assert result["max_latency_ms"] == 2000
