"""Pipeline complet : données -> modèles -> seuil optimisé en euros -> rapport.

Usage (depuis la racine du projet, après scripts/run_sql.py) :
    python scripts/run_pipeline.py

Sorties :
    reports/metrics.json              chiffres clés (repris dans le README)
    reports/model_comparison.csv      bilan financier de chaque approche sur le test
    reports/sensitivity.csv           gain net selon le coût d'une alerte
    reports/figures/*.png             graphiques
    powerbi/exports/*.csv             tables prêtes pour le dashboard Power BI
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from fraud import config, costs, data, features, models, plots  # noqa: E402


def main() -> None:
    config.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    config.POWERBI_DIR.mkdir(parents=True, exist_ok=True)
    metrics: dict = {"review_cost_eur": config.REVIEW_COST_EUR}

    # 1. Données -------------------------------------------------------------
    raw = data.load_raw()
    df = data.clean(raw)
    splits = data.temporal_split(df)
    metrics["data"] = {
        "n_rows_raw": len(raw),
        "n_rows_clean": len(df),
        "n_duplicates_removed": len(raw) - len(df),
        "n_fraud": int(df["Class"].sum()),
        "fraud_rate_pct": round(100 * df["Class"].mean(), 3),
        "splits": {
            k: {
                "n": len(v),
                "n_fraud": int(v["Class"].sum()),
                "fraud_amount_eur": round(float(v.loc[v["Class"] == 1, "Amount"].sum()), 2),
                "hours": [round(v["Time"].min() / 3600, 1), round(v["Time"].max() / 3600, 1)],
            }
            for k, v in splits.items()
        },
    }

    X = {k: features.build_features(v) for k, v in splits.items()}
    y = {k: v["Class"] for k, v in splits.items()}
    amt = {k: v["Amount"] for k, v in splits.items()}

    # 2. Modèles -------------------------------------------------------------
    fitted = models.fit_all(X["train"], y["train"], amt["train"])
    scores = {name: {s: m.predict_proba(X[s])[:, 1] for s in ("valid", "test")} for name, m in fitted.items()}

    # 3. Seuil optimisé en euros sur la VALIDATION, appliqué tel quel au TEST ---
    rows, valid_curves, chosen_idx = [], {}, {}
    test_hours = (splits["test"]["Time"].max() - splits["test"]["Time"].min()) / 3600
    for name in fitted:
        curve = costs.threshold_curve(y["valid"], amt["valid"], scores[name]["valid"], config.REVIEW_COST_EUR)
        threshold = costs.best_threshold(curve)
        valid_curves[name] = curve
        chosen_idx[name] = curve.index[curve["threshold"] == threshold][0]

        flagged = scores[name]["test"] >= threshold
        out = costs.business_outcome(y["test"], amt["test"], flagged, config.REVIEW_COST_EUR)
        lo, hi = costs.bootstrap_net_savings(y["test"], amt["test"], flagged, config.REVIEW_COST_EUR)
        rows.append({
            "model": name,
            "threshold": threshold,
            "valid_net_savings": curve.loc[chosen_idx[name], "net_savings"],
            "pr_auc_test": average_precision_score(y["test"], scores[name]["test"]),
            "roc_auc_test": roc_auc_score(y["test"], scores[name]["test"]),
            **out,
            "alerts_per_hour": out["n_alerts"] / test_hours,
            "ci90_low": lo,
            "ci90_high": hi,
        })
    results = pd.DataFrame(rows)
    results.to_csv(config.REPORTS_DIR / "model_comparison.csv", index=False)

    # Modèle retenu = meilleur gain net en VALIDATION (le test ne sert qu'à mesurer)
    best_name = results.sort_values("valid_net_savings", ascending=False).iloc[0]["model"]
    best = results.set_index("model").loc[best_name]
    metrics["selected_model"] = best_name
    metrics["test_results"] = results.round(4).to_dict(orient="records")

    # 4. Sensibilité au coût d'une alerte ------------------------------------
    sens_rows = []
    for cost in config.REVIEW_COST_SENSITIVITY:
        for name in ("Régression logistique", "LightGBM", "LightGBM pondéré €"):
            curve = costs.threshold_curve(y["valid"], amt["valid"], scores[name]["valid"], cost)
            t = costs.best_threshold(curve)
            out = costs.business_outcome(y["test"], amt["test"], scores[name]["test"] >= t, cost)
            sens_rows.append({"review_cost": cost, "model": name, "threshold": t, **out})
    sens = pd.DataFrame(sens_rows)
    sens.to_csv(config.REPORTS_DIR / "sensitivity.csv", index=False)

    # 5. Contrôle : découpage aléatoire vs temporel --------------------------
    X_all, y_all = features.build_features(df), df["Class"]
    Xtr, Xte, ytr, yte = train_test_split(X_all, y_all, test_size=0.2, stratify=y_all,
                                          random_state=config.RANDOM_STATE)
    rnd = models.lightgbm().fit(Xtr, ytr)
    metrics["pr_auc_random_split_lightgbm"] = round(average_precision_score(yte, rnd.predict_proba(Xte)[:, 1]), 4)
    metrics["pr_auc_temporal_split_lightgbm"] = round(
        float(results.set_index("model").loc["LightGBM", "pr_auc_test"]), 4)

    # 6. Graphiques ----------------------------------------------------------
    sql_dir = config.REPORTS_DIR / "sql_results"
    plots.fraud_by_decile(pd.read_csv(sql_dir / "fraud_by_amount_decile.csv"),
                          config.FIGURES_DIR / "01_fraud_by_amount_decile.png")
    plots.net_savings_curve({k: valid_curves[k] for k in ("Régression logistique", "LightGBM", "LightGBM pondéré €")},
                            {best_name: chosen_idx[best_name]},
                            config.FIGURES_DIR / "02_net_savings_vs_alerts.png")
    plots.model_comparison(results, config.FIGURES_DIR / "03_model_comparison_test.png")
    plots.sensitivity(sens, config.FIGURES_DIR / "04_sensitivity_review_cost.png")
    lgbm = fitted["LightGBM"]
    plots.feature_importance(
        pd.Series(lgbm.booster_.feature_importance(importance_type="gain"), index=features.FEATURES),
        config.FIGURES_DIR / "05_feature_importance.png")

    # 7. Exports Power BI ----------------------------------------------------
    test = splits["test"][["tx_id", "Time", "hour_elapsed", "hour_of_day", "Amount", "Class"]].copy()
    test["score"] = scores[best_name]["test"]
    test["flagged"] = (test["score"] >= best["threshold"]).astype(int)
    test["outcome"] = np.select(
        [(test.flagged == 1) & (test.Class == 1), (test.flagged == 1) & (test.Class == 0),
         (test.flagged == 0) & (test.Class == 1)],
        ["Fraude détectée", "Fausse alerte", "Fraude manquée"], default="Légitime non alertée")
    test["euros_impact"] = np.select(
        [test.outcome == "Fraude détectée", test.outcome == "Fraude manquée", test.outcome == "Fausse alerte"],
        [test.Amount - config.REVIEW_COST_EUR, -test.Amount, -config.REVIEW_COST_EUR], default=0.0)
    test.to_csv(config.POWERBI_DIR / "test_transactions_scored.csv", index=False)

    vc = valid_curves[best_name]
    vc[vc["n_alerts"] <= 2000].drop(columns="threshold").assign(
        threshold=vc["threshold"].replace(np.inf, 1.0)).to_csv(
        config.POWERBI_DIR / "threshold_curve_validation.csv", index=False)
    results.to_csv(config.POWERBI_DIR / "model_comparison.csv", index=False)
    sens.to_csv(config.POWERBI_DIR / "sensitivity_review_cost.csv", index=False)
    pd.read_csv(sql_dir / "fraud_by_hour_elapsed.csv").to_csv(config.POWERBI_DIR / "hourly_fraud.csv", index=False)
    pd.read_csv(sql_dir / "fraud_by_amount_decile.csv").to_csv(config.POWERBI_DIR / "fraud_by_amount_decile.csv",
                                                               index=False)

    with open(config.REPORTS_DIR / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2, default=float)

    pd.set_option("display.width", 200)
    print(results[["model", "valid_net_savings", "pr_auc_test", "n_alerts", "n_fraud_caught", "n_fraud",
                   "fraud_amount_saved", "fraud_amount_total", "net_savings", "ci90_low", "ci90_high",
                   "alerts_per_hour", "precision"]].round(3).to_string(index=False))
    print("\nModèle retenu :", best_name)
    print(sens[["review_cost", "model", "n_alerts", "net_savings"]].round(1).to_string(index=False))
    print("PR-AUC random vs temporal:", metrics["pr_auc_random_split_lightgbm"],
          metrics["pr_auc_temporal_split_lightgbm"])


if __name__ == "__main__":
    main()
