"""Tests sur le nettoyage et le découpage (nécessitent data/raw/creditcard.csv)."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fraud import config, data  # noqa: E402

pytestmark = pytest.mark.skipif(not config.RAW_CSV.exists(), reason="dataset non téléchargé")


@pytest.fixture(scope="module")
def clean_df():
    return data.clean(data.load_raw())


def test_duplicates_removed_like_sql(clean_df):
    # Même résultat que sql/00_load.sql
    assert len(clean_df) == 283_726
    assert clean_df["Class"].sum() == 473


def test_temporal_split_has_no_overlap(clean_df):
    s = data.temporal_split(clean_df)
    assert s["train"]["Time"].max() < s["valid"]["Time"].min()
    assert s["valid"]["Time"].max() < s["test"]["Time"].min()
    assert sum(len(v) for v in s.values()) == len(clean_df)
