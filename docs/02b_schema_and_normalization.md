# Phase 2B — Relational Schema, Functional Dependencies, Normalization and Constraints
## Startup Incubation and Startup Management System

*Builds on: [02a_entities_and_er.md](02a_entities_and_er.md) · Next: Phase 3 (SQL implementation)*

---

## 1. Relational schema

Notation: **PK** is shown in bold, FK is shown as `→ table(column)`, *UQ* = UNIQUE.

```
STARTUP     (**startup_id**, startup_name UQ, sector, founded_date, city, email UQ,
             phone, description, registered_on)

FOUNDER     (**founder_id**, startup_id → STARTUP, full_name, email UQ, phone, designation)

APPLICATION (**application_id**, startup_id → STARTUP, submitted_on, pitch_summary,
             funding_requested, status, decision_date)

EVALUATOR   (**evaluator_id**, full_name, email UQ, expertise_area, organization)

EVALUATION  (**application_id** → APPLICATION, **evaluator_id** → EVALUATOR,
             score, feedback, evaluated_on)

INCUBATION  (**incubation_id**, application_id → APPLICATION  UQ, start_date,
             expected_end_date, actual_end_date, status)

MENTOR      (**mentor_id**, full_name, email UQ, expertise_area, organization, years_experience)

MENTORSHIP  (**incubation_id** → INCUBATION, **mentor_id** → MENTOR,
             assigned_on, end_date, status, remarks)

MILESTONE   (**milestone_id**, incubation_id → INCUBATION, title, description,
             target_date, status, completed_on)      UQ(incubation_id, title)
```

### How each ER element was mapped

| ER element | Mapping rule | Result |
|---|---|---|
| Strong entity | Becomes a table; its key becomes the PK | Startup, Founder, Application, Evaluator, Mentor, Incubation, Milestone |
| 1:N relationship | The PK of the "1" side is added as an FK on the "N" side | founder.startup_id, application.startup_id, milestone.incubation_id |
| 1:1 relationship | FK on the side with **total** participation, plus UNIQUE | incubation.application_id (every incubation has an application, but not vice versa) |
| M:N relationship | New table; PK = both FKs combined; relationship attributes go here | Evaluation, Mentorship |

**Why does the 1:N FK go on the "N" side?** One startup has many founders. Putting `founder_ids` in Startup would need a list in a single cell, which violates 1NF. Putting `startup_id` in Founder needs only one value per row.

### Table creation order

A table can only be created after the tables it references exist:

```
1. startup   2. evaluator   3. mentor          (no FKs)
4. founder   5. application                    (→ startup)
6. evaluation                                  (→ application, evaluator)
7. incubation                                  (→ application)
8. mentorship  9. milestone                    (→ incubation, mentor)
```

Dropping tables must happen in **reverse** order. Otherwise PostgreSQL refuses, because other tables still reference the one being dropped.

---

## 2. Functional dependencies (FDs)

**Definition.** X → Y means: *if two rows agree on X, they must agree on Y.* In other words, X uniquely determines Y.

FDs come from **real-world meaning**, not from looking at sample data. For example, "an application has exactly one status at a time" gives application_id → status.

| Relation | Functional dependencies | Candidate keys |
|---|---|---|
| STARTUP | startup_id → all other attributes<br>startup_name → all other attributes<br>email → all other attributes | {startup_id}, {startup_name}, {email} |
| FOUNDER | founder_id → startup_id, full_name, email, phone, designation<br>email → founder_id, startup_id, full_name, phone, designation | {founder_id}, {email} |
| APPLICATION | application_id → startup_id, submitted_on, pitch_summary, funding_requested, status, decision_date | {application_id} |
| EVALUATOR | evaluator_id → full_name, email, expertise_area, organization<br>email → evaluator_id, … | {evaluator_id}, {email} |
| EVALUATION | {application_id, evaluator_id} → score, feedback, evaluated_on | {application_id, evaluator_id} |
| INCUBATION | incubation_id → application_id, start_date, expected_end_date, actual_end_date, status<br>application_id → incubation_id, … | {incubation_id}, {application_id} |
| MENTOR | mentor_id → full_name, email, expertise_area, organization, years_experience<br>email → mentor_id, … | {mentor_id}, {email} |
| MENTORSHIP | {incubation_id, mentor_id} → assigned_on, end_date, status, remarks | {incubation_id, mentor_id} |
| MILESTONE | milestone_id → incubation_id, title, description, target_date, status, completed_on<br>{incubation_id, title} → milestone_id, … | {milestone_id}, {incubation_id, title} |

**Dependencies that do NOT hold** (just as important to know):
- startup_id ↛ application_id: a startup can have many applications (D2).
- application_id ↛ score: one application gets different scores from different evaluators.
- evaluator_id ↛ score: one evaluator gives different scores to different applications.
- sector ↛ city, city ↛ sector: many startups share a sector or a city.

---

## 3. Normalization, demonstrated step by step

To *demonstrate* normalization rather than just claim it, we start from the kind of single spreadsheet an incubation centre might actually keep, then normalize it until we reach our schema.

### 3.0 Unnormalized form (UNF): the "evaluation spreadsheet"

| app_id | startup_name | sector | city | founders | status | evaluations |
|---|---|---|---|---|---|---|
| 101 | GreenLeaf | AgriTech | Pune | Asha Patil, Ravi Kumar | Under Review | (E1, Dr. Mehta, AgriTech, 78), (E2, Ms. Rao, Finance, 85) |
| 102 | MediQuick | HealthTech | Chennai | Neha Iyer | Under Review | (E1, Dr. Mehta, AgriTech, 62) |

**Problem:** the `founders` and `evaluations` cells hold *lists*. SQL cannot reliably search, count or constrain the values inside a list.

### 3.1 First Normal Form (1NF)

> **1NF rule:** every attribute value is **atomic** (a single value), with no repeating groups or lists.

Fixes:
1. `founders` is a multi-valued attribute of the *startup*, so it moves to its own relation **FOUNDER(founder_id, startup_id, full_name, …)**, one row per founder.
2. The `evaluations` repeating group is flattened into one row per (application, evaluator).

The resulting 1NF relation:

**EVAL_SHEET**(<u>app_id</u>, <u>evaluator_id</u>, startup_id, startup_name, sector, city, status, evaluator_name, expertise_area, score)

| app_id | evaluator_id | startup_id | startup_name | sector | city | status | evaluator_name | expertise_area | score |
|---|---|---|---|---|---|---|---|---|---|
| 101 | E1 | S1 | GreenLeaf | AgriTech | Pune | Under Review | Dr. Mehta | AgriTech | 78 |
| 101 | E2 | S1 | GreenLeaf | AgriTech | Pune | Under Review | Ms. Rao | Finance | 85 |
| 102 | E1 | S2 | MediQuick | HealthTech | Chennai | Under Review | Dr. Mehta | AgriTech | 62 |

Key: **{app_id, evaluator_id}**. FDs in this relation:

```
FD1: {app_id, evaluator_id} → score                         (full dependency)
FD2: app_id        → startup_id, status                      (PARTIAL: depends on part of the key)
FD3: evaluator_id  → evaluator_name, expertise_area          (PARTIAL)
FD4: startup_id    → startup_name, sector, city              (TRANSITIVE, via app_id)
```

This is in 1NF but still has **anomalies**:
- **Update anomaly:** changing application 101's status to "Accepted" means updating **2 rows**. Miss one and the data contradicts itself. Likewise, Dr. Mehta's name is stored twice.
- **Insertion anomaly:** we cannot record a new evaluator who hasn't scored anything yet, because `app_id` is part of the PK and a PK can't be NULL (**entity integrity**).
- **Deletion anomaly:** deleting the only evaluation of application 102 also erases the fact that MediQuick exists and is based in Chennai.

### 3.2 Second Normal Form (2NF)

> **2NF rule:** in 1NF, **and** no non-prime attribute depends on only *part* of a candidate key (no partial dependencies).
> (Non-prime attribute = an attribute that is not part of any candidate key.)

FD2 and FD3 are partial dependencies. We split each one out, using the determining part of the key as the new relation's key:

```
EVALUATION (app_id, evaluator_id, score)                         ← FD1
EVALUATOR  (evaluator_id, evaluator_name, expertise_area)        ← FD3
APP_INFO   (app_id, startup_id, startup_name, sector, city, status)  ← FD2 + FD4
```

The partial dependencies are gone. The status is now stored once per application, and an evaluator can exist without any evaluations.

**But APP_INFO still has a problem:** FD4 holds inside it as a chain, `app_id → startup_id → startup_name, sector, city`.

| app_id | startup_id | startup_name | sector | city | status |
|---|---|---|---|---|---|
| 101 | S1 | GreenLeaf | AgriTech | Pune | Rejected |
| 107 | S1 | GreenLeaf | AgriTech | Pune | Under Review |

When GreenLeaf reapplies (D2), its name, sector and city are **repeated**. Renaming the startup means updating several rows, so the update anomaly is back.

### 3.3 Third Normal Form (3NF)

> **3NF rule:** in 2NF, **and** no non-prime attribute depends transitively on a key through another non-prime attribute.
> Formal test: for **every** non-trivial FD X → A, either **X is a superkey** or **A is a prime attribute**.

In APP_INFO, FD4 is `startup_id → startup_name, sector, city`. Here `startup_id` is **not** a superkey of APP_INFO (it doesn't identify a row; S1 appears twice), and `startup_name` is not prime. So FD4 violates 3NF. We split it out:

```
STARTUP     (startup_id, startup_name, sector, city)
APPLICATION (app_id, startup_id → STARTUP, status)
```

Now each startup's details are stored exactly once, however many times it applies.

**The same reasoning explains why INCUBATION has no `startup_id`** (noted in 2A). If it did, we would have `incubation_id → application_id → startup_id`, a transitive dependency. The startup is always reachable with a join through APPLICATION.

### 3.4 Are the decompositions safe?

- **Lossless join:** each split shares a common attribute that is a **key of one of the pieces** (evaluator_id is the key of EVALUATOR; startup_id is the key of STARTUP). By the standard lossless-join test, joining the pieces back gives exactly the original rows, with no extra (spurious) rows.
- **Dependency preserving:** each of FD1–FD4 lies entirely inside one of the final relations, so it can still be enforced without joining tables.

### 3.5 Final check: every relation in our schema

Using the formal 3NF test (for every non-trivial X → A, X is a superkey or A is prime):

| Relation | Determinants (left sides of the FDs in §2) | Are all of them superkeys? | 3NF? |
|---|---|---|---|
| STARTUP | startup_id, startup_name, email | Yes, all are candidate keys | ✔ |
| FOUNDER | founder_id, email | Yes | ✔ |
| APPLICATION | application_id | Yes | ✔ |
| EVALUATOR | evaluator_id, email | Yes | ✔ |
| EVALUATION | {application_id, evaluator_id} | Yes. Neither part alone determines anything, so there's **no partial dependency** | ✔ |
| INCUBATION | incubation_id, application_id | Yes, both are candidate keys | ✔ |
| MENTOR | mentor_id, email | Yes | ✔ |
| MENTORSHIP | {incubation_id, mentor_id} | Yes, no partial dependency | ✔ |
| MILESTONE | milestone_id, {incubation_id, title} | Yes | ✔ |

In every relation, **every determinant is a superkey**. That is actually the definition of **BCNF**, which is stricter than 3NF. So our schema is in BCNF, and therefore also in 3NF.

### 3.6 Values we deliberately do NOT store

These could be computed, so storing them would create redundancy that could go stale:

| Not stored | Computed instead with |
|---|---|
| Average score of an application | `AVG(score)` over EVALUATION |
| Number of founders of a startup | `COUNT(*)` over FOUNDER |
| Progress % of an incubation | `COUNT` of completed milestones ÷ total milestones |
| "Is this startup incubated?" | Does a joined INCUBATION row exist? |

**A known controlled overlap:** `application.status = 'Accepted'` and "an INCUBATION row exists for this application" express related facts. This isn't an FD violation (they are different relations with different meanings), but they must agree. We keep them consistent with a **transaction** (§5).

---

## 4. Final constraints

Constraints are given **names** (e.g., `chk_evaluation_score`). When one is violated, PostgreSQL's error message includes that name, so the Streamlit app can show a clear message such as "Score must be between 0 and 100."

### 4.1 Constraint list

| Table | Constraint | Type | Integrity kind |
|---|---|---|---|
| All tables | Primary keys | PRIMARY KEY (implies NOT NULL + UNIQUE) | Entity |
| startup | startup_name, email unique | UNIQUE | Entity (candidate keys) |
| startup | sector IN (FinTech, HealthTech, EdTech, AgriTech, CleanTech, E-Commerce, SaaS, Other) | CHECK | Domain |
| startup | founded_date ≤ registered_on (a startup can't be founded after it registered; this also rules out future founding dates, since registered_on defaults to today) | CHECK | Domain |
| startup / founder / evaluator / mentor | email LIKE '%_@_%._%' (basic format) | CHECK | Domain |
| startup | registered_on DEFAULT CURRENT_DATE | DEFAULT | — |
| founder | email unique | UNIQUE | Entity |
| application | funding_requested ≥ 0 | CHECK | Domain |
| application | status IN (Submitted, Under Review, Accepted, Rejected), DEFAULT 'Submitted' | CHECK + DEFAULT | Domain |
| application | decision_date IS NOT NULL **iff** status IN (Accepted, Rejected) | CHECK | Domain (cross-column) |
| application | decision_date ≥ submitted_on | CHECK | Domain |
| evaluation | score BETWEEN 0 AND 100 | CHECK | Domain |
| incubation | application_id unique | UNIQUE | Makes the relationship 1:1 |
| incubation | expected_end_date > start_date; actual_end_date ≥ start_date | CHECK | Domain |
| incubation | status IN (Active, Graduated, Exited); actual_end_date set **iff** status ≠ Active | CHECK | Domain |
| mentor | years_experience ≥ 0 | CHECK | Domain |
| mentorship | status IN (Active, Completed); end_date set **iff** Completed; end_date ≥ assigned_on | CHECK | Domain |
| milestone | (incubation_id, title) unique | UNIQUE | Entity (candidate key) |
| milestone | status IN (Pending, In Progress, Completed); completed_on set **iff** Completed | CHECK | Domain |
| All FKs | See §4.2 | FOREIGN KEY | Referential |

**How an "iff" CHECK is written.** For example:
`CHECK ((status = 'Completed') = (completed_on IS NOT NULL))`
Both sides of the outer `=` are booleans (true/false), and the check passes only when they are **equal**. So "Completed with a date" passes, "Pending with no date" passes, while "Completed with no date" and "Pending with a date" both fail.

### 4.2 Foreign keys and what happens on DELETE (BR-9)

| Foreign key | ON DELETE | Why |
|---|---|---|
| founder.startup_id → startup | **CASCADE** | Founders have no meaning without their startup. Deleting a startup deletes its founders. |
| application.startup_id → startup | **RESTRICT** | Protects history: a startup that has ever applied cannot be deleted. |
| evaluation.application_id → application | **CASCADE** | An evaluation is meaningless without its application. |
| evaluation.evaluator_id → evaluator | **RESTRICT** | You can't delete an evaluator whose scores are on record. |
| incubation.application_id → application | **RESTRICT** | You can't delete an application that led to an incubation. |
| mentorship.incubation_id → incubation | **CASCADE** | An assignment has no meaning without the incubation. |
| mentorship.mentor_id → mentor | **RESTRICT** | You can't delete a mentor who has assignments. Mark the mentorship Completed instead. |
| milestone.incubation_id → incubation | **CASCADE** | Existence dependency (see 2A). |

**Combined effect:** deleting a startup succeeds only if it has never applied. In that case its founders are removed with it. Otherwise PostgreSQL raises a foreign-key violation and the app shows "This startup has application history and cannot be deleted."

**Why no ON UPDATE rules?** Our PKs are surrogate IDs that never change, so there is nothing to cascade.

**RESTRICT vs NO ACTION** (the default): both block the delete. RESTRICT checks immediately; NO ACTION checks at the end of the statement and can be deferred. For us they behave the same, and RESTRICT states the intent explicitly.

---

## 5. Rules that a CHECK constraint cannot enforce

A CHECK can only see **the columns of the row being inserted or updated**. It cannot look at other rows or other tables. These rules need other tools:

| Rule | Why CHECK can't do it | Our solution |
|---|---|---|
| **BR-3** Only one open application per startup | It needs to look at *other rows* of the same startup | A **partial unique index**:<br>`CREATE UNIQUE INDEX uq_one_open_application ON application(startup_id) WHERE status IN ('Submitted','Under Review');`<br>This makes startup_id unique **among open applications only**. Closed (Accepted/Rejected) ones aren't included in the index, so reapplying after a rejection works. |
| **BR-7** Accept only if at least 1 evaluation exists, and create the incubation at the same time | It needs to look at another table (EVALUATION) and make two changes together | A **transaction** in Python: (1) `SELECT COUNT(*)` of evaluations, (2) `UPDATE application SET status='Accepted', decision_date=…`, (3) `INSERT INTO incubation …`, (4) `COMMIT`. If any step fails, `ROLLBACK`, so it's all or nothing (Atomicity). |
| **BR-1** A startup must have ≥ 1 founder | "At least one row in another table" can't be expressed as a row check | A **transaction**: the registration form requires a first founder; INSERT startup + INSERT founder, then COMMIT together. |
| An evaluation is allowed only while the application is Under Review | Needs the application's status, which is in another table | **Application logic:** the Evaluator view lists only Under Review applications. |

**Alternative (for the viva):** PostgreSQL **triggers** could enforce BR-1 and BR-7 inside the database. We chose transactions in Python because they're easier to read and explain, and they demonstrate ACID directly. A trigger would be stronger, since it can't be bypassed by someone running SQL directly.

---

## 6. Summary

- 9 relations, mapped from the ER diagram with the standard mapping rules.
- The FDs of every relation are listed. Every determinant is a superkey, so the schema is in **BCNF**, and therefore in 3NF.
- Normalization was demonstrated from a realistic spreadsheet (UNF → 1NF → 2NF → 3NF), with concrete update, insertion and deletion anomalies at each stage.
- Integrity is enforced by the database through PKs, UNIQUE, NOT NULL, CHECK and FKs with deliberate ON DELETE choices. The remaining rules are handled by a partial unique index and two transactions.
