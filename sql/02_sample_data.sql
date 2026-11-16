-- =====================================================================
-- Startup Incubation and Startup Management System
-- File: 02_sample_data.sql
-- Purpose: insert realistic sample data into all 9 tables.
-- Run AFTER 01_schema.sql:
--     psql -U postgres -d incubation_db -f sql/02_sample_data.sql
--
-- Reference date for this data set: early November 2026.
-- The data is fictional and chosen to exercise every module and report:
--   * applications in every status (Submitted, Under Review, Accepted, Rejected)
--   * a startup that re-applied after rejection (D2)
--   * an application with no evaluations yet          (report R5)
--   * an incubated startup with no mentor assigned     (report R7)
--   * a mentor with no assignments                     (LEFT JOIN demo)
--   * overdue milestones                               (report R9)
--   * Active, Graduated and Exited incubations
-- =====================================================================

\set ON_ERROR_STOP on

-- Everything below is ONE transaction: either all rows are inserted,
-- or (if any statement fails) none are.
BEGIN;

-- Empty all tables and reset the identity counters back to 1, so IDs in
-- this file are predictable (first startup inserted = startup_id 1, ...).
-- CASCADE also empties every table that references these three tables.
TRUNCATE startup, evaluator, mentor RESTART IDENTITY CASCADE;

-- ---------------------------------------------------------------------
-- 1. STARTUP  (IDs 1..10 are assigned in this order)
-- ---------------------------------------------------------------------
INSERT INTO startup (startup_name, sector, founded_date, city, email, phone, description, registered_on)
VALUES
 ('GreenLeaf Agro',     'AgriTech',   '2024-06-15', 'Pune',      'contact@greenleafagro.in',  '9822011001', 'Low-cost soil sensors and crop advisory for small farmers',  '2025-11-20'),  -- 1
 ('MediQuick Health',   'HealthTech', '2024-02-10', 'Chennai',   'hello@mediquick.in',        '9840022002', 'Teleconsultation platform for tier-2 and tier-3 towns',     '2025-12-01'),  -- 2
 ('PaySetu',            'FinTech',    '2023-11-05', 'Bengaluru', 'team@paysetu.in',           '9880033003', 'UPI-based billing tool for small merchants',                '2025-12-05'),  -- 3
 ('VidyaPath Learning', 'EdTech',     '2024-08-01', 'Hyderabad', 'info@vidyapath.in',         '9849044004', 'Regional-language exam preparation app',                    '2025-12-10'),  -- 4
 ('SolarNest Energy',   'CleanTech',  '2023-09-20', 'Jaipur',    'connect@solarnest.in',      '9829055005', 'Rooftop solar kits on monthly subscription',                '2025-12-12'),  -- 5
 ('KiranaKart',         'E-Commerce', '2024-04-18', 'Indore',    'support@kiranakart.in',     '9826066006', 'Online ordering platform for neighbourhood grocery stores', '2025-12-15'),  -- 6
 ('CloudLedger',        'SaaS',       '2022-12-01', 'Bengaluru', 'sales@cloudledger.in',      '9845077007', 'Cloud accounting software for small businesses',           '2025-04-20'),  -- 7
 ('AquaSense',          'AgriTech',   '2025-01-12', 'Nagpur',    'hello@aquasense.in',        '9823088008', 'Smart drip-irrigation controller',                          '2026-08-25'),  -- 8
 ('CareConnect',        'HealthTech', '2025-03-30', 'Kochi',     'care@careconnect.in',       '9847099009', 'Home-nursing booking service for elderly patients',        '2026-09-18'),  -- 9
 ('ByteTutor',          'EdTech',     '2025-07-07', 'New Delhi', 'admin@bytetutor.in',        '9811010010', 'Coding lessons for school students',                        '2026-10-30');  -- 10

-- ---------------------------------------------------------------------
-- 2. FOUNDER  (1 to 3 founders per startup; startup_id refers to the list above)
-- ---------------------------------------------------------------------
INSERT INTO founder (startup_id, full_name, email, phone, designation)
VALUES
 (1,  'Asha Patil',       'asha@greenleafagro.in',    '9822100101', 'CEO'),
 (1,  'Ravi Kumar',       'ravi@greenleafagro.in',    '9822100102', 'CTO'),
 (2,  'Neha Iyer',        'neha@mediquick.in',        '9840200201', 'CEO'),
 (2,  'Karthik Raman',    'karthik@mediquick.in',     '9840200202', 'Co-founder'),
 (3,  'Vikram Shah',      'vikram@paysetu.in',        '9880300301', 'CEO'),
 (3,  'Ananya Bose',      'ananya@paysetu.in',        '9880300302', 'CTO'),
 (4,  'Sneha Reddy',      'sneha@vidyapath.in',       '9849400401', 'CEO'),
 (5,  'Manish Agarwal',   'manish@solarnest.in',      '9829500501', 'CEO'),
 (5,  'Pooja Sharma',     'pooja@solarnest.in',       '9829500502', 'COO'),
 (6,  'Imran Khan',       'imran@kiranakart.in',      '9826600601', 'CEO'),
 (7,  'Deepak Menon',     'deepak@cloudledger.in',    '9845700701', 'CEO'),
 (7,  'Ritu Verma',       'ritu@cloudledger.in',      '9845700702', 'CTO'),
 (7,  'Aditya Kulkarni',  'aditya@cloudledger.in',    NULL,         'CFO'),
 (8,  'Swati Deshmukh',   'swati@aquasense.in',       '9823800801', 'CEO'),
 (8,  'Nikhil Wagh',      'nikhil@aquasense.in',      '9823800802', 'CTO'),
 (9,  'Joseph Mathew',    'joseph@careconnect.in',    '9847900901', 'CEO'),
 (10, 'Harsh Vardhan',    'harsh@bytetutor.in',       '9811001001', 'CEO'),
 (10, 'Simran Kaur',      'simran@bytetutor.in',      '9811001002', 'CTO');

-- ---------------------------------------------------------------------
-- 3. EVALUATOR  (IDs 1..5)
-- ---------------------------------------------------------------------
INSERT INTO evaluator (full_name, email, expertise_area, organization)
VALUES
 ('Dr. Anil Mehta',      'anil.mehta@agriresearch.in',  'AgriTech',   'Western Agri Research Institute'),  -- 1
 ('Lakshmi Rao',         'lakshmi.rao@deccanangels.in', 'Finance',    'Deccan Angel Network'),             -- 2
 ('Dr. Farhan Siddiqui', 'farhan.s@citymedical.in',     'HealthTech', 'City Medical College'),             -- 3
 ('Rahul Bhatia',        'rahul.bhatia@techadvise.in',  'Technology', NULL),                               -- 4
 ('Shalini Gupta',       'shalini@brandworks.in',       'Marketing',  'BrandWorks Advisory');              -- 5

-- ---------------------------------------------------------------------
-- 4. MENTOR  (IDs 1..6; mentor 6 will have NO assignments)
-- ---------------------------------------------------------------------
INSERT INTO mentor (full_name, email, expertise_area, organization, years_experience)
VALUES
 ('Rohan Desai',     'rohan.desai@mentors.in',    'Product Development', 'Independent',            14),  -- 1
 ('Dr. Priya Nair',  'priya.nair@mentors.in',     'Healthcare',          'Coastal Health Systems', 18),  -- 2
 ('Sanjay Gupta',    'sanjay.gupta@mentors.in',   'Finance',             'Sterling Capital',       20),  -- 3
 ('Meera Joshi',     'meera.joshi@mentors.in',    'Agri Supply Chain',   'FarmLink Cooperative',   11),  -- 4
 ('Arjun Malhotra',  'arjun.m@mentors.in',        'SaaS Sales',          'Northstar Software',      9),  -- 5
 ('Kavita Rao',      'kavita.rao@mentors.in',     'Marketing',           'Independent',             7);  -- 6

-- ---------------------------------------------------------------------
-- 5. APPLICATION  (IDs 1..10)
--    decision_date is filled ONLY for Accepted/Rejected (chk_application_decision)
-- ---------------------------------------------------------------------
INSERT INTO application (startup_id, submitted_on, pitch_summary, funding_requested, status, decision_date)
VALUES
 (1, '2026-01-10', 'Soil sensor kit plus SMS advisory to raise small-farm yields',      1500000.00, 'Accepted',     '2026-03-10'),  -- 1
 (2, '2026-01-12', 'Teleconsultation app connecting rural patients to city doctors',    2500000.00, 'Accepted',     '2026-03-10'),  -- 2
 (3, '2026-01-15', 'Simple UPI billing and credit tracking for kirana merchants',       4000000.00, 'Accepted',     '2026-03-11'),  -- 3
 (4, '2026-01-18', 'Regional-language mock tests for state government exams',          1200000.00, 'Rejected',     '2026-03-12'),  -- 4
 (5, '2026-01-20', 'Subscription rooftop solar for middle-income households',           3000000.00, 'Accepted',     '2026-03-12'),  -- 5
 (6, '2026-01-22', 'Marketplace app for local grocery stores',                           800000.00, 'Rejected',     '2026-03-13'),  -- 6
 (7, '2025-05-10', 'Cloud accounting with GST filing for small businesses',             2000000.00, 'Accepted',     '2025-06-15'),  -- 7
 (4, '2026-09-15', 'Revised plan: exam-prep app with adaptive practice and offline mode',1800000.00,'Under Review', NULL),          -- 8 (re-application, D2)
 (8, '2026-09-20', 'Sensor-driven drip irrigation that cuts water use by 40 percent',   3500000.00, 'Under Review', NULL),          -- 9
 (9, '2026-10-25', 'On-demand verified home nurses for elderly care',                   2200000.00, 'Submitted',    NULL);          -- 10 (no evaluations yet)

-- ---------------------------------------------------------------------
-- 6. EVALUATION  (composite PK: application_id + evaluator_id)
-- ---------------------------------------------------------------------
INSERT INTO evaluation (application_id, evaluator_id, score, feedback, evaluated_on)
VALUES
 (1, 1, 88, 'Strong field validation with farmers; hardware cost is realistic',          '2026-02-05'),
 (1, 2, 80, 'Revenue model is clear; needs a plan for working capital',                  '2026-02-07'),
 (1, 4, 84, 'Sensor firmware is solid; SMS backend should be made scalable',             '2026-02-08'),
 (2, 3, 90, 'Addresses a real access gap; doctor network already in place',              '2026-02-06'),
 (2, 2, 78, 'Unit economics depend heavily on consultation volume',                      '2026-02-09'),
 (2, 4, 82, 'App is stable; must strengthen patient data security',                      '2026-02-10'),
 (3, 2, 85, 'Large market and good merchant traction in pilot',                          '2026-02-11'),
 (3, 4, 79, 'Technically sound; competition from large payment apps is a risk',          '2026-02-12'),
 (4, 4, 55, 'Content is good but product is not differentiated',                         '2026-02-14'),
 (4, 5, 48, 'Unclear customer acquisition strategy',                                     '2026-02-15'),
 (5, 1, 76, 'Useful for semi-urban homes; installation network is thin',                 '2026-02-16'),
 (5, 2, 72, 'Subscription model needs careful default-risk management',                  '2026-02-17'),
 (5, 4, 80, 'Good IoT monitoring of panels',                                             '2026-02-18'),
 (6, 2, 45, 'Thin margins and very crowded market',                                      '2026-02-19'),
 (6, 5, 52, 'Branding is weak; retention numbers are low',                               '2026-02-20'),
 (7, 4, 91, 'Mature product with paying users already',                                  '2025-05-25'),
 (7, 2, 86, 'Healthy recurring revenue and low churn',                                   '2025-05-28'),
 (8, 5, 70, 'Much clearer go-to-market than the previous application',                   '2026-10-05'),
 (9, 1, 81, 'Promising water-saving results in pilot farms',                             '2026-10-08'),
 (9, 4, 74, 'Controller hardware needs better weather-proofing',                         '2026-10-10');

-- ---------------------------------------------------------------------
-- 7. INCUBATION  (only for Accepted applications 1, 2, 3, 5, 7; IDs 1..5)
--    actual_end_date is filled ONLY when status is not Active
-- ---------------------------------------------------------------------
INSERT INTO incubation (application_id, start_date, expected_end_date, actual_end_date, status)
VALUES
 (1, '2026-04-01', '2027-03-31', NULL,         'Active'),     -- 1  GreenLeaf Agro
 (2, '2026-04-01', '2027-03-31', NULL,         'Active'),     -- 2  MediQuick Health
 (3, '2026-04-01', '2027-03-31', '2026-09-30', 'Exited'),     -- 3  PaySetu (left early)
 (5, '2026-04-01', '2027-03-31', NULL,         'Active'),     -- 4  SolarNest Energy (no mentor yet)
 (7, '2025-07-01', '2026-06-30', '2026-06-30', 'Graduated');  -- 5  CloudLedger

-- ---------------------------------------------------------------------
-- 8. MENTORSHIP  (composite PK: incubation_id + mentor_id)
--    end_date is filled ONLY when status is Completed
-- ---------------------------------------------------------------------
INSERT INTO mentorship (incubation_id, mentor_id, assigned_on, end_date, status, remarks)
VALUES
 (1, 4, '2026-04-05', NULL,         'Active',    'Helping set up farmer cooperatives for distribution'),
 (1, 1, '2026-04-05', NULL,         'Active',    'Reviewing sensor product roadmap'),
 (2, 2, '2026-04-06', NULL,         'Active',    'Advising on clinical partnerships'),
 (2, 1, '2026-04-06', NULL,         'Active',    'Guiding app feature prioritisation'),
 (3, 3, '2026-04-10', '2026-09-30', 'Completed', 'Mentorship ended when startup exited the programme'),
 (5, 5, '2025-07-05', '2026-06-30', 'Completed', 'Built enterprise sales pipeline'),
 (5, 1, '2025-07-05', '2026-06-30', 'Completed', 'Product-market fit reviews');

-- ---------------------------------------------------------------------
-- 9. MILESTONE
--    completed_on is filled ONLY when status is Completed
-- ---------------------------------------------------------------------
INSERT INTO milestone (incubation_id, title, description, target_date, status, completed_on)
VALUES
 (1, 'Build MVP sensor kit',          'Working prototype tested in the lab',          '2026-06-30', 'Completed',   '2026-06-20'),
 (1, 'Pilot with 50 farmers',         'Field trial in two villages',                  '2026-09-30', 'Completed',   '2026-10-05'),
 (1, 'Onboard 500 farmers',           'Paid subscriptions across the district',       '2026-12-31', 'In Progress', NULL),
 (1, 'Raise seed funding',            'Close a seed round with angel investors',      '2027-03-15', 'Pending',     NULL),
 (2, 'Launch beta app',               'Public beta on Android',                       '2026-07-31', 'Completed',   '2026-07-25'),
 (2, 'Partner with 10 clinics',       'Signed agreements with local clinics',         '2026-10-15', 'In Progress', NULL),   -- overdue
 (2, 'Complete data security audit',  'External audit of patient data handling',      '2026-12-15', 'Pending',     NULL),
 (3, 'Build billing prototype',       'UPI billing app for pilot merchants',          '2026-06-30', 'Completed',   '2026-06-28'),
 (3, 'Sign 100 pilot merchants',      'Merchants actively using the app',             '2026-09-15', 'Pending',     NULL),   -- overdue (startup exited)
 (4, 'Install pilot rooftop units',   'Ten pilot installations in Jaipur',            '2026-08-31', 'Completed',   '2026-09-10'),
 (4, 'Reach 100 subscribed homes',    'Active monthly subscriptions',                 '2026-11-01', 'In Progress', NULL),   -- overdue
 (4, 'Obtain product certification',  'Safety and quality certification of the kit', '2027-01-31', 'Pending',     NULL),
 (5, 'Release version 1.0',           'Stable release with GST filing module',       '2025-10-31', 'Completed',   '2025-10-20'),
 (5, 'Reach 50 paying customers',     'Monthly paid subscriptions',                   '2026-02-28', 'Completed',   '2026-03-05'),
 (5, 'Close seed round',              'Seed investment from angel network',           '2026-06-15', 'Completed',   '2026-06-10');

COMMIT;
