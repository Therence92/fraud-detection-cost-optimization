"""Exécute les scripts SQL (DuckDB) et exporte chaque requête nommée en CSV.

Usage (depuis la racine du projet) :
    python scripts/run_sql.py

Convention : dans les fichiers sql/*.sql, une requête précédée d'une ligne
"-- name: nom_resultat" est exportée dans reports/sql_results/nom_resultat.csv.
Les autres instructions (CREATE TABLE...) sont simplement exécutées.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
OUT_DIR = ROOT / "reports" / "sql_results"
DB_PATH = ROOT / "data" / "fraud.duckdb"

NAME_PATTERN = re.compile(r"^--\s*name:\s*(\w+)", re.MULTILINE)


def split_statements(sql_text: str) -> list[tuple[str | None, str]]:
    """Découpe un fichier SQL en (nom éventuel, instruction)."""
    statements = []
    for chunk in sql_text.split(";"):
        if not re.search(r"\b(SELECT|CREATE|WITH|INSERT)\b", chunk, re.IGNORECASE):
            continue
        match = NAME_PATTERN.search(chunk)
        statements.append((match.group(1) if match else None, chunk.strip()))
    return statements


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Les chemins relatifs des fichiers SQL sont résolus depuis la racine du projet
    os.chdir(ROOT)
    con = duckdb.connect(str(DB_PATH))

    for sql_file in sorted(SQL_DIR.glob("*.sql")):
        print(f"\n=== {sql_file.name}")
        for name, statement in split_statements(sql_file.read_text(encoding="utf-8")):
            result = con.execute(statement)
            if name is None:
                continue
            df = result.df()
            df.to_csv(OUT_DIR / f"{name}.csv", index=False)
            print(f"\n-- {name} ({len(df)} lignes)")
            print(df.head(12).to_string(index=False))

    con.close()


if __name__ == "__main__":
    main()
