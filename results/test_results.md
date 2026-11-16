# Automated Test Results

- Run on: 2026-11-16 22:30
- Command: `python tests/test_app.py`
- Result: **56 of 56 passed**

| ID | Module | Test case | Expected | Actual | Result |
|---|---|---|---|---|---|
| TC-01 | 1 Startup | Register startup with first founder (transaction) | startup created with 1 founder | startup_id=11, founders=1 | PASS |
| TC-02 | 1 Startup | Duplicate startup name rejected; founder not saved (rollback) | uq_startup_name, 0 founder rows | uq_startup_name, founder rows=0 | PASS |
| TC-03 | 1 Startup | Duplicate founder email rejected; startup not saved (rollback) | uq_founder_email, 0 startup rows | uq_founder_email, startup rows=0 | PASS |
| TC-04 | 1 Startup | Sector outside the allowed list rejected | chk_startup_sector | chk_startup_sector | PASS |
| TC-05 | 1 Startup | Badly formatted email rejected | chk_startup_email | chk_startup_email | PASS |
| TC-06 | 1 Startup | Search 'bengal' (ILIKE on city) | CloudLedger, PaySetu | ['CloudLedger', 'PaySetu'] | PASS |
| TC-07 | 1 Startup | Filter by sector AgriTech | AquaSense, GreenLeaf Agro | ['AquaSense', 'GreenLeaf Agro'] | PASS |
| TC-08 | 1 Startup | Update startup city | 1 row updated, city = Mumbai | rows=1, city=Mumbai | PASS |
| TC-09 | 1 Startup | Delete startup that has applications (ON DELETE RESTRICT) | fk_application_startup | fk_application_startup | PASS |
| TC-10 | 1 Startup | Delete startup without applications cascades to founders | 0 founders left | 0 | PASS |
| TC-11 | 1 Startup | Removing the last founder is refused (BR-1) | False | False | PASS |
| TC-12 | 2 Application | Submit application (status defaults to Submitted) | Submitted | Submitted | PASS |
| TC-13 | 2 Application | Second open application for the same startup rejected (BR-3) | uq_one_open_application | uq_one_open_application | PASS |
| TC-14 | 2 Application | Re-application after rejection allowed (D2) | new application created | application_id=13 | PASS |
| TC-15 | 2 Application | Status change Submitted -> Under Review | True, Under Review | True, Under Review | PASS |
| TC-16 | 2 Application | Direct change to Accepted is not allowed | ValueError | ValueError | PASS |
| TC-17 | 2 Application | Status change with stale old status updates nothing | False | False | PASS |
| TC-18 | 2 Application | Admit application with no evaluations refused (BR-7) | ValueError, still Under Review | An application needs at least one evaluation before it can be accepted. / Under Review | PASS |
| TC-19 | 2 Application | Admit with end date before start: whole transaction rolled back | chk_incubation_expected, still Under Review, 0 incubations | chk_incubation_expected, Under Review, 0 | PASS |
| TC-20 | 2 Application | Admit valid application: Accepted + incubation created (transaction) | Accepted, decision_date = today, 1 incubation | Accepted, 2026-11-16, incubation_id=7 | PASS |
| TC-21 | 2 Application | Admitting an already accepted application refused | ValueError | ValueError | PASS |
| TC-22 | 2 Application | Reject application sets decision_date | Rejected, today | Rejected, 2026-11-16 | PASS |
| TC-23 | 2 Application | Status report (GROUP BY status) adds up to all applications | sum = total rows | {'Accepted': 6, 'Rejected': 3, 'Submitted': 2, 'Under Review': 1} | PASS |
| TC-24 | 3 Evaluation | HAVING AVG(score) >= 80 | CloudLedger, GreenLeaf Agro, MediQuick Health, PaySetu | ['CloudLedger', 'GreenLeaf Agro', 'MediQuick Health', 'PaySetu'] | PASS |
| TC-25 | 3 Evaluation | Subquery: applications above the overall average | overall 74.8, 6 applications | overall 74.8, 6 applications | PASS |
| TC-26 | 3 Evaluation | Correlated subquery: top evaluation per application | 9 applications; #2 -> Dr. Farhan Siddiqui 90 | 9 applications; #2 -> ('Dr. Farhan Siddiqui', 90) | PASS |
| TC-27 | 3 Evaluation | Evaluator list (LEFT JOIN + COUNT) | 5 evaluators, Rahul Bhatia 7 | {'Dr. Anil Mehta': 3, 'Dr. Farhan Siddiqui': 1, 'Lakshmi Rao': 6, 'Rahul Bhatia': 7, 'Shalini Gupta': 3} | PASS |
| TC-28 | 3 Evaluation | Pending queue for evaluator 5 (NOT EXISTS) | [9] | [9] | PASS |
| TC-29 | 3 Evaluation | Record evaluation; queue becomes empty | True, [] | True, [] | PASS |
| TC-30 | 3 Evaluation | Second evaluation by same evaluator rejected (composite PK, BR-5) | pk_evaluation | pk_evaluation | PASS |
| TC-31 | 3 Evaluation | Score 150 rejected (CHECK, BR-6) | chk_evaluation_score | chk_evaluation_score | PASS |
| TC-32 | 3 Evaluation | Evaluation of an Accepted application refused (INSERT ... SELECT) | False | False | PASS |
| TC-33 | 3 Evaluation | Delete evaluator with evaluations (ON DELETE RESTRICT) | fk_evaluation_evaluator | fk_evaluation_evaluator | PASS |
| TC-34 | 3 Evaluation | Add then delete an evaluator with no evaluations | 1 row deleted | 1 | PASS |
| TC-35 | 4 Mentor | Mentor workload (LEFT JOIN, condition in ON) includes zeros | Rohan Desai 2, Kavita Rao 0, Sanjay Gupta 0 | {'Rohan Desai': 2, 'Dr. Priya Nair': 1, 'Meera Joshi': 1, 'Arjun Malhotra': 0, 'Kavita Rao': 0, 'Sanjay Gupta': 0} | PASS |
| TC-36 | 4 Mentor | Active incubations without an active mentor | SolarNest Energy | ['SolarNest Energy'] | PASS |
| TC-37 | 4 Mentor | Assign mentor to SolarNest; it leaves the unmentored list | True, [] | True, [] | PASS |
| TC-38 | 4 Mentor | Same mentor assigned twice rejected (composite PK) | pk_mentorship | pk_mentorship | PASS |
| TC-39 | 4 Mentor | Assign mentor to an Exited incubation refused | False | False | PASS |
| TC-40 | 4 Mentor | Mentorship for a non-existent incubation rejected (FK, D4) | fk_mentorship_incubation | fk_mentorship_incubation | PASS |
| TC-41 | 4 Mentor | End mentorship sets Completed and end_date together | True, Completed, today | True, Completed, 2026-11-16 | PASS |
| TC-42 | 4 Mentor | Delete mentor with mentorships (ON DELETE RESTRICT) | fk_mentorship_mentor | fk_mentorship_mentor | PASS |
| TC-43 | 4 Mentor | Mentor role: Rohan's startups | CloudLedger, GreenLeaf Agro, MediQuick Health (any order) | ['GreenLeaf Agro', 'MediQuick Health', 'CloudLedger'] | PASS |
| TC-44 | 5 Progress | Progress report (CASE inside SUM, percentage) | GreenLeaf 2/4 = 50.0, CloudLedger 3/3 = 100.0 | {'CloudLedger': (3, 3, '100.0'), 'GreenLeaf Agro': (2, 4, '50.0'), 'PaySetu': (1, 2, '50.0'), 'MediQuick Health': (1, 3, '33.3'), 'SolarNest Energy': (1, 3, '33.3')} | PASS |
| TC-45 | 5 Progress | Dashboard view: milestone counts not multiplied by mentors (no fan-out) | 5 incubations, GreenLeaf 4 milestones | {'GreenLeaf Agro': 4, 'MediQuick Health': 3, 'PaySetu': 2, 'SolarNest Energy': 3, 'CloudLedger': 3} | PASS |
| TC-46 | 5 Progress | Overdue milestones (date arithmetic; depends on today's date) | includes 'Partner with 10 clinics' and 'Reach 100 subscribed homes'; all past target and not completed | ['Partner with 10 clinics', 'Reach 100 subscribed homes'] | PASS |
| TC-47 | 5 Progress | Create milestone (status defaults to Pending) | True, Pending | True, Pending | PASS |
| TC-48 | 5 Progress | Duplicate milestone title in same incubation rejected | uq_milestone_title | uq_milestone_title | PASS |
| TC-49 | 5 Progress | Create milestone for an Exited incubation refused | False | False | PASS |
| TC-50 | 5 Progress | Complete a milestone, then revert it (completed_on set, then cleared) | Completed/today, then In Progress/None | Completed/2026-11-16, then In Progress/None | PASS |
| TC-51 | 5 Progress | Mentor updates a milestone of a startup they mentor | True | True | PASS |
| TC-52 | 5 Progress | Mentor cannot update another startup's milestone (EXISTS) | False, milestone unchanged | False, In Progress | PASS |
| TC-53 | 5 Progress | Completed without completion date rejected (CHECK, BR-10) | chk_milestone_completion | chk_milestone_completion | PASS |
| TC-54 | UI | Administrator: every action of all 5 modules opens | 25 screens, 0 errors | 25 screens, errors: 0 | PASS |
| TC-55 | UI | Startup, Evaluator and Mentor roles open for several users | 8 role views, 0 errors | errors: 0 | PASS |
| TC-56 | UI | Register form shows a readable error for a duplicate name | 'A startup with this name already exists.' | ['A startup with this name already exists.'] | PASS |
