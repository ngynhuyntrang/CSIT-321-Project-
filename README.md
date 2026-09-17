# SCIT Computing Lab Scheduling

Capstone project (CSIT321, UOW SCIT) replacing manual Enterprise timetable review
with lab utilisation analytics and scenario-modelling for scheduling decisions.
See `docs/A2.pdf` and `docs/Project 24 (SCIT, Ridwan Haq).pdf` for the full
requirements, and `docs/architecture.md` for the phased build plan.

Current scope: **Phase 0 (scaffolding) + Phase 1 (FR1 — timetable data
ingestion & integrity check)**.

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head          # or rely on dev auto-create-all on startup
uvicorn app.main:app --reload --port 8000
```

Run tests: `pytest` (from `backend/`, with the venv active).
Lint: `ruff check app`.

Seed labs before uploading a timetable (no admin UI yet — use the API):

```bash
curl -X POST http://localhost:8000/api/labs \
  -H "Content-Type: application/json" \
  -d '{"code":"3.G17","capacity":48,"room_type":"computing"}'
```

## Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to http://localhost:8000
```

Type-check: `npx tsc --noEmit`. Lint: `npm run lint`. Build: `npm run build`.

## Sample data

`docs/sample-enterprise-exports/semester_export_sample.xlsx` is a synthetic
Enterprise-format export (47 valid rows + 3 intentionally invalid rows: one
missing value, one unrecognized room code, one malformed time block) used for
manual testing and as the integration test fixture. Replace/extend with a real
export once available from the client, and adjust
`backend/app/ingestion/column_mapping.py` if real header names differ.
