# Approach note

The system models staffing as an employee–brand–process allocation problem, with configurable calendars, approved absences, daily workload capacity and mandatory rest rules. An integer optimisation solver (HiGHS, with optional CP-SAT) generates and repairs monthly schedules, while an independent validator blocks publication of invalid rosters and explains coverage gaps separately from preference deviations. Managers review replacement proposals before committing changes; the relational database preserves allocations, revisions and audit history.
