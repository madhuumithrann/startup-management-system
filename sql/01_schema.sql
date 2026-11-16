-- =====================================================================
-- Startup Incubation and Startup Management System
-- File: 01_schema.sql
-- Purpose: create all 9 tables with their constraints.
-- Run with:  psql -U postgres -d incubation_db -f sql/01_schema.sql
-- Design reference: docs/02b_schema_and_normalization.md
-- =====================================================================

-- Stop at the first error instead of continuing with later statements.
\set ON_ERROR_STOP on

-- ---------------------------------------------------------------------
-- 0a. Drop views first (created in 05_views.sql). A view depends on the
--     tables it reads, so PostgreSQL will not drop those tables while
--     the view still exists.
-- ---------------------------------------------------------------------
DROP VIEW IF EXISTS vw_incubation_dashboard;
DROP VIEW IF EXISTS vw_application_summary;

-- ---------------------------------------------------------------------
-- 0b. Drop old tables (so this script can be re-run).
--    Order is the REVERSE of creation order: children before parents,
--    otherwise PostgreSQL refuses because of foreign key references.
-- ---------------------------------------------------------------------
DROP TABLE IF EXISTS milestone;
DROP TABLE IF EXISTS mentorship;
DROP TABLE IF EXISTS incubation;
DROP TABLE IF EXISTS evaluation;
DROP TABLE IF EXISTS application;
DROP TABLE IF EXISTS founder;
DROP TABLE IF EXISTS mentor;
DROP TABLE IF EXISTS evaluator;
DROP TABLE IF EXISTS startup;

-- ---------------------------------------------------------------------
-- 1. STARTUP  (Module 1)
-- ---------------------------------------------------------------------
CREATE TABLE startup (
    startup_id     INT GENERATED ALWAYS AS IDENTITY,
    startup_name   VARCHAR(100) NOT NULL,
    sector         VARCHAR(50)  NOT NULL,
    founded_date   DATE         NOT NULL,
    city           VARCHAR(50)  NOT NULL,
    email          VARCHAR(100) NOT NULL,
    phone          VARCHAR(15),
    description    TEXT,
    registered_on  DATE         NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT pk_startup         PRIMARY KEY (startup_id),
    CONSTRAINT uq_startup_name    UNIQUE (startup_name),
    CONSTRAINT uq_startup_email   UNIQUE (email),
    CONSTRAINT chk_startup_sector CHECK (sector IN ('FinTech', 'HealthTech', 'EdTech',
                                    'AgriTech', 'CleanTech', 'E-Commerce', 'SaaS', 'Other')),
    CONSTRAINT chk_startup_dates  CHECK (founded_date <= registered_on),
    CONSTRAINT chk_startup_email  CHECK (email LIKE '%_@_%._%')
);

-- ---------------------------------------------------------------------
-- 2. EVALUATOR  (Module 3)
-- ---------------------------------------------------------------------
CREATE TABLE evaluator (
    evaluator_id    INT GENERATED ALWAYS AS IDENTITY,
    full_name       VARCHAR(100) NOT NULL,
    email           VARCHAR(100) NOT NULL,
    expertise_area  VARCHAR(50)  NOT NULL,
    organization    VARCHAR(100),

    CONSTRAINT pk_evaluator        PRIMARY KEY (evaluator_id),
    CONSTRAINT uq_evaluator_email  UNIQUE (email),
    CONSTRAINT chk_evaluator_email CHECK (email LIKE '%_@_%._%')
);

-- ---------------------------------------------------------------------
-- 3. MENTOR  (Module 4)
-- ---------------------------------------------------------------------
CREATE TABLE mentor (
    mentor_id         INT GENERATED ALWAYS AS IDENTITY,
    full_name         VARCHAR(100) NOT NULL,
    email             VARCHAR(100) NOT NULL,
    expertise_area    VARCHAR(50)  NOT NULL,
    organization      VARCHAR(100),
    years_experience  INT          NOT NULL,

    CONSTRAINT pk_mentor            PRIMARY KEY (mentor_id),
    CONSTRAINT uq_mentor_email      UNIQUE (email),
    CONSTRAINT chk_mentor_email     CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT chk_mentor_experience CHECK (years_experience >= 0)
);

-- ---------------------------------------------------------------------
-- 4. FOUNDER  (Module 1)  -- child of STARTUP, 1:N
-- ---------------------------------------------------------------------
CREATE TABLE founder (
    founder_id   INT GENERATED ALWAYS AS IDENTITY,
    startup_id   INT          NOT NULL,
    full_name    VARCHAR(100) NOT NULL,
    email        VARCHAR(100) NOT NULL,
    phone        VARCHAR(15),
    designation  VARCHAR(50)  NOT NULL,

    CONSTRAINT pk_founder         PRIMARY KEY (founder_id),
    CONSTRAINT uq_founder_email   UNIQUE (email),
    CONSTRAINT chk_founder_email  CHECK (email LIKE '%_@_%._%'),
    CONSTRAINT fk_founder_startup FOREIGN KEY (startup_id)
        REFERENCES startup (startup_id) ON DELETE CASCADE
);

-- ---------------------------------------------------------------------
-- 5. APPLICATION  (Module 2)  -- child of STARTUP, 1:N
-- ---------------------------------------------------------------------
CREATE TABLE application (
    application_id     INT GENERATED ALWAYS AS IDENTITY,
    startup_id         INT           NOT NULL,
    submitted_on       DATE          NOT NULL DEFAULT CURRENT_DATE,
    pitch_summary      TEXT          NOT NULL,
    funding_requested  NUMERIC(12,2) NOT NULL,
    status             VARCHAR(20)   NOT NULL DEFAULT 'Submitted',
    decision_date      DATE,

    CONSTRAINT pk_application          PRIMARY KEY (application_id),
    CONSTRAINT fk_application_startup  FOREIGN KEY (startup_id)
        REFERENCES startup (startup_id) ON DELETE RESTRICT,
    CONSTRAINT chk_application_funding CHECK (funding_requested >= 0),
    CONSTRAINT chk_application_status  CHECK (status IN ('Submitted', 'Under Review',
                                                         'Accepted', 'Rejected')),
    -- decision_date is filled  <=>  status is Accepted or Rejected
    CONSTRAINT chk_application_decision CHECK ((status IN ('Accepted', 'Rejected'))
                                               = (decision_date IS NOT NULL)),
    CONSTRAINT chk_application_dates   CHECK (decision_date >= submitted_on)
);

-- BR-3: at most ONE open (Submitted / Under Review) application per startup.
-- A partial unique index only contains rows that satisfy the WHERE clause.
CREATE UNIQUE INDEX uq_one_open_application
    ON application (startup_id)
    WHERE status IN ('Submitted', 'Under Review');

-- ---------------------------------------------------------------------
-- 6. EVALUATION  (Module 3)  -- M:N between APPLICATION and EVALUATOR
-- ---------------------------------------------------------------------
CREATE TABLE evaluation (
    application_id  INT,
    evaluator_id    INT,
    score           INT  NOT NULL,
    feedback        TEXT NOT NULL,
    evaluated_on    DATE NOT NULL DEFAULT CURRENT_DATE,

    CONSTRAINT pk_evaluation             PRIMARY KEY (application_id, evaluator_id),
    CONSTRAINT fk_evaluation_application FOREIGN KEY (application_id)
        REFERENCES application (application_id) ON DELETE CASCADE,
    CONSTRAINT fk_evaluation_evaluator   FOREIGN KEY (evaluator_id)
        REFERENCES evaluator (evaluator_id) ON DELETE RESTRICT,
    CONSTRAINT chk_evaluation_score      CHECK (score BETWEEN 0 AND 100)
);

-- ---------------------------------------------------------------------
-- 7. INCUBATION  (Modules 4, 5)  -- 1:1 with an accepted APPLICATION
-- ---------------------------------------------------------------------
CREATE TABLE incubation (
    incubation_id      INT GENERATED ALWAYS AS IDENTITY,
    application_id     INT         NOT NULL,
    start_date         DATE        NOT NULL,
    expected_end_date  DATE        NOT NULL,
    actual_end_date    DATE,
    status             VARCHAR(20) NOT NULL DEFAULT 'Active',

    CONSTRAINT pk_incubation             PRIMARY KEY (incubation_id),
    CONSTRAINT uq_incubation_application UNIQUE (application_id),   -- makes it 1:1
    CONSTRAINT fk_incubation_application FOREIGN KEY (application_id)
        REFERENCES application (application_id) ON DELETE RESTRICT,
    CONSTRAINT chk_incubation_status     CHECK (status IN ('Active', 'Graduated', 'Exited')),
    CONSTRAINT chk_incubation_expected   CHECK (expected_end_date > start_date),
    CONSTRAINT chk_incubation_actual     CHECK (actual_end_date >= start_date),
    -- actual_end_date is filled  <=>  incubation is no longer Active
    CONSTRAINT chk_incubation_end_status CHECK ((status <> 'Active')
                                                = (actual_end_date IS NOT NULL))
);

-- ---------------------------------------------------------------------
-- 8. MENTORSHIP  (Module 4)  -- M:N between INCUBATION and MENTOR
-- ---------------------------------------------------------------------
CREATE TABLE mentorship (
    incubation_id  INT,
    mentor_id      INT,
    assigned_on    DATE        NOT NULL DEFAULT CURRENT_DATE,
    end_date       DATE,
    status         VARCHAR(20) NOT NULL DEFAULT 'Active',
    remarks        TEXT,

    CONSTRAINT pk_mentorship            PRIMARY KEY (incubation_id, mentor_id),
    CONSTRAINT fk_mentorship_incubation FOREIGN KEY (incubation_id)
        REFERENCES incubation (incubation_id) ON DELETE CASCADE,
    CONSTRAINT fk_mentorship_mentor     FOREIGN KEY (mentor_id)
        REFERENCES mentor (mentor_id) ON DELETE RESTRICT,
    CONSTRAINT chk_mentorship_status    CHECK (status IN ('Active', 'Completed')),
    CONSTRAINT chk_mentorship_dates     CHECK (end_date >= assigned_on),
    -- end_date is filled  <=>  mentorship is Completed
    CONSTRAINT chk_mentorship_end       CHECK ((status = 'Completed')
                                               = (end_date IS NOT NULL))
);

-- ---------------------------------------------------------------------
-- 9. MILESTONE  (Module 5)  -- child of INCUBATION, 1:N
-- ---------------------------------------------------------------------
CREATE TABLE milestone (
    milestone_id   INT GENERATED ALWAYS AS IDENTITY,
    incubation_id  INT          NOT NULL,
    title          VARCHAR(100) NOT NULL,
    description    TEXT,
    target_date    DATE         NOT NULL,
    status         VARCHAR(20)  NOT NULL DEFAULT 'Pending',
    completed_on   DATE,

    CONSTRAINT pk_milestone            PRIMARY KEY (milestone_id),
    CONSTRAINT uq_milestone_title      UNIQUE (incubation_id, title),
    CONSTRAINT fk_milestone_incubation FOREIGN KEY (incubation_id)
        REFERENCES incubation (incubation_id) ON DELETE CASCADE,
    CONSTRAINT chk_milestone_status    CHECK (status IN ('Pending', 'In Progress', 'Completed')),
    -- completed_on is filled  <=>  milestone is Completed
    CONSTRAINT chk_milestone_completion CHECK ((status = 'Completed')
                                               = (completed_on IS NOT NULL))
);
