> Live demo: https://smart-roster-dhruthi934-2771.vercel.app/
> Repository: https://github.com/dhruthivijayanand/smart-roster
> Candidate: Dhruthi Vijayanand · https://www.linkedin.com/in/dhruthi-v-877a65286/

# DataStraw Smart Roster Management

A constraint-based operations planner built for the DataStraw internship assessment.

**Author / candidate:** Dhruthi Vijayanand  
**LinkedIn:** https://www.linkedin.com/in/dhruthi-v-877a65286/

## Current delivery status
Publicly deployed on Vercel with Neon PostgreSQL. The backend suite has 24 passing tests; the public browser workflow covers generation/versioning, five views, absence preview/repair, publication and persistence. See docs/verification.md and docs/implementation-checklist.md for evidence and remaining limits.

## Run locally
Requires Python 3.10–3.12 and Node 20.19+ (Node 22 or 24 recommended).

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
Copy-Item .env.example .env
cd frontend
npm ci
npm run build
cd ..
.venv\Scripts\python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000. On first launch, tables and fictional sample data are created. Local SQLite is persisted in roster.db. API documentation is at /docs. For frontend development, run the API and `npm run dev` inside frontend; Vite proxies /api to port 8000.

```powershell
.venv\Scripts\python -m pip install -r requirements-dev.txt
.venv\Scripts\python -m pytest -q
```

## Production
Use PostgreSQL via DATABASE_URL, APP_ENV=production and DEMO_SEED=true for this fictional assessment demo. Production explicitly rejects SQLite to prevent ephemeral data loss. Frontend assets and FastAPI can share one host. Dockerfile and render.yaml provide a container deployment path; provision a persistent database first. A MANAGER_TOKEN can restrict mutations; enter it through the profile button. Never commit .env or credentials. Public unauthenticated mode is only for fictional demonstration data.

## Working through the demo
1. Generate November 2026. Review solver status, coverage and hard findings.
2. Switch between Company, Pod, Brand, Process and Employee. Brand/process views show daily staffing and operating calendar names.
3. Open Organisation & rules to inspect primary owners, qualified backups, calendars, date-specific staffing, leave and comp-offs.
4. Select a working employee-day. Preview leave without repair to expose coverage gaps across duties.
5. Enable repair, optionally choose a replacement, then preview. Approve the validated diff. Unaffected dates remain fixed.
6. Publish only when hard constraints pass. Change a rule to see the old published roster become stale.
7. Review the audit trail and export CSV.

## Eight assessment questions

### 1. How are employees, brands, processes and pods related?
Employees belong to pods. Pods reference an employee lead whose membership is validated. BrandProcess duties join brands to reusable process definitions. EmployeeAssignment joins people to duties with effective dates and a primary/backup role. Operating calendars, absences, holidays and date-specific staffing overrides are separate records. SQLAlchemy tables have real primary/foreign keys and unique relationships; flexible validated attributes use JSON columns. Allocation is a relational employee-duty-date row under a roster version. Roster payloads retain computed results and audit snapshots.

### 2. How does generation establish validity?
The default installed backend is SciPy/HiGHS mixed-integer optimisation. Optional OR-Tools CP-SAT is selected when installed. Both models choose binary employee-duty-date allocations and workday variables. Hard constraints enforce operation, eligibility, availability, distinct staffing, global workload, exclusive interval incompatibility, weekly rest and consecutive-day limits. Adjacent weeks provide boundary context. Published neighbouring months are fixed when present. A separate validator rechecks allocations before publication and after changes. FEASIBLE differs from OPTIMAL; UNKNOWN is never described as infeasible. An INFEASIBLE model can produce a labelled shortage diagnostic, which cannot publish.

### 3. Single-resource versus multi-employee brands?
There is no special shortcut in coverage arithmetic: every brand-process has demand and eligible people. Twenty of 25 seeded brands have a single primary owner for all processes. The remaining five have two or three primary staff with distinct and overlapping responsibilities. Backup eligibility is separate from ownership. Minimum staffing greater than one requires distinct employees, not multiple copies of one employee.

### 4. What if a sole owner is unavailable?
Preview inserts their proposed absence into a copy of current inputs and removes every allocation for that person/date. It reports affected processes and gaps, lists eligible replacements with capacity, then optionally solves a repair with other dates locked. The manager reviews and approves the diff. If no valid repair exists, application is blocked. Managers can record a real absence through management even when coverage cannot be solved; this marks published rosters stale rather than pretending availability remains unchanged.

### 5. Conflicts and insufficient staffing?
Hard findings include date, brand/process, required/eligible/assigned headcount, employee, reason and suggested remedy. Capacity is global across brands. Individually eligible people are not promised to be jointly available. Mandatory constraints are not silently relaxed. Diagnostic shortfall allocations are explicitly non-publishable. Preferences appear separately.

### 6. Automated versus human-controlled?
The solver automates allocation and scoped repair. The validator automates checking. Managers control master data, eligibility, demand, calendars, approval and publication. Human approval is retained because changing client requirements or assigning a new backup is an operational decision, not something an optimisation routine should invent.

### 7. What changes if size doubles?
Measure model construction, solve time and query sizes first. Pre-index eligibility and demand, move generation into persisted background jobs, use database-level job locks and avoid full snapshot payloads in routine reads. Partition only by truly independent employee-duty components; splitting arbitrary brands could break shared capacity. Add pagination/virtualised grids, explicit schema migrations, identity/roles, stronger multi-user revision semantics and PostgreSQL concurrency tests. Do not add microservices without evidence.

### 8. What comes first with another week?
Strengthen published adjacent-month consistency and richer partial-repair scope expansion; add full PostgreSQL concurrency tests and versioned policy snapshots; improve infeasibility explanations using labelled constraints; implement capacity-normalised fairness and warm-start repair. Add authenticated roles, migration tooling, database-level generation locks and broader accessibility testing before real operational use.

## Assumptions and boundaries
- Generating another version preserves a prior valid allocation after independent revalidation against current rules and published neighbouring months. The UI labels reuse explicitly. Invalid saved schedules are never reused; a new solve may return UNKNOWN if its time limit expires without a valid incumbent.

- Planning timezone: Asia/Kolkata; dates are local dates, audit times UTC.
- Fictional rest default: one day off per Monday–Sunday week and maximum six consecutive workdays. Configurable, not a DataStraw-supplied or legal rule.
- Daily capacity default: eight units. Seeded single-owner duties use one unit each; multi-owner duties use two. Units describe divisible daily work, not simultaneous full-day presence. Configure exclusive intervals for simultaneous duty restrictions. Overnight shifts are rejected.
- A process calendar replaces the brand default. Explicit dated staffing overrides take precedence. Demo holidays are fictional. Holiday does not itself mean every employee is unavailable.
- Approved leave, comp-off, unavailability and mandatory offs are hard. Preferred weekdays are soft; pending leave does not block scheduling.
- Solver prioritises feasibility, then preserving allocations on repair, then primary ownership, then off preferences. No arbitrary weighted mixture. Fairness optimisation is not implemented yet.
- Provisional adjacent weeks are scheduled for rest checks. Published neighbouring months are locked. This is not a promise that unapproved future rosters already exist.
- Repair first fixes every other date. Proven same-day infeasibility triggers an explicitly labelled window of up to seven days on either side for rest-day swaps. The manager sees the expanded scope and complete diff before approval; dates outside that scope remain fixed.
- Data edits conservatively stale all published rosters. Record deletion is soft deactivation with dependency checks.
- CP-SAT uses a fixed seed, one worker and deterministic search limits. HiGHS uses a 30-second limit per lexicographic phase and checks integer incumbents before independent validation. Time-limited feasible output is not claimed optimal or guaranteed identical across runs. Local PyPI and GitHub wheel timeouts motivated the HiGHS fallback; this is a documented implementation change from the initial proposal. Install requirements-cpsat.txt to enable CP-SAT.
- Schema creation uses SQLAlchemy create_all for this initial release; Alembic migrations from the original proposal are not yet implemented. Existing databases are not automatically migrated.
- Optional multi-role approval, notifications, alternative plans and AI-generated explanations are not implemented.

## Project map
backend/app/schemas.py — validated inputs; database.py — persistence; domain.py — calendar primitives; scheduler.py — solver selection; milp_scheduler.py — tested HiGHS model; cp_sat_scheduler.py — optional CP-SAT; validation.py — independent checks; services.py — transactions and change control; main.py — API; seed.py — fictional data. frontend/src contains typed API helpers and focused React views. tests contains constraint and API integration tests.

## Technical references
- https://developers.google.com/optimization/cp/cp_solver
- https://fastapi.tiangolo.com/deployment/docker/
- https://www.postgresql.org/docs/current/ddl-constraints.html

AI assistance was used to develop this project. Review and understand the implementation before presenting personal technical ownership; no claim is made that the candidate independently authored every line.
