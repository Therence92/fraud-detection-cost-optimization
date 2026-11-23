-- =============================================================================
-- 01_data_quality.sql : contrôle qualité avant toute analyse
-- Chaque requête précédée de "-- name: xxx" est exportée dans reports/sql_results/xxx.csv
-- =============================================================================

-- name: dq_overview
-- Volumétrie, valeurs manquantes et doublons
WITH raw_stats AS (
    SELECT
        COUNT(*)                                        AS n_rows_raw,
        SUM(CASE WHEN "Class" = 1 THEN 1 ELSE 0 END)    AS n_fraud_raw,
        COUNT(*) - COUNT("Amount")                      AS n_null_amount,
        COUNT(*) - COUNT("Class")                       AS n_null_class
    FROM transactions_raw
),
clean_stats AS (
    SELECT
        COUNT(*)                                        AS n_rows_clean,
        SUM("Class")                                    AS n_fraud_clean
    FROM transactions
)
SELECT
    r.n_rows_raw,
    c.n_rows_clean,
    r.n_rows_raw - c.n_rows_clean                       AS n_duplicates_removed,
    r.n_fraud_raw,
    c.n_fraud_clean,
    r.n_fraud_raw - c.n_fraud_clean                     AS n_fraud_duplicates_removed,
    ROUND(100.0 * c.n_fraud_clean / c.n_rows_clean, 3)  AS fraud_rate_pct,
    r.n_null_amount,
    r.n_null_class
FROM raw_stats r
CROSS JOIN clean_stats c;

-- name: dq_amount_checks
-- Montants nuls ou extrêmes, par classe
SELECT
    CASE WHEN "Class" = 1 THEN 'fraude' ELSE 'légitime' END   AS classe,
    COUNT(*)                                                  AS n_transactions,
    SUM(CASE WHEN "Amount" = 0 THEN 1 ELSE 0 END)             AS n_amount_zero,
    ROUND(MIN("Amount"), 2)                                   AS amount_min,
    ROUND(MEDIAN("Amount"), 2)                                AS amount_median,
    ROUND(AVG("Amount"), 2)                                   AS amount_mean,
    ROUND(QUANTILE_CONT("Amount", 0.99), 2)                   AS amount_p99,
    ROUND(MAX("Amount"), 2)                                   AS amount_max,
    ROUND(SUM("Amount"), 2)                                   AS amount_total
FROM transactions
GROUP BY ALL
ORDER BY classe;
