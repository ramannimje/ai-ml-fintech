.PHONY: install run test train predict format

install:
	pip install -r requirements.txt

run:
	uvicorn app.main:app --reload --port 8000

test:
	pytest -q

train:
	python scripts/train.py gold --horizon 1

predict:
	python scripts/predict.py gold --horizon 7

format:
	python -m compileall app ml scripts
