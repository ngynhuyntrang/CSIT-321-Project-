# Architecture & Phased Build Plan

Living design doc. Full requirements: `A2.pdf` (FR1-FR4, NFRs, tech stack) and
`Project 24 (SCIT, Ridwan Haq).pdf` (original client brief). This rebuild
replaces an earlier FR1 pass that was validated only against a synthetic
fixture; it is preserved on the `archive/fixture-based-fr1` branch. This
rebuild is driven by the real export: `docs/SCIT 2026 Lab Bookings.xlsx`.

## Tech stack (fixed by A2.pdf)

- Frontend: React + TypeScript + Plotly.js (Vite) — Plotly.js is added when
  FR2's heatmap is implemented; not needed for FR1.
- Backend: Python + FastAPI
- Simulation engine (Phase 3+): Google OR-Tools CP-SAT
- Data layer: pandas/openpyxl for parsing, SQLAlchemy + Alembic;
  SQLite for local dev, PostgreSQL planned once multi-user/production use starts
- Deployment (later phase): Docker + Git

## Key structural decisions

- **Dates, not derived recurrence, are ground truth.** The real export's
  "Activity Dates (Individual)" column gives exact calendar dates per
  occurrence. `app/ingestion/occurrence_expander.py` builds
  `ScheduleOccurrence` rows directly from those dates + start time + duration
  — it does not derive dates from a week number, weekday, and an assumed
  semester start (the earlier fixture-based approach). That approach would
  have silently misdated the 7/276 real rows where "Number Of Teaching
  Weeks" doesn't match the actual date count.
- **`week_number` is never guessed.** `Teaching Week Pattern` /
  `Number Of Teaching Weeks` are parsed only for a non-blocking cross-check
  warning against the date count — they are never used to assign a week
  number to an occurrence, because positionally pairing dates to a week
  pattern is an unverified guess, not a fact. `ScheduleOccurrence.week_number`
  stays `null` until a verified date→teaching-week reference (e.g. an
  official UOW semester calendar) is introduced as a separate input.
- **Unknown numbers are stored as `null`, never invented.** The export has no
  room capacity or operating-hours data. `Lab.capacity` and
  `Lab.weekly_available_hours` are nullable and seeded as `null`
  (`scripts/seed_real_rooms.py`) rather than a guessed or zero value — `0`
  would falsely mean "no capacity" instead of "unknown". Any future
  capacity- or utilisation-percentage calculation must check for `null` and
  report "not available" rather than compute against it.
- **Two-severity validation.** `IngestionError.severity` is `"error"` (row
  excluded from the baseline: missing field, unrecognized room, unparseable
  duration/time/date) or `"warning"` (row still inserted, flagged for
  review: cohort size recorded as 0, a start/end/duration mismatch, or a
  date-count vs. teaching-week-count mismatch). The ingestion summary and the
  frontend show these as two separate tables, not one merged list.

## Phase status

- **Phase 0 — Scaffolding**: done. FastAPI + SQLAlchemy + Alembic backend,
  Vite/React/TS frontend, health check wired end-to-end, SQLite for dev.
- **Phase 1 — FR1 (Data Ingestion & Integrity Check)**: done, rebuilt against
  the real Enterprise export format (`docs/SCIT 2026 Lab Bookings.xlsx`).
  Upload `.xlsx`/`.csv` → flexible column mapping
  (`app/ingestion/column_mapping.py`) → subject-code extraction from
  `Module Name` (`app/ingestion/parser.py`) → row validation
  (`app/ingestion/validators.py`) → severity-aware summary log in the UI
  (`IngestPage.tsx` / `ValidationSummary.tsx`).
- **Phase 2 — FR2 (Lab Utilisation & Heatmap)**: **design only, not
  implemented.** Open items below need client confirmation before building.
- **Phase 3 — FR3 (Scenario Simulation Engine)**: not started.
- **Phase 4 — FR4 (Comparison & Recommendations)**: not started.
- **Phase 5 — RBAC/Auth/Hardening**: not started. PostgreSQL + Docker are
  planned for this phase (or whenever multi-user/production use requires
  them) rather than local dev.

## FR2 design sketch — assumptions requiring confirmation from Ridwan Haq

The real export shows all 7 SCIT rooms are shared-purpose: the same room
hosts Computer Lab, Lecture, Tutorial, Practical, and Workshop bookings.
FR2's wording ("lab utilisation") could mean either "Computer-Lab-activity
only" or "the room's total occupancy regardless of activity type" — these
give materially different numbers. Current working assumption, **pending
confirmation**:

- **Room occupancy counts all activity types** in that room (the room isn't
  available to be booked as a lab if it's booked for a lecture), reported as
  the headline "Booked Hours" metric, **plus** a separate
  `booked_computer_lab_hours` breakdown filtered to `class_type == "Computer
  Lab"` only, and a UI filter to view by activity type.
- **Overlap rule**: two occurrences in the same room overlap only if
  `a.start < b.end AND b.start < a.end` (strict inequalities) — back-to-back
  bookings (e.g. 09:00–10:00 and 10:00–11:00) touch at a point and are *not*
  overlapping. Overlapping intervals are merged into one block for "Booked
  Hours" (so double-counted time isn't reported as more capacity used than
  physically possible), and every merge is also recorded as a
  `SchedulingConflict` (room, date, contributing occurrence IDs) surfaced
  separately — this doubles as the NFR's "100% precision on room
  double-booking" check.
- **Utilisation percentage is not computed until "Available Lab Hours" is
  defined**, which needs: (a) a configured weekly operating window per room
  (not in the export), and (b) a holiday/non-teaching-week calendar (not
  available). Until both are confirmed and configured, FR2 shows Booked
  Hours only — never a percentage against an invented or default
  denominator. A booking outside a configured operating window would be
  flagged as a warning once a window exists.

## Data model (current)

`labs`, `ingestion_runs`, `ingestion_errors`, `baseline_schedule_entries`,
`schedule_occurrences` — see `backend/app/db/models/`. Fields FR1 already
persists that FR2 will need: `class_type`, `lab_id`, `week_number`
(nullable), `start_datetime`/`end_datetime` per occurrence, `cohort_size`
(+ its zero-value warning) — no schema change should be needed to build FR2.
`scenarios` / `scenario_entries` / `scenario_occurrences` / `scenario_clashes`
/ `recommendations` are deferred to Phase 3/4.
