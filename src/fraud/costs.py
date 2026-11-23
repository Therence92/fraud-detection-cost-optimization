"""Traduction des prédictions en euros : le cœur métier du projet.

Logique de coût (par transaction) :
    - Alerte (transaction signalée)    : coût de revue `review_cost`
    - Fraude détectée (vrai positif)   : montant sauvé
    - Fraude manquée (faux négatif)    : montant perdu (remboursé au client)
    - Fausse alerte (faux positif)     : uniquement le coût de revue

Référence : "sans modèle", toutes les fraudes sont perdues.
Gain net = montants sauvés - coût total des alertes.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


def business_outcome(
    y_true: np.ndarray,
    amount: np.ndarray,
    flagged: np.ndarray,
    review_cost: float,
) -> dict:
    """Bilan financier et opérationnel pour un ensemble de décisions."""
    y_true = np.asarray(y_true).astype(bool)
    amount = np.asarray(amount, dtype=float)
    flagged = np.asarray(flagged).astype(bool)

    tp = flagged & y_true
    fp = flagged & ~y_true
    fn = ~flagged & y_true

    fraud_total = amount[y_true].sum()
    saved = amount[tp].sum()
    n_alerts = int(flagged.sum())
    alert_cost = n_alerts * review_cost

    return {
        "n_alerts": n_alerts,
        "n_fraud": int(y_true.sum()),
        "n_fraud_caught": int(tp.sum()),
        "n_false_alerts": int(fp.sum()),
        "n_fraud_missed": int(fn.sum()),
        "recall_count": tp.sum() / max(y_true.sum(), 1),
        "precision": tp.sum() / max(n_alerts, 1),
        "fraud_amount_total": fraud_total,
        "fraud_amount_saved": saved,
        "fraud_amount_lost": amount[fn].sum(),
        "recall_amount": saved / fraud_total if fraud_total > 0 else np.nan,
        "alert_cost": alert_cost,
        "net_savings": saved - alert_cost,
        "loss_reduction_pct": (saved - alert_cost) / fraud_total if fraud_total > 0 else np.nan,
    }


def threshold_curve(
    y_true: np.ndarray,
    amount: np.ndarray,
    scores: np.ndarray,
    review_cost: float,
) -> pd.DataFrame:
    """Bilan financier pour TOUS les seuils possibles (un par score distinct).

    Calcul vectorisé : on trie les transactions du plus suspect au moins suspect,
    puis on cumule fraudes détectées, euros sauvés et nombre d'alertes.
    Ligne "seuil" t : on alerte sur toutes les transactions de score >= t.
    """
    y_true = np.asarray(y_true).astype(bool)
    amount = np.asarray(amount, dtype=float)
    scores = np.asarray(scores, dtype=float)

    order = np.argsort(-scores, kind="mergesort")
    s, y, a = scores[order], y_true[order], amount[order]

    n_alerts = np.arange(1, len(s) + 1)
    n_caught = np.cumsum(y)
    saved = np.cumsum(np.where(y, a, 0.0))

    # Un seul point par score distinct (les ex æquo sont alertés ensemble)
    last_of_tie = np.append(s[1:] != s[:-1], True)
    n_fraud, fraud_total = y.sum(), a[y].sum()

    curve = pd.DataFrame({
        "threshold": s[last_of_tie],
        "n_alerts": n_alerts[last_of_tie],
        "n_fraud_caught": n_caught[last_of_tie],
        "fraud_amount_saved": saved[last_of_tie],
    })
    # Point de départ : aucune alerte (seuil au-dessus du score maximal)
    curve = pd.concat([
        pd.DataFrame({"threshold": [np.inf], "n_alerts": [0], "n_fraud_caught": [0], "fraud_amount_saved": [0.0]}),
        curve,
    ], ignore_index=True)

    curve["alert_cost"] = curve["n_alerts"] * review_cost
    curve["net_savings"] = curve["fraud_amount_saved"] - curve["alert_cost"]
    curve["precision"] = curve["n_fraud_caught"] / curve["n_alerts"].clip(lower=1)
    curve["recall_count"] = curve["n_fraud_caught"] / max(n_fraud, 1)
    curve["recall_amount"] = curve["fraud_amount_saved"] / fraud_total if fraud_total > 0 else np.nan
    return curve


def best_threshold(curve: pd.DataFrame) -> float:
    """Seuil qui maximise le gain net (en cas d'égalité : le moins d'alertes)."""
    best = curve.sort_values(["net_savings", "n_alerts"], ascending=[False, True]).iloc[0]
    return float(best["threshold"])


def bootstrap_net_savings(
    y_true: np.ndarray,
    amount: np.ndarray,
    flagged: np.ndarray,
    review_cost: float,
    n_boot: int = 2000,
    seed: int = 42,
) -> tuple[float, float]:
    """Intervalle de confiance à 90 % du gain net (rééchantillonnage des transactions).

    Indispensable ici : le test ne contient que quelques dizaines de fraudes,
    un chiffre unique donnerait une fausse impression de précision.
    """
    rng = np.random.default_rng(seed)
    y_true = np.asarray(y_true).astype(bool)
    amount = np.asarray(amount, dtype=float)
    flagged = np.asarray(flagged).astype(bool)
    gain_per_tx = np.where(flagged & y_true, amount, 0.0) - np.where(flagged, review_cost, 0.0)
    n = len(gain_per_tx)
    stats = [gain_per_tx[rng.integers(0, n, n)].sum() for _ in range(n_boot)]
    return float(np.percentile(stats, 5)), float(np.percentile(stats, 95))
