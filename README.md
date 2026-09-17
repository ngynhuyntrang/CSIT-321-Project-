# SCIT Computing Lab Scheduling

Capstone project (CSIT321, UOW SCIT) replacing manual Enterprise timetable review
with lab utilisation analytics and scenario-modelling for scheduling decisions.
See `docs/A2.pdf` and `docs/Project 24 (SCIT, Ridwan Haq).pdf` for the full
requirements, and `docs/architecture.md` for the phased build plan.

Current scope: **Phase 0 (scaffolding) + Phase 1 (FR1 — timetable data
ingestion & integrity check)**, rebuilt against the real UOW Enterprise
export at `docs/SCIT 2026 Lab Bookings.xlsx`. FR2 (lab utilisation) is
designed but not implemented — see `docs/architecture.md` for the open
questions that need confirmation from the client before it's built.

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head          # or rely on dev auto-create-all on startup
python -m scripts.seed_real_rooms   # seeds the 7 real SCIT room codes
uvicorn app.main:app --reload --port 8000
```

Run tests: `pytest` (from `backend/`, with the venv active).
Lint: `ruff check app`.

Room codes must be seeded before an upload can validate against them — run
`scripts/seed_real_rooms.py` above (capacity/operating-hours are left `null`
until confirmed with SCIT Operations; see `docs/architecture.md`).

## Frontend (React + TypeScript + Vite)

```bash
cd frontend
npm install
npm run dev      # http://localhost:5173, proxies /api to http://localhost:8000
```

Type-check: `npx tsc -b`. Lint: `npm run lint`. Build: `npm run build`.

## Sample data

`backend/tests/fixtures/sample_upload.xlsx` mirrors the real export's column
headers and formats (Enterprise-style `HH:MM` durations, 12-hour times,
`D/M/YYYY` activity dates) and covers the validation edge cases found in the
real file: a joint undergrad/postgrad subject row, a zero-cohort-size
booking, an unrecognized room code, a malformed duration, a malformed date,
and a start/end/duration mismatch. `docs/SCIT 2026 Lab Bookings.xlsx` is the
real client export, used for manual end-to-end verification.
