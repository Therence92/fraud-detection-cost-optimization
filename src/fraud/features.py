"""Construction des variables explicatives."""
from __future__ import annotations

import numpy as np
import pandas as pd

from .data import PCA_COLS

FEATURES = PCA_COLS + ["log_amount", "hour_sin", "hour_cos"]


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Variables du modèle.

    - V1..V28 : composantes ACP fournies (anonymisées par la banque)
    - log_amount : le montant est très asymétrique (médiane 22 €, max 25 691 €)
    - hour_sin / hour_cos : heure de la journée encodée de façon cyclique
      (23 h et 0 h sont proches). Hypothèse : la collecte démarre à minuit.
    """
    X = df[PCA_COLS].copy()
    X["log_amount"] = np.log1p(df["Amount"])
    angle = 2 * np.pi * df["hour_of_day"] / 24
    X["hour_sin"] = np.sin(angle)
    X["hour_cos"] = np.cos(angle)
    return X[FEATURES]
