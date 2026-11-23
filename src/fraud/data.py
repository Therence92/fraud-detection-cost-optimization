"""Chargement, nettoyage et découpage temporel des transactions."""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config

PCA_COLS = [f"V{i}" for i in range(1, 29)]


def load_raw(path=config.RAW_CSV) -> pd.DataFrame:
    """Charge le CSV brut et ajoute un identifiant stable (ordre du fichier)."""
    df = pd.read_csv(path)
    df.insert(0, "tx_id", np.arange(len(df)))
    return df


def clean(df: pd.DataFrame) -> pd.DataFrame:
    """Supprime les doublons exacts en gardant la première occurrence.

    Même règle que sql/00_load.sql : les deux doivent donner 283 726 lignes.
    """
    value_cols = [c for c in df.columns if c != "tx_id"]
    out = df.drop_duplicates(subset=value_cols, keep="first").reset_index(drop=True)
    out["hour_elapsed"] = (out["Time"] // 3600).astype(int)
    out["hour_of_day"] = out["hour_elapsed"] % 24
    return out


def temporal_split(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Découpe selon le temps : passé -> apprentissage, futur -> test.

    Un découpage aléatoire mélange des transactions de la même minute (souvent
    les mêmes fraudeurs) entre apprentissage et test, ce qui gonfle les scores.
    """
    t_train = df["Time"].quantile(config.TRAIN_END_QUANTILE)
    t_valid = df["Time"].quantile(config.VALID_END_QUANTILE)
    return {
        "train": df[df["Time"] <= t_train].copy(),
        "valid": df[(df["Time"] > t_train) & (df["Time"] <= t_valid)].copy(),
        "test": df[df["Time"] > t_valid].copy(),
    }
