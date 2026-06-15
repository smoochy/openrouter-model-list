"""Probe OpenRouter models with a minimal completion request, track history."""
import json
import time
from datetime import datetime, timedelta
from pathlib import Path

HISTORY_DIR = Path(__file__).parent.parent / "history"
HISTORY_WINDOW_DAYS = 30


def probe_model(client, model_id: str) -> dict:
    """Send one minimal completion request, return {success, latency_ms}."""
    start = time.monotonic()
    try:
        client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=1,
        )
        success = True
    except Exception:
        success = False
    latency_ms = int((time.monotonic() - start) * 1000)
    return {"success": success, "latency_ms": latency_ms}


def record_probe(history_dir: Path, model_id: str, result: dict, timestamp: str) -> None:
    """Append a probe result to history/<model>.jsonl, trimmed to the rolling window."""
    history_dir.mkdir(parents=True, exist_ok=True)
    path = _history_path(history_dir, model_id)

    entries = read_history(history_dir, model_id)
    entries.append({"timestamp": timestamp, **result})

    cutoff = _cutoff(timestamp)
    entries = [e for e in entries if e["timestamp"] >= cutoff]

    with open(path, "w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def read_history(history_dir: Path, model_id: str) -> list[dict]:
    path = _history_path(history_dir, model_id)
    if not path.exists():
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _history_path(history_dir: Path, model_id: str) -> Path:
    return history_dir / f"{_safe_filename(model_id)}.jsonl"


def _safe_filename(model_id: str) -> str:
    return model_id.replace("/", "__").replace(":", "__")


def _cutoff(timestamp: str) -> str:
    dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    cutoff_dt = dt - timedelta(days=HISTORY_WINDOW_DAYS)
    return cutoff_dt.isoformat().replace("+00:00", "Z")
