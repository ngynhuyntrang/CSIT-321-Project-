# SCIT Computing Lab Scheduling

Capstone project (CSIT321, UOW SCIT) replacing manual Enterprise timetable review
with lab utilisation analytics and scenario-modelling for scheduling decisions.
See `docs/A2.pdf` and `docs/Project 24 (SCIT, Ridwan Haq).pdf` for the full
requirements, and `docs/architecture.md` for the phased build plan.

Current scope: **Phase 0 (scaffolding) + Phase 1 (FR1 — timetable data
ingestion & integrity check)**, rebuilt against the real UOW Enterprise
export at `docs/SCIT 2026 Lab Bookings.xlsx`, plus **sign-in with
role-based access, admin booking management, and student pages** (class
selection, timetable, lab availability, feedback) as designed in
`docs/SCIT Lab Scheduling Prototype.html`. FR2 (lab utilisation) is
designed but not implemented — see `docs/architecture.md` for the open
questions that need confirmation from the client before it's built.

## Backend (FastAPI)

```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
alembic upgrade head          # or rely on dev auto-create-all on startup
python -m scripts.seed_real_rooms   # seeds the 7 real SCIT room codes
python -m scripts.create_admin you@uow.edu.au "Your Name"   # first admin; prompts for a password
uvicorn app.main:app --reload --port 8000
```

### Accounts and roles

Everything except `/api/health` requires sign-in (`Authorization: Bearer`
token from `POST /api/auth/login`). Sign-up needs a `@uow.edu.au` or
`@uowmail.edu.au` email.

| Role | Can | Gets it by |
|---|---|---|
| `student` | choose classes, view own timetable, lab availability, send feedback | signing up as Student (active immediately) |
| `staff` | read bookings, availability and feedback | signing up as SCIT Staff, then an admin approves |
| `admin` | upload exports, add/adjust/cancel bookings, approve users, review feedback | `scripts/create_admin.py`, or an admin changes the role |

Bookings and the student pages read the **active baseline** — the most
recent completed upload. Admin edits are checked for room double-bookings
(blocked) and capacity/cohort overlaps (warnings), and every change is kept
in a per-booking history.

Run tests: `pytest` (from `backend/`, with the venv active).
Lint: `ruff check app`.

Room codes must be seeded before an upload can validate against them — run
`scripts/seed_real_rooms.py` above. Room `capacity` is populated from the
export's "Capicity" column on the first upload that includes a given room
(left `null` until then); `weekly_available_hours` has no source in the
export and stays `null` until confirmed with SCIT Operations — see
`docs/architecture.md`.

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
