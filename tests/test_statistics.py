from interview_eval.statistics import bootstrap_mean_interval, percentile, stdev


def test_percentile_interpolates():
    assert percentile([0, 10], 50) == 5


def test_sample_standard_deviation():
    assert round(stdev([2, 4, 6]), 5) == 2


def test_bootstrap_interval_is_reproducible():
    values = [1, 2, 3, 4, 5]
    assert bootstrap_mean_interval(values) == bootstrap_mean_interval(values)
