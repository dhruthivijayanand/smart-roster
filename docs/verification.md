# Verification evidence

## Completed locally, 30 October 2026
- TypeScript typecheck: passed.
- Vite production build: passed (6.4.5).
- Python constraint and API tests: **22 passed**, latest run 3.69 seconds. See test-results.xml. A FastAPI/Starlette test-client deprecation warning was emitted; no failing assertions.
- Full fictional dataset: 36 employees, 25 brands, 100 brand-process requirements. November 2026 generation with SciPy 1.15.3 / HiGHS returned **FEASIBLE**, 2,708 required and covered monthly staffing slots, zero mandatory violations, 297 soft preference deviations across the extended planning horizon. First observed generation took 30.99 seconds. This is an observed run, not a performance guarantee or proof of optimality.
- Browser management creation/deactivation and 390px responsive layout: passed in first browser run.
- First full browser flow exposed a same-day repair infeasibility caused by backup weekly rest. Added explicit, manager-reviewed repair-window expansion and reran all backend tests successfully. Full browser flow is being rerun; do not claim it passed yet.

## Pending
- Production PostgreSQL connectivity and concurrency verification.
- Public deployed app and production generation/edit/reload checks.
- Final 3–5 minute video recording and accessible link.

## Important distinction
The initial architecture proposed CP-SAT. Repeated official wheel download timeouts prevented local installation. A mathematically equivalent integer model using already-installed SciPy/HiGHS is implemented and tested. CP-SAT remains an optional backend, but has not been runtime-tested locally. Both use independent allocation validation; solver identity is retained in the payload. HiGHS time-limited feasible incumbents are not claimed deterministic across different cutoff timing or solver versions.
