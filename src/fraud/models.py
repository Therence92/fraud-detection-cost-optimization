"""Modèles comparés : règle métier, régression logistique, gradient boosting."""
from __future__ import annotations

import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from . import config


class AmountRule:
    """Règle métier de référence : plus le montant est élevé, plus on contrôle.

    Le "score" est le rang centile du montant ; le seuil est ensuite optimisé
    comme pour les modèles. Sert à prouver que le modèle apporte plus qu'une règle simple.
    """

    def fit(self, X: pd.DataFrame, y=None) -> "AmountRule":
        self.reference_ = np.sort(X["log_amount"].to_numpy())
        return self

    def predict_proba(self, X: pd.DataFrame) -> np.ndarray:
        pct = np.searchsorted(self.reference_, X["log_amount"].to_numpy(), side="right") / len(self.reference_)
        return np.column_stack([1 - pct, pct])


def logistic_regression() -> object:
    """Modèle linéaire interprétable, classes rééquilibrées."""
    return make_pipeline(
        StandardScaler(),
        LogisticRegression(class_weight="balanced", max_iter=2000, C=0.1),
    )


def lightgbm(**overrides) -> LGBMClassifier:
    """Gradient boosting. Hyperparamètres volontairement prudents (peu de fraudes)."""
    params = dict(
        n_estimators=400,
        learning_rate=0.03,
        num_leaves=15,
        min_child_samples=50,
        subsample=0.8,
        subsample_freq=1,
        colsample_bytree=0.8,
        reg_lambda=1.0,
        random_state=config.RANDOM_STATE,
        verbose=-1,
    )
    params.update(overrides)
    return LGBMClassifier(**params)


def amount_weights(y: pd.Series, amount: pd.Series) -> np.ndarray:
    """Poids d'apprentissage proportionnels à l'enjeu financier.

    Une fraude à 1 000 € coûte 1 000 fois plus qu'une fraude à 1 € : on le dit au modèle.
    Les transactions légitimes gardent un poids de 1.
    """
    w = np.ones(len(y))
    is_fraud = y.to_numpy() == 1
    w[is_fraud] = 1 + amount.to_numpy()[is_fraud]
    return w


def fit_all(X_train: pd.DataFrame, y_train: pd.Series, amount_train: pd.Series) -> dict:
    """Entraîne les 4 approches comparées dans le projet."""
    fitted = {
        "Règle montant": AmountRule().fit(X_train),
        "Régression logistique": logistic_regression().fit(X_train, y_train),
        "LightGBM": lightgbm().fit(X_train, y_train),
    }
    weights = amount_weights(y_train, amount_train)
    fitted["LightGBM pondéré €"] = lightgbm().fit(X_train, y_train, sample_weight=weights)
    return fitted
