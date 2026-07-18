from conftest import make_model
from filters import filter_candidates, is_free, parse_param_count, supports_structured_output, supports_tools
from thresholds import DEFAULTS


def test_parse_param_count_extracts_b_suffix():
    assert parse_param_count("qwen/qwen3-32b:free") == 32.0
    assert parse_param_count("meta-llama/llama-3.1-70b-instruct:free") == 70.0


def test_parse_param_count_returns_none_when_unparseable():
    assert parse_param_count("openrouter/owl-alpha") is None
    assert parse_param_count("qwen/qwen3.6-plus:free") is None


def test_is_free_checks_zero_pricing():
    assert is_free(make_model("a/b:free", free=True)) is True
    assert is_free(make_model("a/b", free=False)) is False


def test_supports_structured_output():
    assert supports_structured_output(make_model("a/b", supported_parameters=["response_format"])) is True
    assert supports_structured_output(make_model("a/b", supported_parameters=["tools"])) is False


def test_supports_tools():
    assert supports_tools(make_model("a/b", supported_parameters=["tools"])) is True
    assert supports_tools(make_model("a/b", supported_parameters=["tool_choice"])) is True
    assert supports_tools(make_model("a/b", supported_parameters=["response_format"])) is False


def test_filter_candidates_requires_tools_when_configured():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["require_structured_output"] = False
    thresholds["require_tools"] = True

    models = [
        make_model("tooled/model-32b:free", supported_parameters=["tools"]),
        make_model("untooled/model-32b:free", supported_parameters=["response_format"]),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert ids == ["tooled/model-32b:free"]


def test_filter_candidates_allowlist_excludes_missing_tools_with_warning(capsys):
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["require_structured_output"] = False
    thresholds["require_tools"] = True
    thresholds["allowlist"] = ["no-tools/model"]

    models = [
        make_model("no-tools/model", context_length=1000, max_completion_tokens=1, supported_parameters=[]),
    ]

    result = filter_candidates(models, thresholds)

    assert result == []
    captured = capsys.readouterr()
    assert "allowlisted model no-tools/model excluded: missing tool-calling support" in captured.err


def test_filter_candidates_applies_param_floor_without_buffer():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0

    models = [
        make_model("big/model-32b:free", context_length=50000, max_completion_tokens=9000),
        make_model("small/model-7b:free", context_length=50000, max_completion_tokens=9000),
        make_model("unsized/model:free", context_length=50000, max_completion_tokens=9000),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "big/model-32b:free" in ids
    assert "small/model-7b:free" not in ids
    assert "unsized/model:free" not in ids


def test_filter_candidates_excludes_non_free_models():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0

    models = [
        make_model("free/model-32b:free", context_length=50000, max_completion_tokens=9000, free=True),
        make_model("paid/model-32b", context_length=50000, max_completion_tokens=9000, free=False),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "free/model-32b:free" in ids
    assert "paid/model-32b" not in ids


def test_filter_candidates_applies_buffer_to_context_and_output():
    thresholds = dict(DEFAULTS)
    thresholds["min_context_length"] = 40000
    thresholds["min_max_output_tokens"] = 8000
    thresholds["buffer_pct"] = 12  # buffered min_context = 44800, min_output = 8960
    thresholds["min_candidate_pool"] = 0

    models = [
        make_model("ok/model-32b:free", context_length=45000, max_completion_tokens=9000),
        make_model("toosmallctx/model-32b:free", context_length=44000, max_completion_tokens=9000),
        make_model("toosmallout/model-32b:free", context_length=45000, max_completion_tokens=8500),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert ids == ["ok/model-32b:free"]


def test_filter_candidates_requires_structured_output_when_configured():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["require_structured_output"] = True

    models = [
        make_model("supported/model-32b:free", supported_parameters=["response_format"]),
        make_model("unsupported/model-32b:free", supported_parameters=["tools"]),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert ids == ["supported/model-32b:free"]


def test_filter_candidates_relaxes_buffer_until_min_pool_met():
    thresholds = dict(DEFAULTS)
    thresholds["min_context_length"] = 40000
    thresholds["min_max_output_tokens"] = 8000
    thresholds["buffer_pct"] = 12  # 44800 / 8960 at full buffer
    thresholds["min_candidate_pool"] = 2

    # Both models have context_length=41000: fails at buffer_pct=12 (need
    # >=44800) but passes once buffer_pct drops to 0 (need >=40000).
    models = [
        make_model("a/model-32b:free", context_length=41000, max_completion_tokens=9000),
        make_model("b/model-32b:free", context_length=41000, max_completion_tokens=9000),
    ]

    result = filter_candidates(models, thresholds)

    assert len(result) == 2


def test_filter_candidates_treats_missing_max_output_tokens_as_unknown():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0

    models = [
        make_model("a/model-32b:free", context_length=50000, max_completion_tokens=None),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "a/model-32b:free" in ids


def test_filter_candidates_allowlist_bypasses_size_and_context():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["allowlist"] = ["openrouter/owl-alpha"]

    models = [
        make_model("openrouter/owl-alpha", context_length=1000, max_completion_tokens=1, supported_parameters=["response_format"]),
        make_model("small/model-7b:free", context_length=50000, max_completion_tokens=9000),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "openrouter/owl-alpha" in ids
    assert "small/model-7b:free" not in ids


def test_filter_candidates_allowlist_excludes_missing_structured_output_with_warning(capsys):
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["require_structured_output"] = True
    thresholds["allowlist"] = ["no-struct/model"]

    models = [
        make_model("no-struct/model", context_length=1000, max_completion_tokens=1, supported_parameters=[]),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "no-struct/model" not in ids

    captured = capsys.readouterr()
    assert "allowlisted model no-struct/model excluded: missing structured-output support" in captured.err


def test_filter_candidates_hardallowlist_bypasses_all_filters_including_structured_output():
    thresholds = dict(DEFAULTS)
    thresholds["buffer_pct"] = 0
    thresholds["require_structured_output"] = True
    thresholds["hardallowlist"] = ["legacy/model"]

    models = [
        make_model("legacy/model", context_length=1000, max_completion_tokens=1, supported_parameters=[]),
        make_model("small/model-7b:free", context_length=50000, max_completion_tokens=9000),
    ]

    result = filter_candidates(models, thresholds)

    ids = [m["id"] for m in result]
    assert "legacy/model" in ids
    assert "small/model-7b:free" not in ids
