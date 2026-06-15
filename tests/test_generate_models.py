"""Tests for generate_models.generate()."""
import json

from generate_models import generate
from scoring import NEUTRAL_UPTIME


def make_model(id, context_length=40000, max_completion_tokens=8000, supported_parameters=None, free=True):
    return {
        "id": id,
        "context_length": context_length,
        "pricing": {"prompt": "0" if free else "0.001", "completion": "0" if free else "0.002"},
        "top_provider": {"max_completion_tokens": max_completion_tokens},
        "supported_parameters": supported_parameters or ["response_format"],
    }


CATALOG = [
    make_model("good/model-32b:free"),
    make_model("tiny/model-7b:free"),  # excluded by 32B min_param_b floor
    make_model("bad/model-70b:free", context_length=131072, max_completion_tokens=32768),
]


def fake_fetch_models(api_key):
    return CATALOG


def fake_fetch_endpoint_stats(api_key, model_id):
    return {
        "good/model-32b:free": {"uptime": 1.0, "latency_p50": 100},
        "bad/model-70b:free": {"uptime": 0.5, "latency_p50": 2000},
    }.get(model_id)


def fake_probe_model(client, model_id):
    if model_id == "bad/model-70b:free":
        return {"success": False, "latency_ms": None}
    return {"success": True, "latency_ms": 50}


def test_generate_writes_models_json_sorted_by_score(tmp_path):
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "min_param_b: 32\n"
        "min_context_length: 38000\n"
        "min_max_output_tokens: 7600\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 1\n"
        "allowlist: []\n"
    )
    history_dir = tmp_path / "history"
    output_path = tmp_path / "models.json"

    output = generate(
        thresholds_path=thresholds_path,
        history_dir=history_dir,
        output_path=output_path,
        fetch_models_fn=fake_fetch_models,
        fetch_endpoint_stats_fn=fake_fetch_endpoint_stats,
        probe_model_fn=fake_probe_model,
        llm_client=None,
        now="2026-06-14T03:00:00Z",
    )

    assert output["schema_version"] == 2
    ids = [m["id"] for m in output["models"]]
    assert "tiny/model-7b:free" not in ids
    assert ids[0] == "good/model-32b:free"

    with open(output_path) as f:
        written = json.load(f)
    assert written == output


def test_generate_writes_probe_history(tmp_path):
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "min_param_b: 32\n"
        "min_context_length: 38000\n"
        "min_max_output_tokens: 7600\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 1\n"
        "allowlist: []\n"
    )
    history_dir = tmp_path / "history"
    output_path = tmp_path / "models.json"

    generate(
        thresholds_path=thresholds_path,
        history_dir=history_dir,
        output_path=output_path,
        fetch_models_fn=fake_fetch_models,
        fetch_endpoint_stats_fn=fake_fetch_endpoint_stats,
        probe_model_fn=fake_probe_model,
        llm_client=None,
        now="2026-06-14T03:00:00Z",
    )

    history_files = list(history_dir.glob("*.jsonl"))
    assert len(history_files) >= 1


def test_generate_includes_own_uptime_and_sanity_ok(tmp_path):
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "min_param_b: 32\n"
        "min_context_length: 38000\n"
        "min_max_output_tokens: 7600\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 1\n"
        "allowlist: []\n"
    )
    history_dir = tmp_path / "history"
    output_path = tmp_path / "models.json"

    output = generate(
        thresholds_path=thresholds_path,
        history_dir=history_dir,
        output_path=output_path,
        fetch_models_fn=fake_fetch_models,
        fetch_endpoint_stats_fn=fake_fetch_endpoint_stats,
        probe_model_fn=fake_probe_model,
        llm_client=None,
        now="2026-06-14T03:00:00Z",
    )

    by_id = {m["id"]: m for m in output["models"]}
    assert by_id["good/model-32b:free"]["own_uptime"] == NEUTRAL_UPTIME
    assert by_id["good/model-32b:free"]["sanity_ok"] is True
    assert by_id["bad/model-70b:free"]["sanity_ok"] is False


def test_generate_logs_warning_for_missing_endpoint_stats(tmp_path, capsys):
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "min_param_b: 32\n"
        "min_context_length: 38000\n"
        "min_max_output_tokens: 7600\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 1\n"
        "allowlist: []\n"
    )
    history_dir = tmp_path / "history"
    output_path = tmp_path / "models.json"

    def fetch_stats_missing(api_key, model_id):
        return None

    output = generate(
        thresholds_path=thresholds_path,
        history_dir=history_dir,
        output_path=output_path,
        fetch_models_fn=fake_fetch_models,
        fetch_endpoint_stats_fn=fetch_stats_missing,
        probe_model_fn=fake_probe_model,
        llm_client=None,
        now="2026-06-14T03:00:00Z",
    )

    captured = capsys.readouterr()
    assert "no free endpoint stats for good/model-32b:free" in captured.err

    by_id = {m["id"]: m for m in output["models"]}
    assert by_id["good/model-32b:free"]["uptime"] == NEUTRAL_UPTIME
    assert by_id["good/model-32b:free"]["latency_ms"] is None


def test_generate_logs_warning_for_failed_sanity_probe(tmp_path, capsys):
    thresholds_path = tmp_path / "thresholds.yaml"
    thresholds_path.write_text(
        "min_param_b: 32\n"
        "min_context_length: 38000\n"
        "min_max_output_tokens: 7600\n"
        "buffer_pct: 5\n"
        "require_structured_output: true\n"
        "min_uptime:\n"
        "max_latency_ms:\n"
        "min_candidate_pool: 1\n"
        "allowlist: []\n"
    )
    history_dir = tmp_path / "history"
    output_path = tmp_path / "models.json"

    generate(
        thresholds_path=thresholds_path,
        history_dir=history_dir,
        output_path=output_path,
        fetch_models_fn=fake_fetch_models,
        fetch_endpoint_stats_fn=fake_fetch_endpoint_stats,
        probe_model_fn=fake_probe_model,
        llm_client=None,
        now="2026-06-14T03:00:00Z",
    )

    captured = capsys.readouterr()
    assert "sanity probe failed for bad/model-70b:free" in captured.err
