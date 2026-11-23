-- =============================================================================
-- 00_load.sql : chargement des données brutes et création de la table nettoyée
-- Moteur : DuckDB (exécuté par scripts/run_sql.py)
-- =============================================================================

-- Table brute : on ajoute un identifiant de transaction stable (ordre du fichier)
CREATE OR REPLACE TABLE transactions_raw AS
SELECT
    ROW_NUMBER() OVER () - 1 AS tx_id,
    *
FROM read_csv('data/raw/creditcard.csv', header = true);

-- Table nettoyée : suppression des doublons exacts (toutes colonnes identiques).
-- On conserve la première occurrence (plus petit tx_id).
-- Ajout de variables temporelles lisibles :
--   hour_elapsed : heure écoulée depuis le début de la collecte (0 à 47)
--   hour_of_day  : heure "de la journée" en supposant que la collecte démarre à minuit
--                  (hypothèse non garantie par la source : à présenter comme telle)
CREATE OR REPLACE TABLE transactions AS
WITH dedup AS (
    SELECT
        MIN(tx_id) AS tx_id,
        * EXCLUDE (tx_id)
    FROM transactions_raw
    GROUP BY ALL
)
SELECT
    *,
    CAST(FLOOR("Time" / 3600) AS INTEGER)            AS hour_elapsed,
    CAST(FLOOR("Time" / 3600) AS INTEGER) % 24       AS hour_of_day
FROM dedup
ORDER BY tx_id;
