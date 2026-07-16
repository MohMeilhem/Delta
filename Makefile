# Delta — dev orchestration
# `make dev` starts backend on :8000 and frontend on :5173

BACKEND_PY := backend/.venv/Scripts/python
ifeq ($(OS),Windows_NT)
	BACKEND_PY := backend/.venv/Scripts/python
else
	BACKEND_PY := backend/.venv/bin/python
endif

.PHONY: dev backend frontend install test

dev:
	$(MAKE) -j2 backend frontend

backend:
	cd backend && .venv/Scripts/python -m uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm run dev

install:
	cd backend && python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
	cd frontend && npm install

test:
	cd backend && .venv/Scripts/python -m pytest -q
