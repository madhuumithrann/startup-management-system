-- =====================================================================
-- Startup Incubation and Startup Management System
-- File: 05_views.sql
-- Purpose: create the views used by the application's screens.
-- Run AFTER 01_schema.sql (and normally after 02_sample_data.sql):
--     psql -U postgres -d incubation_db -f sql/05_views.sql
-- =====================================================================

\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------
-- VIEW 1: one row per application, with startup name and evaluation stats.
-- Used by: Admin "Applications" tab, Startup "My applications" tab.
-- LEFT JOIN so that applications with no evaluations still appear.
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_application_summary AS
SELECT a.application_id,
       a.startup_id,
       s.startup_name,
       s.sector,
       a.submitted_on,
       a.status,
       a.funding_requested,
       a.decision_date,
       COUNT(e.evaluator_id)  AS evaluation_count,
       ROUND(AVG(e.score), 1) AS avg_score
FROM application a
JOIN startup s         ON s.startup_id = a.startup_id
LEFT JOIN evaluation e ON e.application_id = a.application_id
GROUP BY a.application_id, a.startup_id, s.startup_name, s.sector,
         a.submitted_on, a.status, a.funding_requested, a.decision_date;

-- ---------------------------------------------------------------------
-- VIEW 2: incubation dashboard  [R11]
-- One row per incubation: startup, active mentors, milestone progress.
-- Mentors and milestones are each computed in their OWN subquery to avoid
-- the "fan-out" problem (see explanation in the course notes).
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW vw_incubation_dashboard AS
SELECT i.incubation_id,
       s.startup_id,
       s.startup_name,
       s.sector,
       i.start_date,
       i.expected_end_date,
       i.status,
       (SELECT STRING_AGG(me.full_name, ', ' ORDER BY me.full_name)
        FROM mentorship ms
        JOIN mentor me ON me.mentor_id = ms.mentor_id
        WHERE ms.incubation_id = i.incubation_id
          AND ms.status = 'Active')                        AS active_mentors,
       (SELECT COUNT(*)
        FROM milestone m
        WHERE m.incubation_id = i.incubation_id)           AS total_milestones,
       (SELECT COUNT(*)
        FROM milestone m
        WHERE m.incubation_id = i.incubation_id
          AND m.status = 'Completed')                      AS completed_milestones
FROM incubation i
JOIN application a ON a.application_id = i.application_id
JOIN startup s     ON s.startup_id = a.startup_id;

-- ---------------------------------------------------------------------
-- Using the views: a view is queried exactly like a table.
-- ---------------------------------------------------------------------
\echo ''
\echo '=== Q20 Applications of one startup (Startup role view)   [FR-2.3]  SELECT from a VIEW'
SELECT application_id, submitted_on, status, evaluation_count, avg_score
FROM vw_application_summary
WHERE startup_id = 4
ORDER BY submitted_on;

\echo ''
\echo '=== Q21 Incubation dashboard with progress percentage   [R11]  SELECT from a VIEW'
SELECT incubation_id, startup_name, status, active_mentors,
       completed_milestones || ' / ' || total_milestones AS progress,
       ROUND(100.0 * completed_milestones / NULLIF(total_milestones, 0), 1) AS percent_complete
FROM vw_incubation_dashboard
ORDER BY incubation_id;
