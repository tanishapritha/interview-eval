from __future__ import annotations

import math
import random
from collections.abc import Sequence


def mean(values: Sequence[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def stdev(values: Sequence[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = mean(values)
    return math.sqrt(sum((value - avg) ** 2 for value in values) / (len(values) - 1))


def percentile(values: Sequence[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = (len(ordered) - 1) * percentile_value / 100
    lower = math.floor(index)
    upper = math.ceil(index)
    if lower == upper:
        return float(ordered[lower])
    return float(ordered[lower] * (upper - index) + ordered[upper] * (index - lower))


def bootstrap_mean_interval(
    values: Sequence[float], confidence: float = 0.95, samples: int = 2000, seed: int = 7
) -> tuple[float, float]:
    """Percentile bootstrap interval; interpret cautiously for small samples."""
    if not values:
        return (0.0, 0.0)
    rng = random.Random(seed)
    estimates = [mean([rng.choice(values) for _ in values]) for _ in range(samples)]
    tail = (1 - confidence) * 50
    return percentile(estimates, tail), percentile(estimates, 100 - tail)
