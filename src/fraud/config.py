"""Paramètres centraux du projet (chemins, découpage, hypothèses de coût)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_CSV = ROOT / "data" / "raw" / "creditcard.csv"
REPORTS_DIR = ROOT / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
POWERBI_DIR = ROOT / "powerbi" / "exports"

RANDOM_STATE = 42

# Découpage temporel (quantiles de la variable Time, après dédoublonnage)
TRAIN_END_QUANTILE = 0.60   # 60 % les plus anciens  -> apprentissage
VALID_END_QUANTILE = 0.80   # 20 % suivants           -> choix du seuil
                            # 20 % les plus récents   -> test final, jamais vu

# ---------------------------------------------------------------------------
# Hypothèses de coût (à adapter au contexte réel d'une banque)
# ---------------------------------------------------------------------------
# Coût d'une alerte : temps d'un analyste pour vérifier la transaction
# (~5 min à ~60 €/h chargé) + éventuel appel client. Valeur centrale : 5 €.
REVIEW_COST_EUR = 5.0
# Fraude non détectée : la banque rembourse le client -> perte = montant de la transaction.
# Fraude détectée : on considère la perte évitée (montant sauvé), moins le coût de revue.
REVIEW_COST_SENSITIVITY = [1.0, 2.0, 5.0, 10.0, 20.0]
