from os import makedirs
import numpy as np
import pandas as pd
import pytest
from scorer import EpiMetrics, Score


@pytest.fixture
def paper_example_epimetric(shared_datadir) -> Score:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")
    return EpiMetrics(cases, signals)


def test_timeliness(paper_example_epimetric: EpiMetrics) -> None:
    timeliness = paper_example_epimetric.timeliness("x2", 4)
    timeliness_expected = pd.Series(
        [0.0, 0.0, 0.0], index=pd.Index(["one", "three", "two"], name="data_label")
    )
    pd.testing.assert_series_equal(timeliness, timeliness_expected)


def test_calc_delay() -> None:
    delay_3 = pd.DataFrame({"value_cases": [0, 0, 0], "value_signals": [0, 0, 1]})
    assert 3 == EpiMetrics._calc_delay(delay_3)
    delay_3 = pd.DataFrame({"value_cases": [0, 0, 1], "value_signals": [0, 0, 0]})
    assert 3 == EpiMetrics._calc_delay(delay_3)
    delay_3 = pd.DataFrame({"value_cases": [0, 0, 0], "value_signals": [0, 0, 0]})
    assert 3 == EpiMetrics._calc_delay(delay_3)
    delay_3 = pd.DataFrame({"value_cases": [0, 1, 0], "value_signals": [1, 0, 0]})
    assert 3 == EpiMetrics._calc_delay(delay_3)

    delay_2 = pd.DataFrame({"value_cases": [1, 0, 0], "value_signals": [0, 0, 1]})
    assert 2 == EpiMetrics._calc_delay(delay_2)
    delay_2 = pd.DataFrame({"value_cases": [1, 0, 1], "value_signals": [0, 0, 1]})
    assert 2 == EpiMetrics._calc_delay(delay_2)

    delay_1 = pd.DataFrame({"value_cases": [0, 1, 1], "value_signals": [0, 0, 1]})
    assert 1 == EpiMetrics._calc_delay(delay_1)
    delay_1 = pd.DataFrame({"value_cases": [1, 1, 1], "value_signals": [0, 1, 1]})
    assert 1 == EpiMetrics._calc_delay(delay_1)

    delay_0 = pd.DataFrame({"value_cases": [0, 1, 0], "value_signals": [0, 1, 1]})
    assert 0 == EpiMetrics._calc_delay(delay_0)
    delay_0 = pd.DataFrame({"value_cases": [1, 1, 0], "value_signals": [1, 1, 1]})
    assert 0 == EpiMetrics._calc_delay(delay_0)


def test_time_masking(shared_datadir, paper_example_epimetric) -> None:
    time_mask = paper_example_epimetric._time_mask("x2").reset_index(drop=True)
    expected = pd.read_csv(shared_datadir / "paper_example/time_masking.csv")
    pd.testing.assert_frame_equal(time_mask, expected)


def test_gauss_weighting(shared_datadir, paper_example_epimetric: EpiMetrics) -> None:
    gauss_weights = paper_example_epimetric.gauss_weighting(["x1", "x2"])
    expected = pd.read_csv(shared_datadir / "paper_example/gauss_weights.csv")
    pd.testing.assert_frame_equal(gauss_weights, expected)

    gauss_weights = paper_example_epimetric.gauss_weighting(
        ["x1", "x2"],np.diag(np.ones(2))
    )
    expected = pd.read_csv(shared_datadir / "paper_example/gauss_weights.csv")
    pd.testing.assert_frame_equal(gauss_weights, expected)

    gauss_weights = paper_example_epimetric.gauss_weighting(["x1", "x2"], time_axis="x2")
    expected = pd.read_csv(shared_datadir / "paper_example/gauss_weights_timemask.csv")
    pd.testing.assert_frame_equal(gauss_weights, expected)
