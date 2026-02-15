.PHONY: dev build test lint backend-dev frontend-dev

dev:
	docker compose up --build

backend-dev:
	uvicorn backend.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm install && npm run dev

build:
	cd frontend && npm run build

test:
	pytest -q backend/tests
	cd frontend && npm run test

lint:
	cd frontend && npm run lint && npm run typecheck
