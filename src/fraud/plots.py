"""Graphiques du rapport (style sobre, couleurs constantes par modèle)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

SURFACE = "#fcfcfb"
INK = "#0b0b0b"
INK_2 = "#52514e"
GRID = "#e4e3df"
NEUTRAL = "#a3a29c"

# Une couleur fixe par modèle, partout dans le projet
MODEL_COLORS = {
    "Règle montant": NEUTRAL,
    "Régression logistique": "#2a78d6",
    "LightGBM": "#eb6834",
    "LightGBM pondéré €": "#1baf7a",
}


def _style(ax, title: str, subtitle: str | None = None) -> None:
    ax.set_facecolor(SURFACE)
    ax.figure.set_facecolor(SURFACE)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(GRID)
    ax.tick_params(colors=INK_2, labelsize=9)
    ax.grid(axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=13, color=INK, fontweight="bold", pad=22 if subtitle else 10)
    if subtitle:
        ax.text(0, 1.02, subtitle, transform=ax.transAxes, fontsize=9.5, color=INK_2)
    ax.xaxis.label.set_color(INK_2)
    ax.yaxis.label.set_color(INK_2)


def _save(fig, path) -> None:
    fig.tight_layout()
    fig.savefig(path, dpi=150, facecolor=SURFACE)
    plt.close(fig)


def fraud_by_decile(deciles: pd.DataFrame, path) -> None:
    """Nombre de fraudes vs euros perdus par décile de montant : deux réalités opposées."""
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    x = deciles["amount_decile"]
    labels = [f"D{d}" for d in x]
    axes[0].bar(labels, deciles["n_fraud"], color="#2a78d6", width=0.7)
    _style(axes[0], "Nombre de fraudes", "par décile de montant (D1 = montants ≤ 1 €)")
    axes[1].bar(labels, deciles["fraud_amount_eur"], color="#eb6834", width=0.7)
    _style(axes[1], "Euros perdus", "par décile de montant (D10 = montants > 203 €)")
    axes[1].yaxis.set_major_formatter(lambda v, _: f"{v/1000:.0f} k€")
    for ax, col, fmt in ((axes[0], "n_fraud", "{:.0f}"), (axes[1], "fraud_amount_eur", "{:,.0f} €")):
        i_max = deciles[col].idxmax()
        ax.annotate(fmt.format(deciles.loc[i_max, col]).replace(",", " "),
                    (labels[i_max], deciles.loc[i_max, col]), ha="center", va="bottom",
                    fontsize=9, color=INK, xytext=(0, 3), textcoords="offset points")
    _save(fig, path)


def net_savings_curve(curves: dict[str, pd.DataFrame], chosen: dict[str, int], path, max_alerts: int = 600) -> None:
    """Gain net en fonction du nombre d'alertes (validation)."""
    fig, ax = plt.subplots(figsize=(9, 4.8))
    for name, curve in curves.items():
        c = curve[curve["n_alerts"] <= max_alerts]
        ax.plot(c["n_alerts"], c["net_savings"], color=MODEL_COLORS[name], linewidth=2, label=name,
                drawstyle="steps-post")
        if name in chosen:
            row = curve.loc[chosen[name]]
            ax.scatter(row["n_alerts"], row["net_savings"], s=60, color=MODEL_COLORS[name],
                       edgecolor=SURFACE, linewidth=2, zorder=5)
            gain = f"{row['net_savings']:,.0f}".replace(",", " ")
            ax.annotate(f"seuil retenu : {row['n_alerts']:.0f} alertes, gain net {gain} €",
                        (row["n_alerts"], row["net_savings"]), xytext=(12, -34), textcoords="offset points",
                        fontsize=8.5, color=INK, bbox=dict(boxstyle="round,pad=0.3", fc=SURFACE, ec=GRID))
    ax.axhline(0, color=INK_2, linewidth=0.8)
    ax.set_xlabel("Nombre d'alertes envoyées aux analystes (période de validation)")
    ax.set_ylabel("Gain net (€)")
    _style(ax, "Trop peu d'alertes : on rate la fraude. Trop d'alertes : la revue coûte plus qu'elle ne rapporte.",
           "Gain net = euros de fraude évités − coût des alertes (5 € / alerte)")
    ax.title.set_fontsize(11)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    _save(fig, path)


def model_comparison(results: pd.DataFrame, path) -> None:
    """Gain net sur le test (période la plus récente) avec intervalle de confiance 90 %."""
    r = results.sort_values("net_savings")
    fig, ax = plt.subplots(figsize=(9, 3.8))
    y = np.arange(len(r))
    colors = [MODEL_COLORS[m] for m in r["model"]]
    ax.barh(y, r["net_savings"], color=colors, height=0.55)
    err_low = r["net_savings"] - r["ci90_low"]
    err_high = r["ci90_high"] - r["net_savings"]
    ax.errorbar(r["net_savings"], y, xerr=[err_low, err_high], fmt="none", ecolor=INK_2, capsize=4, linewidth=1)
    ax.set_yticks(y, r["model"])
    for yi, (v, tot) in enumerate(zip(r["net_savings"], r["fraud_amount_total"])):
        ax.text(max(r["ci90_high"].max(), 0) * 1.02 if v >= 0 else 50, yi,
                f"{v:,.0f}".replace(",", " ") + f" € ({v/tot:.0%} des pertes évitées)",
                va="center", fontsize=9, color=INK)
    ax.axvline(0, color=INK_2, linewidth=0.8)
    ax.set_xlabel("Gain net sur la période de test (€), barre = IC 90 % par bootstrap")
    _style(ax, "Gain net par approche, sur des transactions jamais vues")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    ax.set_xlim(right=max(r["ci90_high"].max(), 1) * 1.75)
    _save(fig, path)


def sensitivity(sens: pd.DataFrame, path) -> None:
    """Gain net (test) selon le coût d'une alerte."""
    fig, ax = plt.subplots(figsize=(9, 4.2))
    for name, g in sens.groupby("model"):
        g = g.sort_values("review_cost")
        ax.plot(g["review_cost"], g["net_savings"], color=MODEL_COLORS[name], linewidth=2, marker="o",
                markersize=7, markeredgecolor=SURFACE, markeredgewidth=2, label=name)
    ax.set_xscale("log")
    ax.set_xticks(sens["review_cost"].unique(), [f"{c:g} €" for c in sens["review_cost"].unique()])
    ax.set_xlabel("Coût d'une alerte (revue analyste, appel ou SMS client)")
    ax.set_ylabel("Gain net sur le test (€)")
    _style(ax, "Le meilleur modèle dépend du coût de traitement d'une alerte",
           "Seuil ré-optimisé sur la validation pour chaque coût, puis appliqué au test")
    ax.legend(frameon=False, fontsize=9)
    _save(fig, path)


def feature_importance(importances: pd.Series, path, top: int = 12) -> None:
    imp = importances.sort_values().tail(top)
    fig, ax = plt.subplots(figsize=(8, 4.6))
    ax.barh(imp.index, imp.values / imp.values.sum() * 100, color="#eb6834", height=0.6)
    ax.set_xlabel("Part de l'importance totale parmi le top 12 (%, gain LightGBM)")
    _style(ax, "Variables les plus utilisées par le modèle",
           "V1 à V28 sont anonymisées (ACP) : on sait QUOI compte, pas POURQUOI")
    ax.grid(axis="y", visible=False)
    ax.grid(axis="x", color=GRID, linewidth=0.8)
    _save(fig, path)
