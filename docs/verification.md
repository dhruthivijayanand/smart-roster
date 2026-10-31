# Verification evidence

## Completed locally, 30 October 2026
- TypeScript typecheck: passed.
- Vite production build: passed (6.4.5).
- Python constraint and API tests: **24 passed**, latest run 4.58 seconds. See test-results.xml. A FastAPI/Starlette test-client deprecation warning was emitted; no failing assertions.
- Full fictional dataset: 36 employees, 25 brands, 100 brand-process requirements. November 2026 generation with SciPy 1.15.3 / HiGHS returned **FEASIBLE**, 2,708 required and covered monthly staffing slots, zero mandatory violations, 297 soft preference deviations across the extended planning horizon. First observed generation took 30.99 seconds. This is an observed run, not a performance guarantee or proof of optimality.
- Browser management creation/deactivation and 390px responsive layout: passed in first browser run.
- First full browser flow exposed a same-day repair infeasibility caused by backup weekly rest. Added explicit, manager-reviewed repair-window expansion and reran all backend tests successfully. Both browser tests now pass (59.8 seconds): generation, five views, rejected unsafe edit, validated repair, apply, publish, reload, validation, management and mobile layout.

## Production checks, 31 October 2026
- Public Vercel application and Neon PostgreSQL: verified without sign-in.
- Both production Playwright tests passed in 1.4 minutes: generation, all five views, unsafe absence rejection, repair preview/apply, publication, reload, validation, management creation/deactivation and 390px layout.
- Initial concurrent startup exposed hard-coded seed IDs. Fixed with generated-ID references and PostgreSQL advisory initialization locks; added an idempotent, shifted-ID seed regression test.

## Pending
- Full multi-instance PostgreSQL concurrency verification.
- Clean-checkout dependency installation on a second machine has not been repeated.

## Important distinction
The initial architecture proposed CP-SAT. Repeated official wheel download timeouts prevented local installation. A mathematically equivalent integer model using already-installed SciPy/HiGHS is implemented and tested. CP-SAT remains an optional backend, but has not been runtime-tested locally. Both use independent allocation validation; solver identity is retained in the payload. HiGHS time-limited feasible incumbents are not claimed deterministic across different cutoff timing or solver versions.


The live recording exposed a fresh-generation time limit after an applied absence. A feasibility-first experiment also timed out and was not retained. Generation now independently revalidates recent schedules and preserves a valid allocation as a new version; a regression test verifies this behavior. New optimisation remains necessary when no saved allocation passes validation.

## Additional production workflow check
The final live UI run completed a revalidated new version, all five views, unsafe absence preview, successful repair, approval, publication, reload, validation and audit history. The second absence was on 3 November; four allocations were removed and four added.

## Candidate video
The candidate will record and present their own walkthrough. No demo video has been uploaded or included in the submission package.
