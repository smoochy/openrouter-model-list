from scoring import compute_latency_p50, compute_score, compute_uptime, passes_post_probe_filters


def test_compute_uptime_returns_neutral_with_few_samples():
    history = [{"success": True, "latency_ms": 100}]
    assert compute_uptime(history) == 0.5


def test_compute_uptime_returns_success_ratio_with_enough_samples():
    history = [
        {"success": True, "latency_ms": 100},
        {"success": True, "latency_ms": 100},
        {"success": False, "latency_ms": 5000},
        {"success": True, "latency_ms": 100},
    ]
    assert compute_uptime(history) == 0.75


def test_compute_latency_p50_uses_successful_entries_only():
    history = [
        {"success": True, "latency_ms": 100},
        {"success": True, "latency_ms": 200},
        {"success": False, "latency_ms": 9999},
    ]
    assert compute_latency_p50(history) == 150


def test_compute_latency_p50_returns_none_with_no_successes():
    history = [{"success": False, "latency_ms": 9999}]
    assert compute_latency_p50(history) is None


def test_passes_post_probe_filters_disabled_by_default():
    thresholds = {"min_uptime": None, "max_latency_ms": None}
    assert passes_post_probe_filters(0.0, None, thresholds) is True


def test_passes_post_probe_filters_enforces_min_uptime():
    thresholds = {"min_uptime": 0.9, "max_latency_ms": None}
    assert passes_post_probe_filters(0.95, 100, thresholds) is True
    assert passes_post_probe_filters(0.5, 100, thresholds) is False


def test_passes_post_probe_filters_enforces_max_latency():
    thresholds = {"min_uptime": None, "max_latency_ms": 1000}
    assert passes_post_probe_filters(1.0, 500, thresholds) is True
    assert passes_post_probe_filters(1.0, 2000, thresholds) is False


def test_compute_score_weights_uptime_highest():
    model = {"context_length": 50000}
    high_uptime = compute_score(
        model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    low_uptime = compute_score(
        model, or_uptime=0.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    assert high_uptime > low_uptime


def test_compute_score_treats_no_successful_probes_as_worst_latency():
    model = {"context_length": 50000}
    with_latency = compute_score(
        model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    without_latency = compute_score(
        model, or_uptime=1.0, or_latency_p50=None, max_context=100000, own_uptime=1.0
    )
    assert with_latency > without_latency


def test_compute_score_capability_uses_relative_context():
    small_model = {"context_length": 50000}
    large_model = {"context_length": 100000}
    small_score = compute_score(
        small_model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    large_score = compute_score(
        large_model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    assert large_score > small_score


def test_compute_score_own_uptime_malus_scales_score():
    model = {"context_length": 50000}
    full = compute_score(
        model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=1.0
    )
    halved = compute_score(
        model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=0.5
    )
    zeroed = compute_score(
        model, or_uptime=1.0, or_latency_p50=1000, max_context=100000, own_uptime=0.0
    )
    assert halved == full * 0.5
    assert zeroed == 0.0
