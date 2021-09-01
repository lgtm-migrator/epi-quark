import json

import pandas as pd
import pytest
from scorer import Score
from sklearn import metrics


@pytest.fixture
def paper_example_score(shared_datadir) -> Score:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")
    return Score(cases, signals)


def test_non_case_imputation(shared_datadir, paper_example_score: Score) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    imputed = paper_example_score._impute_non_case(cases)

    imputed_expected = pd.read_csv(shared_datadir / "paper_example/non_case_imputed_long.csv")
    pd.testing.assert_frame_equal(imputed, imputed_expected, check_dtype=False)


def test_signal_imputation(shared_datadir, paper_example_score: Score) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/non_case_imputed_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/signals_long.csv")

    imputed = paper_example_score._impute_signals(signals, cases, "min")
    imputed_expected = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")
    pd.testing.assert_frame_equal(imputed, imputed_expected, check_dtype=False)


def test_p_di_given_x(shared_datadir, paper_example_score: Score) -> None:
    p_di_given_x = paper_example_score._p_di_given_x()
    p_di_given_x_expected = pd.read_csv(shared_datadir / "paper_example/p_di_given_x.csv")
    pd.testing.assert_frame_equal(p_di_given_x, p_di_given_x_expected, check_dtype=False)


def test_p_hat_sj_given_x(shared_datadir, paper_example_score: Score) -> None:
    p_hat_sj_given_x = paper_example_score._p_hat_sj_given_x()
    p_hat_sj_given_x_expected = pd.read_csv(
        shared_datadir / "paper_example/p_hat_sj_given_x_long.csv"
    )
    pd.testing.assert_frame_equal(p_hat_sj_given_x, p_hat_sj_given_x_expected, check_dtype=False)


def test_p_hat_di_given_sj_x(shared_datadir, paper_example_score: Score) -> None:
    p_hat_di_given_sj_x = paper_example_score._p_hat_di_given_sj_x()
    p_hat_di_given_sj_x_expected = pd.read_csv(
        shared_datadir / "paper_example/p_hat_di_given_sj_x.csv"
    )
    str_cols = list(p_hat_di_given_sj_x.select_dtypes(exclude="number").columns)
    pd.testing.assert_frame_equal(
        p_hat_di_given_sj_x.sort_values(by=str_cols).reset_index(drop=True),
        p_hat_di_given_sj_x_expected.sort_values(by=str_cols).reset_index(drop=True),
        check_dtype=False,
    )


def test_p_hat_di(shared_datadir, paper_example_score: Score) -> None:
    p_hat_di = (
        paper_example_score.p_hat_di().sort_values(by=["x1", "x2", "d_i"]).reset_index(drop=True)
    )
    p_hat_di_expected = (
        pd.read_csv(shared_datadir / "paper_example/p_hat_di.csv")
        .sort_values(by=["x1", "x2", "d_i"])
        .reset_index(drop=True)
    )
    pd.testing.assert_frame_equal(
        p_hat_di,
        p_hat_di_expected,
        check_dtype=False,
    )


def test_eval_df(shared_datadir, paper_example_score: Score) -> None:
    eval_df = paper_example_score.eval_df()
    eval_df_expected = pd.read_csv(shared_datadir / "paper_example/eval_df.csv")
    pd.testing.assert_frame_equal(eval_df, eval_df_expected, check_dtype=False)


def test_timeliness(shared_datadir) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")
    s = Score(cases, signals)

    timeliness = s.timeliness("x2", 4)
    timeliness_expected = {"three": 1.0, "two": 0.5, "one": 1.0}
    assert timeliness == timeliness_expected


def test_mean_score(paper_example_score: Score) -> None:
    scores = paper_example_score.mean_score(metrics.f1_score)
    assert scores == (
        0.5175213675213676,
        0.7006081525312294,
    )


def test_case_data_error(shared_datadir) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")

    cases.loc[2, "value"] = pd.NA
    with pytest.raises(ValueError):
        Score(cases, signals)

    cases.at[2, "value"] = -1
    with pytest.raises(ValueError):
        Score(cases, signals)

    cases.at[2, "value"] = 2.7
    with pytest.raises(ValueError):
        Score(cases, signals)

    cases.at[0, "data_label"] = "non_case"
    with pytest.raises(ValueError):
        Score(cases, signals)


def test_signal_coord_error(shared_datadir) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")

    signals.at[0, "x1"] = 6
    with pytest.raises(
        ValueError, match="Coordinats of 'signals' must be a subset of coordinats of 'cases'."
    ):
        Score(cases, signals)


def test_signals_float_error(shared_datadir) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")

    signals_negative_value = signals.copy()
    signals_negative_value.at[0, "value"] = -1.2
    with pytest.raises(
        ValueError, match="'values' in signal DataFrame must be floats between 0 and 1."
    ):
        Score(cases, signals_negative_value)

    signals_high_values = signals.copy()
    signals_high_values.at[0, "value"] = 2.0
    with pytest.raises(
        ValueError, match="'values' in signal DataFrame must be floats between 0 and 1."
    ):
        Score(cases, signals_high_values)

    signals_not_float = signals.copy()
    signals_not_float.loc[:, "value"] = 1
    with pytest.raises(
        ValueError, match="'values' in signal DataFrame must be floats between 0 and 1."
    ):
        Score(cases, signals_not_float)


def test_signals_equal_number_error(shared_datadir) -> None:
    cases = pd.read_csv(shared_datadir / "paper_example/cases_long.csv")
    signals = pd.read_csv(shared_datadir / "paper_example/imputed_signals_long.csv")

    signals = signals.iloc[1:]
    with pytest.raises(
        ValueError, match="Each coordinate must contain the same amount of signals."
    ):
        Score(cases, signals)


def test_class_based_conf_mat(paper_example_score: Score) -> None:
    confusion_matrix = paper_example_score.class_based_conf_mat()
    confusion_matrix_expected = {
        "endemic": [[16, 4], [1, 4]],
        "non_case": [[13, 0], [0, 12]],
        "one": [[20, 2], [0, 3]],
        "three": [[18, 5], [2, 0]],
        "two": [[17, 4], [3, 1]],
    }
    assert json.dumps(confusion_matrix, sort_keys=True) == json.dumps(
        confusion_matrix_expected, sort_keys=True
    )

    confusion_matrix_weighted = paper_example_score.class_based_conf_mat(weighted=True)
    confusion_matrix_weighted_expected = {
        "endemic": [[20, 4], [1, 4]],
        "non_case": [[13, 0], [0, 12]],
        "one": [[20, 2], [0, 3]],
        "three": [[19, 5], [2, 0]],
        "two": [[17, 4], [3, 1]],
    }
    assert json.dumps(confusion_matrix_weighted, sort_keys=True) == json.dumps(
        confusion_matrix_weighted_expected, sort_keys=True
    )
