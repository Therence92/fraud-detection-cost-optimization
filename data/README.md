# Données

Jeu de données public **Credit Card Fraud Detection** (ULB Machine Learning Group, Worldline),
disponible sur Kaggle : <https://www.kaggle.com/datasets/mlg-ulb/creditcardfraud>.

Le fichier (`creditcard.csv`, 150 Mo) n'est pas versionné : GitHub refuse les fichiers de plus de 100 Mo.

## Téléchargement

```bash
python scripts/download_data.py
```

Le script utilise l'API Kaggle (fichier `~/.kaggle/kaggle.json` requis, à générer dans
Kaggle > Settings > API > Create New Token). Sinon : téléchargez le zip à la main depuis la page
Kaggle et placez `creditcard.csv` dans `data/raw/`. Le script vérifie l'empreinte MD5 du fichier.
