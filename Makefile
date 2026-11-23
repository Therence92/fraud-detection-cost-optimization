# Reproduire tout le projet :  make all
.PHONY: all data sql model test notebook

all: data sql model test notebook

data:
	python scripts/download_data.py

sql:
	python scripts/run_sql.py

model:
	python scripts/run_pipeline.py

test:
	python -m pytest -q tests

notebook:
	jupyter nbconvert --to notebook --execute --inplace notebooks/analyse_fraude.ipynb
