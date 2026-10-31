# Four-minute demo script

Use November 2026 and fictional data. Confirm the live application works before recording. This is a script, not evidence that a video has been recorded.

0:00–0:25 — Introduce the problem. “This application coordinates employees across brands and processes. Its central concern is valid coverage rather than simply displaying a calendar.” Show 36 employees, 25 brands and three pods.

0:25–1:00 — Show Organisation & rules: one single-owner brand and a multi-owner brand, backup eligibility, daily workload limits and the three calendars. Explain that a process can override its brand's calendar. The holiday is fictional demo data.

1:00–1:40 — Generate a November version. Explain the displayed result: existing valid allocations may be revalidated and preserved; a new solve is used when no valid saved schedule exists. Explain FEASIBLE versus OPTIMAL honestly. Show coverage and switch Company, Pod, Brand, Process and Employee. Point out approved leave and comp-offs.

1:40–2:45 — Select a working day for a single-owner brand's employee. Preview leave with repair disabled. Show the affected duties and specific shortage findings. Enable repair; select a qualified candidate if appropriate; preview again and show the changed assignments. Approve the valid result. Explain which dates remained fixed; if the repair scope expanded, show that scope honestly.

2:45–3:15 — Select a multi-owner brand, inspect process-specific staffing and explain why two remaining employees do not necessarily cover the missing person's process. Demonstrate a second preview if time permits.

3:15–3:40 — Publish a valid roster and inspect the audit trail. Explain that a direct policy change makes old results stale and that unsafe manual edits cannot publish. Show CSV export.

3:40–4:00 — Explain the architecture: React, FastAPI, relational storage, solver and separate validator. Mention the actual limitations: scoped repairs, provisional boundary weeks, no enterprise roles or notifications. Close with the repository and deployment links.

Before sharing: video must last 3–5 minutes, play without requesting access, show no secrets and describe only actual observed behavior.
