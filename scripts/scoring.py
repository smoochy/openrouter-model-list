"""Compute uptime, latency, and overall weighted score for candidate models."""

MIN_SAMPLES_FOR_UPTIME = 3
NEUTRAL_UPTIME = 0.5
LATENCY_CAP_MS = 5000

UPTIME_WEIGHT = 0.6
LATENCY_WEIGHT = 0.3
CAPABILITY_WEIGHT = 0.1


def compute_uptime(history: list[dict]) -> float:
    if len(history) < MIN_SAMPLES_FOR_UPTIME:
        return NEUTRAL_UPTIME
    successes = sum(1 for e in history if e["success"])
    return successes / len(history)


def compute_latency_p50(history: list[dict]) -> float | None:
    latencies = sorted(e["latency_ms"] for e in history if e["success"])
    if not latencies:
        return None
    mid = len(latencies) // 2
    if len(latencies) % 2 == 1:
        return float(latencies[mid])
    return (latencies[mid - 1] + latencies[mid]) / 2


def passes_post_probe_filters(uptime: float, latency_p50: float | None, thresholds: dict) -> bool:
    min_uptime = thresholds.get("min_uptime")
    max_latency = thresholds.get("max_latency_ms")
    if min_uptime is not None and uptime < min_uptime:
        return False
    if max_latency is not None and latency_p50 is not None and latency_p50 > max_latency:
        return False
    return True


def compute_score(
    model: dict,
    or_uptime: float,
    or_latency_p50: float | None,
    max_context: int,
    own_uptime: float,
) -> float:
    """Weighted score from OpenRouter endpoint stats, malused by our own
    daily sanity-probe history.

    base = 0.6*or_uptime + 0.3*latency_norm + 0.1*capability_norm
    return base * own_uptime
    """
    if or_latency_p50 is None:
        latency_norm = 0.0
    else:
        latency_norm = max(0.0, 1 - or_latency_p50 / LATENCY_CAP_MS)

    capability_norm = 0.0
    if max_context > 0:
        capability_norm = model.get("context_length", 0) / max_context

    base = (
        UPTIME_WEIGHT * or_uptime
        + LATENCY_WEIGHT * latency_norm
        + CAPABILITY_WEIGHT * capability_norm
    )
    return base * own_uptime
