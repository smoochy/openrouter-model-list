"""Generate models.json: filter, fetch endpoint stats, probe, score, write."""
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from openai import OpenAI

from endpoint_stats import fetch_endpoint_stats
from filters import filter_candidates
from openrouter_client import fetch_models
from probe import HISTORY_DIR, probe_model, read_history, record_probe
from scoring import NEUTRAL_UPTIME, compute_score, compute_uptime, passes_post_probe_filters
from thresholds import load_thresholds

REPO_ROOT = Path(__file__).parent.parent

PROFILES = {
    "mengram": {
        "thresholds_path": REPO_ROOT / "thresholds-mengram.yaml",
        "output_path": REPO_ROOT / "models-mengram.json",
    },
    "yt-summarizer": {
        "thresholds_path": REPO_ROOT / "thresholds-yt-summarizer.yaml",
        "output_path": REPO_ROOT / "models-yt-summarizer.json",
    },
    "openwiki": {
        "thresholds_path": REPO_ROOT / "thresholds-openwiki.yaml",
        "output_path": REPO_ROOT / "models-openwiki.json",
    },
}

SCHEMA_VERSION = 2


def resolve_profile(name: str) -> dict:
    if name not in PROFILES:
        raise ValueError(f"Unknown profile: {name!r}. Choose from: {list(PROFILES)}")
    return PROFILES[name]


def generate(
    *,
    thresholds_path: Path,
    history_dir: Path,
    output_path: Path,
    fetch_models_fn,
    fetch_endpoint_stats_fn,
    probe_model_fn,
    llm_client,
    now: str,
) -> dict:
    thresholds = load_thresholds(thresholds_path)
    api_key = os.environ.get("OPENROUTER_API_KEY", "")

    all_models = fetch_models_fn(api_key)
    candidates = filter_candidates(all_models, thresholds)

    max_context = max((m.get("context_length", 0) for m in candidates), default=0)

    scored = []
    for model in candidates:
        stats = fetch_endpoint_stats_fn(api_key, model["id"])
        if stats is None:
            print(f"warning: no free endpoint stats for {model['id']}", file=sys.stderr)
            or_uptime, or_latency_p50 = NEUTRAL_UPTIME, None
        else:
            or_uptime, or_latency_p50 = stats["uptime"], stats["latency_p50"]

        sanity = probe_model_fn(llm_client, model["id"])
        record_probe(history_dir, model["id"], sanity, now)
        if not sanity["success"]:
            print(f"warning: sanity probe failed for {model['id']}", file=sys.stderr)

        history = read_history(history_dir, model["id"])
        own_uptime = compute_uptime(history)

        if not passes_post_probe_filters(or_uptime, or_latency_p50, thresholds):
            continue

        score = compute_score(model, or_uptime, or_latency_p50, max_context, own_uptime)
        scored.append({
            "id": model["id"],
            "score": round(score, 4),
            "context_length": model.get("context_length", 0),
            "max_output_tokens": model.get("top_provider", {}).get("max_completion_tokens"),
            "uptime": round(or_uptime, 4),
            "latency_ms": int(or_latency_p50) if or_latency_p50 is not None else None,
            "own_uptime": round(own_uptime, 4),
            "sanity_ok": sanity["success"],
        })

    scored.sort(key=lambda m: m["score"], reverse=True)

    output = {
        "generated_at": now,
        "schema_version": SCHEMA_VERSION,
        "models": scored,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
        f.write("\n")

    return output


def main() -> int:
    import argparse
    parser = argparse.ArgumentParser(description="Generate an OpenRouter model list.")
    parser.add_argument(
        "--profile",
        choices=list(PROFILES),
        default="mengram",
        help="Which profile to run (default: mengram)",
    )
    args = parser.parse_args()

    profile = resolve_profile(args.profile)
    api_key = os.environ["OPENROUTER_API_KEY"]
    client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    generate(
        thresholds_path=profile["thresholds_path"],
        history_dir=HISTORY_DIR,
        output_path=profile["output_path"],
        fetch_models_fn=fetch_models,
        fetch_endpoint_stats_fn=fetch_endpoint_stats,
        probe_model_fn=probe_model,
        llm_client=client,
        now=now,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
