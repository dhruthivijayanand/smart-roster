# Implementation checklist — 31 October 2026

This supersedes the status column in the original architecture proposal. Status vocabulary: Not started / In progress / Implemented / Tested / Verified. Verified means observed in the stated environment, not exhaustive correctness.

| ID | Requirement | Status | Evidence / limitation |
|---|---|---|---|
| 1 | Employees, pods, leads, brands, processes | Verified | 36 fictional employees, three pods, lead validation and management forms |
| 2 | 80% single-owner brands | Verified | Live API: 20 single-owner, three two-owner and two three-owner brands; backups counted separately |
| 3 | Distinct/shared processes and minimum >1 | Tested | Unit fixtures; seed includes a two-person requirement |
| 4 | Cross-brand/process assignment editing | Tested | Eligibility CRUD, effective dates and global capacity tests |
| 5 | Three calendar types and process overrides | Tested | Parameterised calendar fixtures and management forms |
| 6 | Specific-day minimum staffing | Tested | Dated demand overrides; separate recurring weekday demand overrides were not implemented |
| 7 | Weekly offs, leave, comp-off, holidays | Tested | Approved absence/rest/calendar tests; real absence repair in production |
| 8 | Organisation-wide month generation | Verified | November 2026 generated on public Vercel/Neon; alternate month/leap-year unit cases |
| 9 | Coverage, overlap, absence and capacity conflicts | Tested | Deliberately invalid fixtures and independent validator |
| 10 | Hard rules versus preferences | Verified | Unsafe proposal blocked; soft findings shown separately |
| 11 | Truthful infeasibility explanation | Tested | Shortage findings and non-publishable diagnostic output; no full minimal-conflict explanation engine |
| 12 | Company view | Verified | Public browser workflow |
| 13 | Pod view | Verified | Public browser workflow |
| 14 | Brand view | Verified | Public browser workflow |
| 15 | Process view | Verified | Public browser workflow |
| 16 | Employee view | Verified | Public browser workflow |
| 17 | Manual preview/apply and validation | Verified | Public unsafe edit, repaired preview, approval and publication |
| 18 | Post-generation staffing changes | Tested | Single-owner browser example; multi-resource API fixture |
| 19 | Scoped repair preserving unaffected work | Tested | Fixed-date preservation test; explicit expanded window for rest swaps |
| 20 | Documented/configurable assumptions | Implemented | README and validated management forms |
| 21 | Dynamic entity management | Verified | Process creation/deactivation and persistence through public UI; other entity forms implemented |
| 22 | Capacity and incompatible intervals | Tested | Shared workload and overlap fixtures |
| 23 | Actionable conflict details | Tested | Dates, duties, counts, reasons, severity and remedies |
| 24 | Dashboard, filters, responsive UI | Verified | Five public views and 390px layout check |
| 25 | Approval, audit and preservation | Verified | Public preview/apply/publish/reload; stale revision API tests |
| 26 | Unit/integration/end-to-end tests | Verified | 24 backend tests; two public browser tests, 1.4 minutes |
| 27 | Public persistent deployment | Verified | Vercel with Neon PostgreSQL; public browser reload after publication |
| 28 | Repository and setup documentation | Implemented | Source, setup instructions, environment example and evidence included; final clean-checkout dependency installation was not repeated |
| 29 | Video, approach note and LinkedIn | In progress | Candidate will record and share their own 3–5 minute walkthrough. Approach note, script and LinkedIn are ready. |
| 30 | Eight README answers | Implemented | README answers each assessment question |
| 31 | Fairness, backups, export | Implemented | Backups and CSV work; fairness optimisation deferred |
| 32 | Alternatives, notifications, roles, AI explanations | Not started | Explicitly deferred optional enhancements |

## Engineering changes from the approved proposal
- Tested solver: SciPy/HiGHS mixed-integer optimisation. OR-Tools CP-SAT remains optional and unverified at runtime after package-download failures.
- SQLAlchemy create_all replaces the proposed Alembic migrations for this initial release; no automatic schema migration is claimed.
- JSON attributes with relational foreign keys replace a fully normalised attribute schema; inputs are validated by Pydantic.
- Dated staffing overrides are implemented; recurring weekday-specific staffing overrides are not a separate feature.
- A database advisory lock protects PostgreSQL initialization. Runtime generation still has a process-local lock, not a distributed job system.
- Multi-user concurrent publication and full PostgreSQL race-condition testing remain production-hardening work.
- The public demo permits edits to fictional data. It is unsuitable for private employee information without authentication and operational hardening.
