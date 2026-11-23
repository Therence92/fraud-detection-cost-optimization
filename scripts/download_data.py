"""Télécharge le dataset depuis Kaggle et vérifie son intégrité (MD5)."""
from __future__ import annotations

import hashlib
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
CSV = RAW_DIR / "creditcard.csv"
EXPECTED_MD5 = "e90efcb83d69faf99fcab8b0255024de"
DATASET = "mlg-ulb/creditcardfraud"


def md5(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if not CSV.exists():
        print(f"Téléchargement de {DATASET} via l'API Kaggle...")
        try:
            subprocess.run(["kaggle", "datasets", "download", "-d", DATASET, "-p", str(RAW_DIR)], check=True)
        except (FileNotFoundError, subprocess.CalledProcessError):
            sys.exit("Échec : installez `kaggle`, configurez ~/.kaggle/kaggle.json, "
                     "ou téléchargez le fichier à la main (voir data/README.md).")
        with zipfile.ZipFile(RAW_DIR / "creditcardfraud.zip") as z:
            z.extract("creditcard.csv", RAW_DIR)
        (RAW_DIR / "creditcardfraud.zip").unlink()

    checksum = md5(CSV)
    if checksum != EXPECTED_MD5:
        sys.exit(f"Attention : MD5 inattendu ({checksum}). Le fichier n'est pas la version de référence.")
    print(f"OK : {CSV} (MD5 vérifié)")


if __name__ == "__main__":
    main()
