# Dashboard Power BI : pilotage du dispositif anti-fraude

Les tables sont générées par `python scripts/run_pipeline.py` dans `powerbi/exports/`.
Le fichier `fraud_dashboard.pbix` est à construire à partir de ces exports (voir plan ci-dessous),
puis à déposer dans ce dossier avec une capture `dashboard.png` affichée dans le README principal.

## Tables (Obtenir les données > Texte/CSV)

| Fichier | Grain | Usage |
|---|---|---|
| `test_transactions_scored.csv` | 1 ligne = 1 transaction de la période de test | KPI, résultats par heure, détail des alertes |
| `threshold_curve_validation.csv` | 1 ligne = 1 seuil possible | choix du seuil, simulation du coût d'une alerte |
| `model_comparison.csv` | 1 ligne = 1 approche | comparaison des modèles |
| `sensitivity_review_cost.csv` | 1 ligne = 1 modèle × 1 coût | sensibilité |
| `hourly_fraud.csv` | 1 ligne = 1 heure (48 h) | profil temporel de la fraude |
| `fraud_by_amount_decile.csv` | 1 ligne = 1 décile de montant | nombre de fraudes vs euros perdus |

Pas de relation nécessaire entre les tables (chaque page s'appuie sur une table).

## Mesures DAX

```DAX
-- Table test_transactions_scored
Fraudes totales (€)    = CALCULATE(SUM(test_transactions_scored[Amount]), test_transactions_scored[Class] = 1)
Fraudes évitées (€)    = CALCULATE(SUM(test_transactions_scored[Amount]), test_transactions_scored[outcome] = "Fraude détectée")
Alertes                = CALCULATE(COUNTROWS(test_transactions_scored), test_transactions_scored[flagged] = 1)
Fraudes détectées      = CALCULATE(COUNTROWS(test_transactions_scored), test_transactions_scored[outcome] = "Fraude détectée")
Précision des alertes  = DIVIDE([Fraudes détectées], [Alertes])
Gain net (€)           = SUM(test_transactions_scored[euros_impact]) + [Fraudes manquées (€)]
Fraudes manquées (€)   = CALCULATE(SUM(test_transactions_scored[Amount]), test_transactions_scored[outcome] = "Fraude manquée")
Pertes évitées (%)     = DIVIDE([Gain net (€)], [Fraudes totales (€)])
Alertes par heure      = DIVIDE([Alertes], DISTINCTCOUNT(test_transactions_scored[hour_elapsed]))
```

Note sur `Gain net (€)` : la colonne `euros_impact` compte une fraude manquée en négatif (perte).
Le gain net se mesure par rapport à la situation « sans modèle » où toutes les fraudes sont perdues,
d'où l'ajout des fraudes manquées.

### Simulation interactive du coût d'une alerte (page 2)

Modélisation > Nouveau paramètre > Plage numérique : `Coût alerte`, de 1 à 20, pas de 1, valeur par défaut 5.

```DAX
-- Table threshold_curve_validation
Gain net simulé (€) =
    SUM(threshold_curve_validation[fraud_amount_saved])
    - SUM(threshold_curve_validation[n_alerts]) * 'Coût alerte'[Valeur Coût alerte]
```

Courbe : axe X = `n_alerts`, axe Y = `Gain net simulé (€)`. En bougeant le curseur, le métier voit
le point optimal se déplacer : moins d'alertes quand la revue coûte cher.

## Plan du rapport (3 pages)

1. **Synthèse** : cartes Fraudes évitées (€), Gain net (€), Pertes évitées (%), Alertes par heure,
   Précision des alertes ; histogramme `outcome` par `hour_elapsed` ; tableau des fraudes manquées
   triées par montant (ce que le modèle rate et combien ça coûte).
2. **Choix du seuil** : courbe gain net / nombre d'alertes avec le paramètre `Coût alerte` ;
   graphique de `sensitivity_review_cost` (une ligne par modèle).
3. **Profil de la fraude** : deux histogrammes côte à côte depuis `fraud_by_amount_decile`
   (nombre de fraudes / euros perdus), courbe `fraud_rate_pct` et `fraud_rate_3h_rolling_pct` sur 48 h.

Règles de lisibilité : une couleur fixe par modèle (identique aux graphiques Python), pas de double axe,
titres qui énoncent la conclusion (« 78 % des pertes viennent de 10 % des transactions ») plutôt que le sujet.
