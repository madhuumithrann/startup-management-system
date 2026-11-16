-- =====================================================================
-- Startup Incubation and Startup Management System
-- File: 04_queries.sql
-- Purpose: the important SELECT queries used by the application's
--          screens and reports (each one is linked to a requirement ID).
-- Run with:  psql -U postgres -d incubation_db -f sql/04_queries.sql
-- These queries only READ data; they change nothing.
-- =====================================================================

-- =====================================================================
-- BATCH 1: filtering, sorting, joins, aggregates, GROUP BY, HAVING
-- =====================================================================

\echo ''
\echo '=== Q1  Startups in one sector, sorted by name   [FR-1.3]  WHERE, ORDER BY'
SELECT startup_id, startup_name, city, founded_date
FROM startup
WHERE sector = 'AgriTech'
ORDER BY startup_name;

\echo ''
\echo '=== Q2  Search startups by part of the name or city   [FR-1.3]  ILIKE, OR'
SELECT startup_id, startup_name, sector, city
FROM startup
WHERE startup_name ILIKE '%care%'
   OR city ILIKE '%care%'
ORDER BY startup_name;

\echo ''
\echo '=== Q3  Full details of one startup with its founders   [FR-1.4]  INNER JOIN'
SELECT s.startup_name, s.sector, s.city, f.full_name AS founder, f.designation, f.email
FROM startup s
INNER JOIN founder f ON f.startup_id = s.startup_id
WHERE s.startup_id = 7
ORDER BY f.founder_id;

\echo ''
\echo '=== Q4  Open applications, oldest first   [FR-2.2, FR-2.3]  JOIN, IN, ORDER BY'
SELECT a.application_id, s.startup_name, a.submitted_on, a.status, a.funding_requested
FROM application a
JOIN startup s ON s.startup_id = a.startup_id
WHERE a.status IN ('Submitted', 'Under Review')
ORDER BY a.submitted_on ASC;

\echo ''
\echo '=== Q5  Number of startups in each sector   [R1]  COUNT, GROUP BY'
SELECT sector, COUNT(*) AS number_of_startups
FROM startup
GROUP BY sector
ORDER BY number_of_startups DESC, sector;

\echo ''
\echo '=== Q6  Applications and funding requested by status   [R2]  COUNT, SUM, AVG, GROUP BY'
SELECT status,
       COUNT(*)                        AS applications,
       SUM(funding_requested)          AS total_funding_requested,
       ROUND(AVG(funding_requested), 2) AS avg_funding_requested
FROM application
GROUP BY status
ORDER BY applications DESC;

\echo ''
\echo '=== Q7  Evaluation summary per application   [R3, FR-3.4]  3-table JOIN, COUNT/AVG/MIN/MAX'
SELECT a.application_id,
       s.startup_name,
       a.status,
       COUNT(e.evaluator_id)  AS evaluators,
       ROUND(AVG(e.score), 1) AS avg_score,
       MIN(e.score)           AS lowest,
       MAX(e.score)           AS highest
FROM application a
JOIN startup s    ON s.startup_id = a.startup_id
JOIN evaluation e ON e.application_id = a.application_id
GROUP BY a.application_id, s.startup_name, a.status
ORDER BY avg_score DESC;

\echo ''
\echo '=== Q8  Strong applications: average score of at least 80   [R3]  GROUP BY + HAVING'
SELECT a.application_id, s.startup_name, ROUND(AVG(e.score), 1) AS avg_score
FROM application a
JOIN startup s    ON s.startup_id = a.startup_id
JOIN evaluation e ON e.application_id = a.application_id
GROUP BY a.application_id, s.startup_name
HAVING AVG(e.score) >= 80
ORDER BY avg_score DESC;

\echo ''
\echo '=== Q9  Evaluators who have done at least 3 evaluations   [FR-3.1]  JOIN, GROUP BY, HAVING COUNT'
SELECT ev.evaluator_id, ev.full_name, ev.expertise_area,
       COUNT(*)               AS evaluations_done,
       ROUND(AVG(e.score), 1) AS avg_score_given
FROM evaluator ev
JOIN evaluation e ON e.evaluator_id = ev.evaluator_id
GROUP BY ev.evaluator_id, ev.full_name, ev.expertise_area
HAVING COUNT(*) >= 3
ORDER BY evaluations_done DESC;

-- =====================================================================
-- BATCH 2: LEFT JOIN, subqueries, correlated subqueries, NOT EXISTS, CASE
-- =====================================================================

\echo ''
\echo '=== Q10 ALL applications with their evaluation count (incl. zero)   [FR-2.2, FR-3.4]  LEFT JOIN'
SELECT a.application_id, s.startup_name, a.status,
       COUNT(e.evaluator_id)  AS evaluations,
       ROUND(AVG(e.score), 1) AS avg_score
FROM application a
JOIN startup s         ON s.startup_id = a.startup_id
LEFT JOIN evaluation e ON e.application_id = a.application_id
GROUP BY a.application_id, s.startup_name, a.status
ORDER BY a.application_id;

\echo ''
\echo '=== Q11 Applications not evaluated by anyone yet   [R5]  LEFT JOIN ... IS NULL'
SELECT a.application_id, s.startup_name, a.status, a.submitted_on
FROM application a
JOIN startup s         ON s.startup_id = a.startup_id
LEFT JOIN evaluation e ON e.application_id = a.application_id
WHERE e.application_id IS NULL
ORDER BY a.submitted_on;

\echo ''
\echo '=== Q12 Active incubations with NO active mentor   [R7, FR-4.2]  LEFT JOIN with condition in ON'
SELECT i.incubation_id, s.startup_name, s.sector, i.start_date
FROM incubation i
JOIN application a      ON a.application_id = i.application_id
JOIN startup s          ON s.startup_id = a.startup_id
LEFT JOIN mentorship ms ON ms.incubation_id = i.incubation_id
                       AND ms.status = 'Active'
WHERE i.status = 'Active'
  AND ms.incubation_id IS NULL;

\echo ''
\echo '=== Q13 Mentor workload: active startups per mentor (incl. zero)   [R6, FR-4.3]  LEFT JOIN + COUNT'
SELECT me.mentor_id, me.full_name, me.expertise_area,
       COUNT(ms.incubation_id) AS active_startups
FROM mentor me
LEFT JOIN mentorship ms ON ms.mentor_id = me.mentor_id
                       AND ms.status = 'Active'
GROUP BY me.mentor_id, me.full_name, me.expertise_area
ORDER BY active_startups DESC, me.full_name;

\echo ''
\echo '=== Q14 Applications scoring above the overall average score   [R4]  subquery in HAVING'
SELECT a.application_id, s.startup_name, a.status, ROUND(AVG(e.score), 1) AS avg_score
FROM application a
JOIN startup s    ON s.startup_id = a.startup_id
JOIN evaluation e ON e.application_id = a.application_id
GROUP BY a.application_id, s.startup_name, a.status
HAVING AVG(e.score) > (SELECT AVG(score) FROM evaluation)
ORDER BY avg_score DESC;

\echo ''
\echo '=== Q15 Highest-scoring evaluation of each application   [R10]  CORRELATED subquery'
SELECT e1.application_id, s.startup_name, ev.full_name AS top_evaluator, e1.score AS top_score
FROM evaluation e1
JOIN application a ON a.application_id = e1.application_id
JOIN startup s     ON s.startup_id = a.startup_id
JOIN evaluator ev  ON ev.evaluator_id = e1.evaluator_id
WHERE e1.score = (SELECT MAX(e2.score)
                  FROM evaluation e2
                  WHERE e2.application_id = e1.application_id)
ORDER BY e1.application_id;

\echo ''
\echo '=== Q16 Evaluator view: Under Review applications evaluator 5 has NOT scored yet   [FR-3.2, D5]  NOT EXISTS'
SELECT a.application_id, s.startup_name, a.submitted_on, a.funding_requested
FROM application a
JOIN startup s ON s.startup_id = a.startup_id
WHERE a.status = 'Under Review'
  AND NOT EXISTS (SELECT 1
                  FROM evaluation e
                  WHERE e.application_id = a.application_id
                    AND e.evaluator_id = 5)
ORDER BY a.submitted_on;

\echo ''
\echo '=== Q17 Progress of each incubated startup   [R8, FR-5.4]  CASE inside SUM, percentage'
SELECT i.incubation_id, s.startup_name, i.status,
       COUNT(m.milestone_id)                                    AS total_milestones,
       SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END)  AS completed,
       ROUND(100.0 * SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END)
             / NULLIF(COUNT(m.milestone_id), 0), 1)             AS percent_complete
FROM incubation i
JOIN application a     ON a.application_id = i.application_id
JOIN startup s         ON s.startup_id = a.startup_id
LEFT JOIN milestone m  ON m.incubation_id = i.incubation_id
GROUP BY i.incubation_id, s.startup_name, i.status
ORDER BY percent_complete DESC, s.startup_name;

\echo ''
\echo '=== Q18 Overdue milestones of active incubations   [R9, FR-5.5]  date arithmetic, 4-table JOIN'
SELECT s.startup_name, m.title, m.target_date, m.status,
       CURRENT_DATE - m.target_date AS days_overdue
FROM milestone m
JOIN incubation i  ON i.incubation_id = m.incubation_id
JOIN application a ON a.application_id = i.application_id
JOIN startup s     ON s.startup_id = a.startup_id
WHERE m.status <> 'Completed'
  AND m.target_date < CURRENT_DATE
  AND i.status = 'Active'
ORDER BY days_overdue DESC;

\echo ''
\echo '=== Q19 Startups that have never been accepted   [FR-1.3]  subquery with NOT IN'
SELECT startup_id, startup_name, sector
FROM startup
WHERE startup_id NOT IN (SELECT startup_id
                         FROM application
                         WHERE status = 'Accepted')
ORDER BY startup_name;
