# Architecture & Phased Build Plan

Living design doc. Full requirements: `A2.pdf` (FR1-FR4, NFRs, tech stack) and
`Project 24 (SCIT, Ridwan Haq).pdf` (original client brief). Full phased plan
history: see the plan approved at project kickoff (summarized below); update
this file as each phase lands.

## Tech stack (fixed by A2.pdf)

- Frontend: React + TypeScript + Plotly.js (Vite)
- Backend: Python + FastAPI
- Simulation engine (Phase 3+): Google OR-Tools CP-SAT
- Data layer: pandas/openpyxl for parsing, SQLAlchemy + Alembic;
  SQLite for local dev, PostgreSQL planned once multi-user/production use starts
- Deployment (later phase): Docker + Git

## Key structural decision: flattened occurrences

`BaselineScheduleEntry` stores the raw recurring pattern (subject, lab,
duration, delivery weeks, frequency). `app/ingestion/occurrence_expander.py`
immediately expands it into concrete `ScheduleOccurrence` rows
`(lab, week_number, start_datetime, end_datetime)`. Every downstream feature
(utilisation math, double-booking checks, clash diagnostics) operates on flat
occurrences, not recurrence math — this avoids off-by-one bugs between
weekly/fortnightly patterns and keeps the "100% precision on contact hours /
double-booking" NFR tractable.

## Phase status

- **Phase 0 — Scaffolding**: done. FastAPI + SQLAlchemy + Alembic backend,
  Vite/React/TS frontend, health check wired end-to-end, SQLite for dev.
- **Phase 1 — FR1 (Data Ingestion & Integrity Check)**: done for the MVP
  scope. Upload `.xlsx`/`.csv` → flexible column mapping
  (`app/ingestion/column_mapping.py`) → row validation for missing values /
  unrecognized room codes / malformed time blocks
  (`app/ingestion/validators.py`) → summary log in the UI
  (`IngestPage.tsx` / `ValidationSummary.tsx`).
  Open item: swap in a real Enterprise export once provided and verify
  `column_mapping.py` covers its actual headers.
- **Phase 2 — FR2 (Lab Utilisation & Heatmap)**: not started. Needs the
  client's definition of "Available Lab Hours" before the utilisation formula
  can be implemented correctly.
- **Phase 3 — FR3 (Scenario Simulation Engine)**: not started. Highest
  technical risk (CP-SAT infeasibility explanation); see plan for the
  pre-filter → diagnostic → honest-fallback approach.
- **Phase 4 — FR4 (Comparison & Recommendations)**: not started.
- **Phase 5 — RBAC/Auth/Hardening**: not started. PostgreSQL + Docker are
  planned for this phase (or whenever multi-user/production use requires
  them) rather than local dev.

## Data model (current)

`labs`, `ingestion_runs`, `ingestion_errors`, `baseline_schedule_entries`,
`schedule_occurrences` — see `backend/app/db/models/`. `scenarios` /
`scenario_entries` / `scenario_occurrences` / `scenario_clashes` /
`recommendations` are deferred to Phase 3/4.
