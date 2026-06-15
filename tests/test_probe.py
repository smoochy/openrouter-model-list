import json

from probe import probe_model, read_history, record_probe


class FakeCompletions:
    def __init__(self, should_fail):
        self.should_fail = should_fail

    def create(self, **kwargs):
        if self.should_fail:
            raise RuntimeError("model unavailable")
        return object()


class FakeChat:
    def __init__(self, should_fail):
        self.completions = FakeCompletions(should_fail)


class FakeClient:
    def __init__(self, should_fail=False):
        self.chat = FakeChat(should_fail)


def test_probe_model_success():
    result = probe_model(FakeClient(should_fail=False), "good/model:free")

    assert result["success"] is True
    assert isinstance(result["latency_ms"], int)
    assert result["latency_ms"] >= 0


def test_probe_model_failure():
    result = probe_model(FakeClient(should_fail=True), "bad/model:free")

    assert result["success"] is False
    assert isinstance(result["latency_ms"], int)


def test_record_and_read_history_roundtrip(tmp_path):
    record_probe(tmp_path, "a/model:free", {"success": True, "latency_ms": 100}, "2026-06-14T00:00:00Z")
    record_probe(tmp_path, "a/model:free", {"success": False, "latency_ms": 5000}, "2026-06-14T01:00:00Z")

    history = read_history(tmp_path, "a/model:free")

    assert len(history) == 2
    assert history[0] == {"timestamp": "2026-06-14T00:00:00Z", "success": True, "latency_ms": 100}
    assert history[1]["success"] is False


def test_record_probe_trims_entries_older_than_30_days(tmp_path):
    record_probe(tmp_path, "a/model:free", {"success": True, "latency_ms": 100}, "2026-01-01T00:00:00Z")
    record_probe(tmp_path, "a/model:free", {"success": True, "latency_ms": 200}, "2026-06-14T00:00:00Z")

    history = read_history(tmp_path, "a/model:free")

    assert len(history) == 1
    assert history[0]["timestamp"] == "2026-06-14T00:00:00Z"


def test_read_history_returns_empty_list_when_no_file(tmp_path):
    assert read_history(tmp_path, "missing/model:free") == []


def test_record_probe_uses_safe_filename(tmp_path):
    record_probe(tmp_path, "org/name:free", {"success": True, "latency_ms": 1}, "2026-06-14T00:00:00Z")

    assert (tmp_path / "org__name__free.jsonl").exists()
