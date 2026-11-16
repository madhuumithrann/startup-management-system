# Phase 1 — Requirements Document
## Startup Incubation and Startup Management System

*DBS Course Project · Status: CONFIRMED (decisions D1–D5 finalised 2026-11-06)*

---

## 1. How this document maps to the professor's instructions

| PDF section | Covered here |
|---|---|
| §2 Choose a real-world problem | §2 Problem statement |
| §3 Identify functional modules | §6 Functional modules and requirements |
| §4 Problem, need, objectives, users | §2, §3, §4, §5 |
| §13 Reports / outputs | §7 Reports |
| §16 "Design must support the functional requirements" | §8 Business rules (these become our constraints in Phase 2) |

Everything later (ER diagram, schema, SQL, app) must trace back to a requirement in this document. If a table or query does not support a requirement listed here, it should not exist.

---

## 2. Problem statement

A startup incubation centre accepts early-stage startups into a support programme. To run it, the centre has to:

1. keep records of startups and their founders,
2. receive incubation applications,
3. have expert evaluators score those applications,
4. admit the best startups into incubation,
5. assign mentors to admitted startups, and
6. track each admitted startup's progress through milestones.

Many small incubation centres do this with spreadsheets, email threads and paper forms. The data is scattered, duplicated and easy to make inconsistent. Some typical failures:

- A startup's details are typed again in several sheets. When one copy changes, the others become wrong (an **update anomaly**).
- Nothing stops a mentor being "assigned" to a startup that was never admitted.
- A score of 150 out of 100, or an evaluation for an application that doesn't exist, can be entered without any error.
- Questions like "What is the average score of each applicant?" or "Which mentor has the most startups?" need manual counting.

## 3. Why the application is required

A relational database with an application in front of it solves these problems:

- **Single source of truth:** each fact is stored once (normalization).
- **Integrity enforced by the database itself:** PRIMARY KEY, FOREIGN KEY, NOT NULL, UNIQUE and CHECK constraints reject invalid data, even if the UI has a bug.
- **Instant reporting:** SQL joins, aggregates and subqueries answer management questions in milliseconds.
- **Consistent multi-step operations:** transactions make sure that admitting a startup either completes fully or not at all.

## 4. Objectives

1. Design a normalized (3NF) relational database for the incubation process.
2. Enforce data integrity with appropriate database constraints.
3. Provide a working Streamlit interface that lets the user perform INSERT, UPDATE, DELETE and SELECT operations on every module.
4. Implement the application lifecycle: submission → evaluation → decision → incubation.
5. Support mentor assignment and milestone-based progress tracking for incubated startups.
6. Generate meaningful reports using joins, aggregates, GROUP BY/HAVING, subqueries and views.
7. Demonstrate a transaction for a multi-step operation (admitting a startup).

## 5. Users of the system

| User | What their view (tab set) lets them do |
|---|---|
| **Administrator** (incubation centre manager) | Everything: register startups and founders; manage evaluators and mentors; change application status; admit startups; assign mentors; create milestones; view all reports |
| **Startup / Founder** | Pick their startup → view and update its details, submit an application, track application status, read evaluation feedback, view milestones and progress |
| **Evaluator** | Pick their own name → see applications Under Review that they have not yet evaluated, record a score and feedback, view their past evaluations |
| **Mentor** | Pick their own name → see the startups they mentor, update milestone status for those startups, add mentorship remarks |

**How roles work (D5):** A sidebar selector, "View as: Administrator / Startup / Evaluator / Mentor", shows a different set of tabs for each role. For non-admin roles the user then picks *which* startup, evaluator or mentor they are from a dropdown, and the queries in those tabs are filtered by that ID (e.g., `WHERE evaluator_id = %s`).

**This is not authentication.** There are no passwords, and anyone can pick any role. It is a **UI organisation** feature that shows how different users see different slices of the same database. Real login and security are out of scope (§9).

---

## 6. Functional modules and requirements

Each requirement has an ID (FR-x.y) so we can trace it to tables, SQL queries and test cases later.

### Module 1 — Startup Management
| ID | Requirement |
|---|---|
| FR-1.1 | Register a new startup (name, sector, founding date, contact details, etc.) |
| FR-1.2 | Add one or more founders to a startup |
| FR-1.3 | View the list of registered startups, with search/filter by name or sector |
| FR-1.4 | View the full details of one startup, including its founders |
| FR-1.5 | Update startup and founder information |
| FR-1.6 | Delete a startup *only where appropriate* (see BR-9) |

### Module 2 — Application Management
| ID | Requirement |
|---|---|
| FR-2.1 | Submit an incubation application for a registered startup |
| FR-2.2 | View all submitted applications, with filter by status |
| FR-2.3 | Track the status of a given application |
| FR-2.4 | Update application status (Submitted → Under Review → Accepted / Rejected) |
| FR-2.5 | On acceptance, admit the startup into incubation (start date, expected end date) as a single transaction |

### Module 3 — Evaluation Management
| ID | Requirement |
|---|---|
| FR-3.1 | Add, view and update evaluators (name, expertise area, contact) |
| FR-3.2 | Record an evaluation score for an application by an evaluator |
| FR-3.3 | Store written feedback with each evaluation |
| FR-3.4 | View evaluation results per application (each score, average, highest, lowest) |

### Module 4 — Mentor Management
| ID | Requirement |
|---|---|
| FR-4.1 | Add, view and update mentors (name, expertise area, contact) |
| FR-4.2 | Assign a mentor to an **admitted (incubated)** startup |
| FR-4.3 | View mentor assignments, both by mentor and by startup |
| FR-4.4 | Maintain mentorship records (assignment date, end date, status / remarks) |

### Module 5 — Progress Management
| ID | Requirement |
|---|---|
| FR-5.1 | Create milestones for an incubated startup (title, description, target date) |
| FR-5.2 | Update milestone status (Pending → In Progress → Completed) |
| FR-5.3 | Record the completion date when a milestone is completed |
| FR-5.4 | View the progress of a startup (milestones completed vs. total, percentage) |
| FR-5.5 | Identify overdue milestones (target date passed, not completed) |

---

## 7. Reports and outputs (PDF §13)

These are the concrete outputs the application will show. Each one also exercises a specific SQL concept, which is how we will reach the 15–20 meaningful queries.

| # | Report | SQL concept it demonstrates |
|---|---|---|
| R1 | Startups per sector | COUNT, GROUP BY |
| R2 | Application count by status | COUNT, GROUP BY |
| R3 | Evaluation summary per application (avg / min / max score, no. of evaluators) | AVG, MIN, MAX, multi-table JOIN |
| R4 | Applications scoring above the overall average | Subquery |
| R5 | Applications that have not yet been evaluated | LEFT JOIN … IS NULL / NOT EXISTS |
| R6 | Mentor workload (active startups per mentor) | JOIN, GROUP BY, HAVING |
| R7 | Incubated startups with no mentor assigned | LEFT JOIN |
| R8 | Progress per startup (% milestones completed) | SUM/COUNT, CASE, GROUP BY |
| R9 | Overdue milestones | WHERE with date comparison, ORDER BY |
| R10 | Each startup's highest-scoring evaluation | Correlated subquery |
| R11 | Incubation dashboard: startup + founders + mentors + progress | VIEW over several joins |

The exact SQL, with full clause-by-clause explanations, comes in Phases 3–4.

---

## 8. Business rules (draft)

Business rules are the real-world rules the data must obey. They matter in a DBMS project because in Phase 2 **each rule becomes a constraint, a relationship cardinality or a transaction**. These are drafts to confirm in Section 10.

| ID | Rule | Likely enforcement (decided in Phase 2) |
|---|---|---|
| BR-1 | A startup has **one or more** founders. In this system a founder belongs to exactly one startup. | FK from Founder → Startup (1:N) |
| BR-2 | Startup names and contact emails are unique. | UNIQUE |
| BR-3 | A startup may submit several applications over time (e.g., reapply after rejection), but only one may be open (Submitted / Under Review) at a time. | App-level check, or a partial unique index |
| BR-4 | Application status is one of: Submitted, Under Review, Accepted, Rejected. | CHECK |
| BR-5 | An application can be evaluated by many evaluators, but **each evaluator evaluates a given application at most once**. | Composite UNIQUE (application, evaluator) |
| BR-6 | An evaluation score is a whole number from 0 to 100. | CHECK |
| BR-7 | An application can be Accepted only if it has at least one evaluation. Accepting it creates an incubation record, and both steps must succeed or fail together. | Application check + **transaction** |
| BR-8 | Mentors can be assigned **only to incubated startups**. A mentor can guide many startups, and a startup can have many mentors. | M:N via Mentorship, FK → Incubation |
| BR-9 | A startup that has applications or incubation history must not be silently deleted, because that history is valuable. Deleting a startup with no applications is allowed, and its founders are deleted with it. | ON DELETE RESTRICT / CASCADE choices |
| BR-10 | Milestones belong to an incubated startup. Status is Pending, In Progress or Completed. A completion date must exist **if and only if** the status is Completed. | FK + CHECK |
| BR-11 | Dates must be logical: expected end date > start date, mentorship end ≥ start, and so on. | CHECK |

---

## 9. Scope boundaries

**In scope:** the five modules above, the reports in §7, the constraints implied by §8, a single-operator Streamlit UI, a locally hosted PostgreSQL database, and realistic sample data (roughly 8–12 startups, 5 evaluators, 5 mentors).

**Out of scope (deliberately excluded):**
- Login / authentication / role-based access
- Payments, funding rounds, investor portals, equity tracking
- Notifications, email, chat
- AI recommendations or scoring automation
- Multiple incubation centres
- Resource / office-space allocation
- File uploads (pitch decks, documents)
- Cloud deployment, Docker

**Non-functional requirements:**
- Runs locally on one Windows machine (Python + PostgreSQL + Streamlit).
- Integrity is enforced **in the database**, not only in the UI.
- All SQL is written by hand (no ORM) and uses parameterized queries to prevent SQL injection.
- The code stays simple enough for the team to explain any line during the viva.

## 10. Confirmed decisions

| # | Question | Decision |
|---|---|---|
| D1 | Can one founder belong to more than one startup? | **No.** Founder is a 1:N child of Startup |
| D2 | Can a startup reapply after rejection? | **Yes**, but only one open application at a time |
| D3 | Score format? | **One overall score (0–100)** plus written feedback |
| D4 | Do milestones and mentorships attach to the incubation (admitted startup)? | **Yes** |
| D5 | Login? | **No login**, but **separate tab sets per role** (Admin / Startup / Evaluator / Mentor) chosen from a sidebar selector (see §5) |
