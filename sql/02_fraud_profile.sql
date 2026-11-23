-- =============================================================================
-- 02_fraud_profile.sql : où se concentre la fraude, en volume et en euros ?
-- Techniques : CTE, NTILE, SUM() OVER (cumul), RANK(), fenêtre glissante (ROWS BETWEEN)
-- =============================================================================

-- name: fraud_by_amount_decile
-- Taux de fraude et pertes par décile de montant (1 = plus petits montants)
WITH deciles AS (
    SELECT
        *,
        NTILE(10) OVER (ORDER BY "Amount", tx_id) AS amount_decile
    FROM transactions
)
SELECT
    amount_decile,
    ROUND(MIN("Amount"), 2)                                   AS amount_from,
    ROUND(MAX("Amount"), 2)                                   AS amount_to,
    COUNT(*)                                                  AS n_transactions,
    SUM("Class")                                              AS n_fraud,
    ROUND(100.0 * SUM("Class") / COUNT(*), 3)                 AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN "Class" = 1 THEN "Amount" END), 2)    AS fraud_amount_eur
FROM deciles
GROUP BY amount_decile
ORDER BY amount_decile;

-- name: fraud_pareto
-- Concentration des pertes : quelle part des fraudes représente quelle part des euros perdus ?
WITH frauds AS (
    SELECT tx_id, "Amount"
    FROM transactions
    WHERE "Class" = 1
),
ranked AS (
    SELECT
        tx_id,
        "Amount",
        ROW_NUMBER() OVER (ORDER BY "Amount" DESC, tx_id)     AS rank_by_amount,
        COUNT(*)     OVER ()                                  AS n_fraud_total,
        SUM("Amount") OVER (ORDER BY "Amount" DESC, tx_id
                            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cum_amount,
        SUM("Amount") OVER ()                                 AS total_amount
    FROM frauds
)
SELECT
    pct_frauds,
    ROUND(100.0 * MAX(cum_amount) / MAX(total_amount), 1)     AS pct_fraud_losses
FROM (
    SELECT
        *,
        CEIL(100.0 * rank_by_amount / n_fraud_total / 10) * 10 AS pct_frauds
    FROM ranked
)
GROUP BY pct_frauds
ORDER BY pct_frauds;

-- name: fraud_by_hour_elapsed
-- Évolution heure par heure sur les 48 h, avec moyenne glissante sur 3 h
-- et rang des heures les plus risquées
WITH hourly AS (
    SELECT
        hour_elapsed,
        COUNT(*)                                              AS n_transactions,
        SUM("Class")                                          AS n_fraud,
        ROUND(SUM(CASE WHEN "Class" = 1 THEN "Amount" ELSE 0 END), 2) AS fraud_amount_eur
    FROM transactions
    GROUP BY hour_elapsed
)
SELECT
    hour_elapsed,
    n_transactions,
    n_fraud,
    fraud_amount_eur,
    ROUND(100.0 * n_fraud / n_transactions, 3)                AS fraud_rate_pct,
    ROUND(100.0 * SUM(n_fraud) OVER w3 / SUM(n_transactions) OVER w3, 3) AS fraud_rate_3h_rolling_pct,
    RANK() OVER (ORDER BY 1.0 * n_fraud / n_transactions DESC) AS risk_rank
FROM hourly
WINDOW w3 AS (ORDER BY hour_elapsed ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
ORDER BY hour_elapsed;

-- name: fraud_by_hour_of_day
-- Profil "jour / nuit" (hypothèse : la collecte commence à minuit)
SELECT
    hour_of_day,
    COUNT(*)                                                  AS n_transactions,
    SUM("Class")                                              AS n_fraud,
    ROUND(100.0 * SUM("Class") / COUNT(*), 3)                 AS fraud_rate_pct,
    ROUND(AVG("Class") / (SELECT AVG("Class") FROM transactions), 2) AS lift_vs_average
FROM transactions
GROUP BY hour_of_day
ORDER BY hour_of_day;

-- name: split_summary
-- Découpage temporel utilisé par le modèle : 60 % / 20 % / 20 % du temps de collecte
-- (on apprend sur le passé, on règle le seuil sur la période suivante, on teste sur la plus récente)
WITH bounds AS (
    SELECT
        QUANTILE_CONT("Time", 0.60) AS t_train_end,
        QUANTILE_CONT("Time", 0.80) AS t_valid_end
    FROM transactions
),
labelled AS (
    SELECT
        t.*,
        CASE
            WHEN t."Time" <= b.t_train_end THEN '1_train'
            WHEN t."Time" <= b.t_valid_end THEN '2_validation'
            ELSE '3_test'
        END AS split
    FROM transactions t
    CROSS JOIN bounds b
)
SELECT
    split,
    ROUND(MIN("Time") / 3600, 1)                              AS start_hour,
    ROUND(MAX("Time") / 3600, 1)                              AS end_hour,
    COUNT(*)                                                  AS n_transactions,
    SUM("Class")                                              AS n_fraud,
    ROUND(100.0 * SUM("Class") / COUNT(*), 3)                 AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN "Class" = 1 THEN "Amount" ELSE 0 END), 2) AS fraud_amount_eur
FROM labelled
GROUP BY split
ORDER BY split;
