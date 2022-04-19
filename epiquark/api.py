from dataclasses import dataclass
from typing import Optional, Union

import numpy as np
import pandas as pd
import sklearn.metrics as sk_metrics

from .scorer import ScoreCalculator, Timeliness


@dataclass
class _ThreshRequired:
    p_thresh: bool
    p_hat_thresh: bool

    def check_threshs_correct(
        self, p_thresh: Optional[float], p_hat_thresh: Optional[float]
    ) -> None:
        actual = (p_thresh is not None, p_hat_thresh is not None)
        threshs_correct = actual == (self.p_thresh, self.p_hat_thresh)
        if not threshs_correct:
            raise ValueError(
                (
                    f"This metric {self._thresh_text(self.p_thresh)} p_thresh "
                    f"and {self._thresh_text(self.p_hat_thresh)} p_hat_thresh."
                )
            )

    def _thresh_text(self, thresh: bool):
        if thresh:
            thresh_text = "requires"
        else:
            thresh_text = "must not contain"
        return thresh_text


def score(
    cases: pd.DataFrame,
    signals: pd.DataFrame,
    metric: str,
    threshold_true: Optional[float] = None,
    threshold_pred: Optional[float] = None,
    weighting: Optional[Union[str, np.ndarray]] = None,
    time_space_weighting: dict[str, float] = None,
    time_axis: Optional[str] = None,
):
    r"""Calculates epidemiologically meaningful scores.

    Given case count data of infectious diseases, information on cases linked through an
    outbreak, signals for outbreaks generated by outbreak detection algorithms, and
    a metric, a cell-grid-based score is calculated.

    This score can also be weighted by spatial-temporal accuracy or by the number of
    cases.


    Args:
        cases: This DataFrame must contain the following columns and no NaNs:

            - ``data_label``. Is the class per outbreak. Must contain ``endemic``
              and must not contain ``non-case``.
            - ``value``. This is the amount of cases in the respective cell.
              This value must be an positive integer.
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. This coordinate system is
              the evaluation resolution.

        signals: This DataFrame must contain the following columns:

            - ``signal_label``. Is the class per signal. Must contain ``endemic`` and
              ``non-case``.
            - ``value``. This is the signal strength :math:`w` and should be :math:`w \in [0,1]`
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. Cases coordinates and cells
              must be subset of cases coordinates and cells. Cells outside
              the coordinate system of the cases DataFrame are ignored.

        metric: Specifies metric to compare :math:`p(d_i|x)` and :math:`\hat{p}(d_i|x)`.
        Possible options are:

            - `'f1'`
            - `'brier'`
            - `'auc'` (area under the curve)
            - `'sensitivity'`
            - `'recall'`
            - `'tpr'` (true positive rate)
            - `'specificity'`
            - `'tnr'` (true negative rate)
            - `'fpr'` (false positive rate)
            - `'fnr'` (false negative rate)
            - `'precision'`
            - `'ppv'` (positive predictive value)
            - `'npv'` (negative predictive value)
            - `'matthews'`
            - `'r2'`
            - `'mse'` (mean squared error)
            - `'mae'` (mean absolute error)
        threshold_true: To binarize :math:`p(d_i|x)`, the true probability per disease given cell.
        threshold_pred: To binarize :math:`\hat{p}(d_i|x)`, the predicted
                        probability per disease given cell.
        weighting: Assigns weight to :math:`p(d_i|x)` and :math:`\hat{p}(d_i|x)` by either
                 'cases' or 'timespace'. If None, no weighting is applied. You can use
                 a 1-D numpy array where each entry is the weighting per cell in the same
                 order as the `cases` DataFrame
        gauss_dims: Only valid if weight is 'timespace'. Assigns over which coordinate cells
                    spatial weighting should happen.
        covariance_diag: Only valid if weight is 'timespace'.
                         Specifies the n-dim. Gaussian covariance.
        time_axis: Only valid if weight is 'timespace'. Assigns over which coordinates
                   temporal weighting should happen.

    Returns:
        Scores per ``data_label``.
    """
    _check_threshs(metric, threshold_true, threshold_pred)
    metrics = {
        "f1": sk_metrics.f1_score,
        "brier": sk_metrics.brier_score_loss,
        "auc": _auc,
        "sensitivity": _sensitivity,
        "recall": _sensitivity,
        "tpr": _sensitivity,
        "specificity": _specificity,
        "tnr": _specificity,
        "fpr": _fpr,
        "fnr": _fnr,
        "precision": _precision,
        "ppv": _precision,
        "npv": _npv,
        "matthews": sk_metrics.matthews_corrcoef,
        "r2": sk_metrics.r2_score,
        "mse": sk_metrics.mean_squared_error,
        "mae": sk_metrics.mean_absolute_error,
    }
    return ScoreCalculator(cases, signals).calc_score(
        scorer=metrics[metric],
        p_thresh=threshold_true,
        p_hat_thresh=threshold_pred,
        weighting=weighting,
        time_space_weighting=time_space_weighting,
        time_axis=time_axis,
    )


def _check_threshs(
    metric: str, p_thresh: Optional[float] = None, p_hat_thresh: Optional[float] = None
):
    required_treshs = {
        "f1": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "brier": _ThreshRequired(p_thresh=True, p_hat_thresh=False),
        "auc": _ThreshRequired(p_thresh=True, p_hat_thresh=False),
        "sensitivity": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "recall": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "tpr": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "specificity": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "tnr": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "fpr": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "fnr": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "precision": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "ppv": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "npv": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "matthews": _ThreshRequired(p_thresh=True, p_hat_thresh=True),
        "r2": _ThreshRequired(p_thresh=False, p_hat_thresh=False),
        "mse": _ThreshRequired(p_thresh=False, p_hat_thresh=False),
        "mae": _ThreshRequired(p_thresh=False, p_hat_thresh=False),
    }
    try:
        required_tresh = required_treshs[metric]
    except KeyError:
        raise KeyError(
            (
                "This metric is not recognized. "
                f"Please use one of the following: {', '.join(required_treshs.keys())}"
            )
        )

    required_tresh.check_threshs_correct(p_thresh=p_thresh, p_hat_thresh=p_hat_thresh)


def _sensitivity(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return tp / (tp + fn)


def _specificity(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return tn / (tn + fp)


def _fpr(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return fp / (fp + tn)


def _fnr(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return fn / (fn + tp)


def _auc(true, pred, sample_weight):
    fpr, tpr, _ = sk_metrics.roc_curve(true, pred, sample_weight=sample_weight)
    return sk_metrics.auc(fpr, tpr)


def _precision(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return tp / (tp + fp)


def _npv(true, pred, sample_weight):
    tn, fp, fn, tp = sk_metrics.confusion_matrix(true, pred, sample_weight=sample_weight).ravel()
    return tn / (tn + fn)


def conf_matrix(
    cases: pd.DataFrame,
    signals: pd.DataFrame,
    threshold_true: Optional[float] = None,
    threshold_pred: Optional[float] = None,
    weighting: Optional[Union[str, np.ndarray]] = None,
    time_space_weighting: dict[str, float] = None,
    time_axis: Optional[str] = None,
) -> dict[str, np.ndarray]:
    r"""Calculate epidemiologically meaningful confusion matrices.

    Given case count data of infectious diseases, information on cases linked through an
    outbreak, signals for outbreaks generated by outbreak detection algorithms, a cell-grid based
    calculation of the confusion matrix per data label is returned.

    Args:
        cases: This DataFrame must contain the following columns and no NaNs:

            - ``data_label``. Is the class per outbreak. Must contain ``endemic``
              and must not contain ``non-case``.
            - ``value``. This is the amount of cases in the respective cell.
              This value must be an positive integer.
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. This coordinate system is
              the evaluation resolution.

        signals: This DataFrame must contain the following columns:

            - ``signal_label``. Is the class per signal. Must contain ``endemic`` and
              ``non-case``.
            - ``value``. This is the signal strength :math:`w` and should be :math:`w \in [0,1]`
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. Cases coordinates and cells
              must be subset of cases coordinates and cells. Cells outside
              the coordinate system of the cases DataFrame are ignored.

        threshold_true: To binarize :math:`p(d_i|x)`, the true probability per disease given cell.
        threshold_pred: To binarize :math:`\hat{p}(d_i|x)`, the predicted probability
                        per disease given cell.
        weighting: Assigns weight to :math:`p(d_i|x)` and :math:`\hat{p}(d_i|x)` by either
                 'cases' or 'timespace'. If None, no weighting is applied. You can use
                 a 1-D numpy array where each entry is the weighting per cell in the same
                 order as the `cases` DataFrame
        gauss_dims: Only valid if weight is 'timespace'. Assigns over which coordinate cells
                    spatial weighting should happen.
        covariance_diag: Only valid if weight is 'timespace'.
                         Specifies the n-dim. Gaussian covariance.
        time_axis: Only valid if weight is 'timespace'. Assigns over which coordinates
                   temporal weighting should happen.

    Returns:
        Confusion matrix per data label.
    """
    if threshold_true is None:
        threshold_true = 0
    threshold_pred = threshold_pred or 0.5
    return ScoreCalculator(cases, signals).calc_score(
        scorer=sk_metrics.confusion_matrix,
        p_thresh=threshold_true,
        p_hat_thresh=threshold_pred,
        weighting=weighting,
        time_space_weighting=time_space_weighting,
        time_axis=time_axis,
    )


def timeliness(
    cases: pd.DataFrame, signals: pd.DataFrame, time_axis: str, D: int, signal_threshold: float = 0
) -> dict[str, float]:
    r"""Calculates the timeliness of the detection of outbreaks.

    Timeliness is calculated per data label and is defines as:

    .. math::

        p_{time} = \begin{cases}
          1 -s/D     & \text{if } s \leq D \text{,}\\
          0,         & \text{otherwise.}
        \end{cases}

    Where :math:`s` is the amount of elapsed cells before detecting an outbreak and :math:`D`
           is the maximum amount of elapsed cells that we want to allow.

    Args:
        cases: This DataFrame must contain the following columns and no NaNs:

            - ``data_label``. Is the class per outbreak. Must contain ``endemic``
              and must not contain ``non-case``.
            - ``value``. This is the amount of cases in the respective cell.
              This value must be an positive integer.
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. This coordinate system is
              the evaluation resolution.

        signals: This DataFrame must contain the following columns:

            - ``signal_label``. Is the class per signal. Must contain ``endemic`` and
              ``non-case``.
            - ``value``. This is the signal strength :math:`w` and should be :math:`w \in [0,1]`
            - Each other column in the DataFrame is treated as a coordinate
              where each row is one single cell. Cases coordinates and cells
              must be subset of cases coordinates and cells. Cells outside
              the coordinate system of the cases DataFrame are ignored.

        time_axis: Column name of the time dimension/axis
        D: Is the maximum allowed delay to detect an outbreak. If an outbreak is detected
           at :math:`s>D` where :math:`s` is the number of cells that have elapsed since
           the outbreak started, then the timeliness is :math:`0` for that data label.
        signal_threshold: Indicates at which threshold a generated signal is counted as one.
                          Binarized signal is used to quantify timeliness.

    Returns:
        Timeliness score per data label.
    """
    return Timeliness(cases, signals).timeliness(time_axis, D, signal_threshold)
