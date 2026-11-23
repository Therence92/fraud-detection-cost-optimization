"""Tests unitaires de la logique financière (le cœur métier doit être juste)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fraud.costs import best_threshold, business_outcome, threshold_curve  # noqa: E402

Y = np.array([1, 0, 1, 0, 0])
AMOUNT = np.array([100.0, 50.0, 10.0, 20.0, 5.0])
SCORES = np.array([0.9, 0.8, 0.3, 0.2, 0.1])


def test_business_outcome_counts_and_euros():
    flagged = np.array([1, 1, 0, 0, 0], dtype=bool)
    out = business_outcome(Y, AMOUNT, flagged, review_cost=5.0)
    assert out["n_alerts"] == 2
    assert out["n_fraud_caught"] == 1
    assert out["n_false_alerts"] == 1
    assert out["n_fraud_missed"] == 1
    assert out["fraud_amount_saved"] == pytest.approx(100.0)
    assert out["fraud_amount_lost"] == pytest.approx(10.0)
    assert out["net_savings"] == pytest.approx(100.0 - 2 * 5.0)


def test_no_alert_means_zero_savings():
    out = business_outcome(Y, AMOUNT, np.zeros(5, dtype=bool), review_cost=5.0)
    assert out["net_savings"] == 0
    assert out["fraud_amount_lost"] == pytest.approx(110.0)


def test_threshold_curve_matches_business_outcome_for_every_threshold():
    curve = threshold_curve(Y, AMOUNT, SCORES, review_cost=5.0)
    for _, row in curve.iterrows():
        expected = business_outcome(Y, AMOUNT, SCORES >= row["threshold"], 5.0)
        assert row["net_savings"] == pytest.approx(expected["net_savings"])
        assert row["n_alerts"] == expected["n_alerts"]


def test_threshold_curve_handles_ties():
    scores = np.array([0.5, 0.5, 0.5, 0.1, 0.1])
    curve = threshold_curve(Y, AMOUNT, scores, review_cost=1.0)
    # Les ex æquo sont alertés ensemble : 0, 3 ou 5 alertes, jamais 1 ou 2
    assert sorted(curve["n_alerts"].tolist()) == [0, 3, 5]


def test_best_threshold_maximises_net_savings():
    curve = threshold_curve(Y, AMOUNT, SCORES, review_cost=5.0)
    # Alerter uniquement la 1re transaction : 100 - 5 = 95 € (le maximum)
    assert best_threshold(curve) == pytest.approx(0.9)


def test_expensive_review_means_no_alert():
    curve = threshold_curve(Y, AMOUNT, SCORES, review_cost=1000.0)
    assert best_threshold(curve) == np.inf
