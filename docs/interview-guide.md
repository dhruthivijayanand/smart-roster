# Technical interview preparation

Use these explanations after reviewing the corresponding code. They describe the delivered implementation, not claims of independent authorship.

## Explain the architecture in one minute
The React client collects rules and displays schedules. FastAPI validates input and coordinates transactions. SQLAlchemy persists entities, allocations, roster snapshots and change history in PostgreSQL. An integer solver proposes assignments; a separate validator recomputes the mandatory rules before publication. This separation keeps the UI simple and makes solver mistakes detectable.

## Explain the resource model
An assignment variable x(employee, duty, day) is binary. A duty is one brand/process requirement. Coverage is the sum of distinct assigned employees and must equal its minimum. Each assignment consumes effort units from the employee's shared daily capacity, across all brands. Exclusive intervals additionally prevent overlapping work. Four one-unit duties can fit within eight units; four simultaneous exclusive duties cannot. Eligibility is permission to work, not evidence that the employee is available.

## Explain hard versus soft rules
Leave, eligibility, operating dates, workload, overlap, staffing and weekly rest are hard constraints. A schedule with any mandatory violation cannot publish. Preferred off weekdays are soft: a valid schedule may violate them, but the deviations remain visible. The solver prioritises repair stability, primary ownership and then preferred offs in separate optimisation phases. FEASIBLE means a valid incumbent was found; it does not prove the best possible objective.

## Explain an absence change
The preview records the proposed absence and validates its immediate effect. Without repair, the manager sees uncovered duties. Repair initially fixes other dates, then may expand seven days either side if same-day repair is infeasible because of rest constraints. The manager sees the scope and allocation differences before approval. Applying checks revisions again, saves the changes transactionally and records an audit entry. It does not quietly change eligibility or lower demand.

## Explain persistence and the production bug
Entity attributes use validated JSON while identity, foreign keys and uniqueness constraints use real relational columns. The initial PostgreSQL startup exposed a mistake: generated IDs were assumed to start at one. PostgreSQL sequences can advance even when a transaction rolls back. Seeding now uses returned IDs and PostgreSQL advisory transaction locks to coordinate concurrent initialization. A regression test seeds into an existing database with shifted IDs. This is a good example of why local SQLite testing is insufficient for deployment confidence.

## Explain limits candidly
The tested backend is SciPy/HiGHS MILP. CP-SAT is optional and was not runtime-tested. Roster generation is synchronous; a process-local lock does not serialize all serverless instances. Revision checks are useful but are not a complete distributed concurrency design. There are no enterprise user roles, schema migrations or fairness optimisation. Adjacent unapproved weeks are provisional. Production hardening would start with authentication, database-level job/revision locks, migrations and PostgreSQL concurrency tests.

## Code-reading order
1. schemas.py: what managers can configure.
2. domain.py: eligibility, calendars and date boundaries.
3. milp_scheduler.py: variables, constraints and objective phases.
4. validation.py: checks independent of the solver.
5. services.py: snapshots, preview/apply and publication.
6. database.py and seed.py: relational constraints and initialization.
7. tests: invalid fixtures and transaction scenarios.

Practise changing one rule, predicting the resulting schedule or error, then running the corresponding test. Do not claim to have understood a module until you can explain its inputs, outputs and failure cases.
