# Phase 5 — Testing
## Startup Incubation and Startup Management System

*Builds on: all modules in `app/` and the SQL scripts in `sql/` · Next: Phase 6 (report + presentation)*

---

## 1. Test strategy

Testing was done at three levels:

| Level | What is tested | How | Evidence |
|---|---|---|---|
| **1. Database** | Every constraint (NOT NULL, UNIQUE, CHECK, PK, FK with RESTRICT/CASCADE, partial unique index, identity) and the report queries | SQL scripts run with `psql` | `results/constraint_tests_output.txt`, `results/query_outputs.txt` |
| **2. Application functions** | The Python functions behind each screen: correct results, correct database state afterwards, correct rejection of invalid input, transaction rollback | `tests/test_app.py` (TC-01 to TC-53) | `results/test_results.md` |
| **3. User interface** | Every screen of every role opens without errors, and constraint errors are shown as readable messages | `tests/test_app.py` using Streamlit's `AppTest` (TC-54 to TC-56), plus the manual checklist in §5 | `results/test_results.md` |

**Known starting state.** Before each group of tests, `tests/test_app.py` reloads `sql/02_sample_data.sql`, so every group starts from the same known data. It reloads again at the end, so the database is left clean.

**How a test checks the database.** A test doesn't trust only the function's return value; it also queries the database. For example, TC-19 checks that after a failed admit, the application is **still** "Under Review" **and** no incubation row exists. That's how the rollback is proven.

---

## 2. How to run the tests

From the project folder:

```
.\.venv\Scripts\activate
python tests/test_app.py
```

To regenerate the SQL-level evidence:

```
psql -U postgres -d incubation_db -f sql/03_constraint_tests.sql > results/constraint_tests_output.txt 2>&1
psql -U postgres -d incubation_db -f sql/04_queries.sql          > results/query_outputs.txt 2>&1
```

---

## 3. Results summary (run on 2026-11-06)

| Area | Test cases | Passed |
|---|---|---|
| Module 1 — Startup Management | TC-01 – TC-11 | 11 / 11 |
| Module 2 — Application Management | TC-12 – TC-23 | 12 / 12 |
| Module 3 — Evaluation Management | TC-24 – TC-34 | 11 / 11 |
| Module 4 — Mentor Management | TC-35 – TC-43 | 9 / 9 |
| Module 5 — Progress Management | TC-44 – TC-53 | 10 / 10 |
| User interface | TC-54 – TC-56 | 3 / 3 |
| **Total (application)** | | **56 / 56** |
| Database constraint script (`03_constraint_tests.sql`) | T1–T15 must fail, V1–V6 must succeed | 15 / 15 rejected with the expected constraint, 6 / 6 succeeded |

The full table, with the expected and actual value for every test, is in [results/test_results.md](../results/test_results.md).

---

## 4. Coverage of the requirements

| Requirement / concept | Test cases |
|---|---|
| INSERT | TC-01, 12, 14, 29, 34, 37, 47 |
| UPDATE | TC-08, 15, 22, 41, 50, 51 |
| DELETE (CASCADE and RESTRICT) | TC-09, 10, 33, 34, 42 |
| NOT NULL / UNIQUE / CHECK | TC-02, 03, 04, 05, 31, 48, 53 |
| Primary keys (composite) | TC-30, 38 |
| Foreign keys | TC-09, 33, 40, 42 |
| Partial unique index (BR-3) | TC-13, 14 |
| Transactions and rollback (Atomicity) | TC-01, 02, 03, 19, 20 |
| Business rules BR-1, BR-5, BR-6, BR-7, BR-8, BR-10 | TC-11, 30, 31, 18–21, 39–40, 53 |
| Joins (INNER, LEFT, multi-table) | TC-27, 35, 36, 43, 45 |
| Aggregates, GROUP BY, HAVING | TC-23, 24, 27, 44 |
| Subquery / correlated subquery / NOT EXISTS / EXISTS | TC-25, 26, 28, 52 |
| View | TC-45 |
| Role-based views (D5) | TC-28, 43, 51, 52, 55 |
| Invalid input shown as a readable message | TC-56 |

---

## 5. Manual test checklist (browser, for the demonstration)

Start the app with `streamlit run app/app.py`, and reload the sample data first.

| # | Role / screen | Action | Expected |
|---|---|---|---|
| M1 | Admin → Startups → Register | Register a startup using an existing founder email | Error "A founder with this email already exists."; the startup is **not** in the list (rollback) |
| M2 | Admin → Startups → Delete | Delete VidyaPath Learning | Error: has applications (RESTRICT) |
| M3 | Startup → CareConnect → My applications | Submit a new application | Error: already has an open application |
| M4 | Admin → Applications → Update status | Move CareConnect (#10) to Under Review | Success |
| M5 | Evaluator → any → Pending | CareConnect appears; score it | Saved; it leaves the queue |
| M6 | Admin → Applications → Admit | Admit #10 with end date before start | Error; still Under Review |
| M7 | Admin → Applications → Admit | Admit #10 with valid dates | Accepted, incubation created |
| M8 | Admin → Mentors → Assign | Assign a mentor to CareConnect | Success; appears under Assignments |
| M9 | Admin → Progress → Add milestone | Add a milestone for CareConnect | Status Pending |
| M10 | Mentor → (the assigned mentor) → Milestones | Mark it Completed | Saved; progress % on the dashboard increases |
| M11 | Startup → CareConnect → My progress | View progress | Progress bar and milestone list |

M4 → M11 walk through the **complete lifecycle**: registration → application → evaluation → admission → mentoring → progress.

---

## 6. Limitations of the testing

- **Date-dependent results.** The overdue milestones (R9) and `days_overdue` depend on the date the test is run. As time passes, more milestones become overdue. TC-46 therefore checks that the known overdue milestones are included and that every listed milestone really is past its target date, rather than checking an exact list.
- **Concurrency.** The `FOR UPDATE` lock in `admit_application()` and the optimistic `WHERE status = old_status` check in `change_status()` are explained, and the stale-status case is tested (TC-17), but two truly simultaneous users were not simulated.
- **Single-user application.** Roles are chosen from a sidebar selector, not a login (decision D5), so access control is not security-tested.
