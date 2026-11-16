-- =====================================================================
-- Startup Incubation and Startup Management System
-- File: 03_constraint_tests.sql
-- Purpose: prove that every constraint works, and demonstrate
--          INSERT / UPDATE / DELETE (including ON DELETE CASCADE / RESTRICT).
-- Run AFTER 01_schema.sql and 02_sample_data.sql:
--     psql -U postgres -d incubation_db -f sql/03_constraint_tests.sql
--
-- Everything runs inside ONE transaction that is ROLLED BACK at the end,
-- so the sample data is left exactly as it was.
-- =====================================================================

-- If a statement fails inside the transaction, undo only THAT statement
-- (psql creates an automatic savepoint before each statement) and continue.
-- Without this, the first error would abort the whole transaction.
\set ON_ERROR_ROLLBACK on

BEGIN;

\echo ''
\echo '================ PART A: INVALID operations (each must FAIL) ================'

\echo ''
\echo '--- T1  NOT NULL: startup without a city'
INSERT INTO startup (startup_name, sector, founded_date, city, email)
VALUES ('NoCity Labs', 'SaaS', '2025-01-01', NULL, 'hi@nocity.in');

\echo ''
\echo '--- T2  UNIQUE: startup name that already exists (PaySetu)'
INSERT INTO startup (startup_name, sector, founded_date, city, email)
VALUES ('PaySetu', 'FinTech', '2025-01-01', 'Mumbai', 'other@paysetu2.in');

\echo ''
\echo '--- T3  CHECK (domain): sector not in the allowed list'
INSERT INTO startup (startup_name, sector, founded_date, city, email)
VALUES ('CoinVerse', 'Crypto', '2025-01-01', 'Mumbai', 'hi@coinverse.in');

\echo ''
\echo '--- T4  CHECK: badly formatted email (no @)'
INSERT INTO startup (startup_name, sector, founded_date, city, email)
VALUES ('BadMail Co', 'SaaS', '2025-01-01', 'Mumbai', 'badmail.in');

\echo ''
\echo '--- T5  CHECK: founded AFTER registering'
INSERT INTO startup (startup_name, sector, founded_date, city, email, registered_on)
VALUES ('Future Corp', 'SaaS', '2026-12-01', 'Mumbai', 'hi@futurecorp.in', '2026-11-01');

\echo ''
\echo '--- T6  IDENTITY ALWAYS: supplying our own startup_id'
INSERT INTO startup (startup_id, startup_name, sector, founded_date, city, email)
VALUES (500, 'Manual Id Ltd', 'SaaS', '2025-01-01', 'Mumbai', 'hi@manualid.in');

\echo ''
\echo '--- T7  FOREIGN KEY: founder for a startup that does not exist (999)'
INSERT INTO founder (startup_id, full_name, email, designation)
VALUES (999, 'Ghost Founder', 'ghost@nowhere.in', 'CEO');

\echo ''
\echo '--- T8  CHECK: evaluation score above 100'
INSERT INTO evaluation (application_id, evaluator_id, score, feedback)
VALUES (10, 1, 150, 'Excellent');

\echo ''
\echo '--- T9  COMPOSITE PRIMARY KEY: evaluator 1 scores application 1 a second time'
INSERT INTO evaluation (application_id, evaluator_id, score, feedback)
VALUES (1, 1, 70, 'Second opinion from the same evaluator');

\echo ''
\echo '--- T10 PARTIAL UNIQUE INDEX: second OPEN application for AquaSense (startup 8)'
INSERT INTO application (startup_id, pitch_summary, funding_requested)
VALUES (8, 'Another irrigation idea', 500000);

\echo ''
\echo '--- T11 CHECK (iff): reject application 10 without a decision_date'
UPDATE application SET status = 'Rejected' WHERE application_id = 10;

\echo ''
\echo '--- T12 UNIQUE (1:1): a second incubation for application 1'
INSERT INTO incubation (application_id, start_date, expected_end_date)
VALUES (1, '2026-11-01', '2027-10-31');

\echo ''
\echo '--- T13 CHECK (iff): mark a milestone Completed without completed_on'
UPDATE milestone SET status = 'Completed' WHERE milestone_id = 3;

\echo ''
\echo '--- T14 ON DELETE RESTRICT: delete a startup that has applications (VidyaPath, 4)'
DELETE FROM startup WHERE startup_id = 4;

\echo ''
\echo '--- T15 ON DELETE RESTRICT: delete an evaluator who has evaluations (1)'
DELETE FROM evaluator WHERE evaluator_id = 1;


\echo ''
\echo '================ PART B: VALID operations (each must SUCCEED) ================'

\echo ''
\echo '--- V1  INSERT a new startup and its founder'
INSERT INTO startup (startup_name, sector, founded_date, city, email)
VALUES ('TestCo Robotics', 'Other', '2025-05-05', 'Surat', 'hi@testco.in');

INSERT INTO founder (startup_id, full_name, email, designation)
VALUES ((SELECT startup_id FROM startup WHERE startup_name = 'TestCo Robotics'),
        'Test Founder', 'founder@testco.in', 'CEO');

SELECT s.startup_id, s.startup_name, s.registered_on, f.full_name
FROM startup s JOIN founder f ON f.startup_id = s.startup_id
WHERE s.startup_name = 'TestCo Robotics';

\echo ''
\echo '--- V2  DELETE with ON DELETE CASCADE: deleting TestCo also deletes its founder'
DELETE FROM startup WHERE startup_name = 'TestCo Robotics';
SELECT COUNT(*) AS testco_founders_left FROM founder WHERE email = 'founder@testco.in';

\echo ''
\echo '--- V3  Re-application after rejection is allowed (KiranaKart, startup 6)'
INSERT INTO application (startup_id, pitch_summary, funding_requested)
VALUES (6, 'Pivot: B2B supply app for grocery stores', 900000);
SELECT application_id, startup_id, status, submitted_on
FROM application WHERE startup_id = 6 ORDER BY application_id;

\echo ''
\echo '--- V4  UPDATE: move application 10 to Under Review'
UPDATE application SET status = 'Under Review' WHERE application_id = 10;
SELECT application_id, status FROM application WHERE application_id = 10;

\echo ''
\echo '--- V5  UPDATE: complete a milestone correctly (status + date together)'
UPDATE milestone SET status = 'Completed', completed_on = '2026-11-05' WHERE milestone_id = 3;
SELECT milestone_id, title, status, completed_on FROM milestone WHERE milestone_id = 3;

\echo ''
\echo '--- V6  Two-level CASCADE: deleting incubation 3 removes its mentorships and milestones'
SELECT (SELECT COUNT(*) FROM mentorship WHERE incubation_id = 3) AS mentorships_before,
       (SELECT COUNT(*) FROM milestone  WHERE incubation_id = 3) AS milestones_before;
DELETE FROM incubation WHERE incubation_id = 3;
SELECT (SELECT COUNT(*) FROM mentorship WHERE incubation_id = 3) AS mentorships_after,
       (SELECT COUNT(*) FROM milestone  WHERE incubation_id = 3) AS milestones_after;


\echo ''
\echo '================ Undo all changes made by this test file ================'
ROLLBACK;

SELECT (SELECT COUNT(*) FROM startup)     AS startups,
       (SELECT COUNT(*) FROM application) AS applications,
       (SELECT COUNT(*) FROM incubation)  AS incubations,
       (SELECT COUNT(*) FROM milestone)   AS milestones;
