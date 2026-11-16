"""
db.py - the ONLY file that talks to PostgreSQL directly.

Every module file calls these functions to run its SQL:
    fetch_all(sql, params)   -> list of rows   (SELECT returning many rows)
    fetch_one(sql, params)   -> one row / None (SELECT returning one row)
    execute(sql, params)     -> rows affected  (INSERT / UPDATE / DELETE)
    get_connection()         -> a connection   (for multi-statement transactions)
    error_message(error)     -> readable text for a database error
"""

import os
from pathlib import Path

import psycopg
from psycopg.rows import dict_row


def load_env_file():
    """Read KEY=value lines from the project's .env file into os.environ.

    The password lives in .env (which git ignores), never in the code.
    A value that is already set in the environment is not overwritten.
    """
    env_file = Path(__file__).resolve().parent.parent / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_env_file()

# Connection settings for our local PostgreSQL server.
# (Kept in one place so they are easy to change; values come from .env.)
DB_SETTINGS = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "port": int(os.environ.get("DB_PORT", "5432")),
    "dbname": os.environ.get("DB_NAME", "incubation_db"),
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", ""),
}


def get_connection():
    """Open a new connection. Rows will come back as dictionaries."""
    return psycopg.connect(**DB_SETTINGS, row_factory=dict_row)


def fetch_all(sql, params=None):
    """Run a SELECT and return all rows as a list of dictionaries."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()


def fetch_one(sql, params=None):
    """Run a SELECT and return the first row (a dictionary), or None."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()


def execute(sql, params=None):
    """Run one INSERT / UPDATE / DELETE, commit it, return rows affected."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.rowcount


# Readable messages for our named constraints (see sql/01_schema.sql).
CONSTRAINT_MESSAGES = {
    "uq_startup_name": "A startup with this name already exists.",
    "uq_startup_email": "A startup with this email already exists.",
    "uq_founder_email": "A founder with this email already exists.",
    "uq_evaluator_email": "An evaluator with this email already exists.",
    "uq_mentor_email": "A mentor with this email already exists.",
    "chk_startup_email": "Please enter a valid email address.",
    "chk_founder_email": "Please enter a valid email address.",
    "chk_evaluator_email": "Please enter a valid email address.",
    "chk_mentor_email": "Please enter a valid email address.",
    "chk_startup_dates": "Founded date cannot be after the registration date.",
    "fk_application_startup": "This startup has applications, so it cannot be deleted.",
    "fk_evaluation_evaluator": "This evaluator has recorded evaluations, so they cannot be deleted.",
    "fk_mentorship_mentor": "This mentor has mentorship records, so they cannot be deleted.",
    "fk_incubation_application": "This application led to an incubation, so it cannot be deleted.",
    "uq_one_open_application": "This startup already has an open application (Submitted or Under Review).",
    "pk_evaluation": "This evaluator has already evaluated this application.",
    "chk_evaluation_score": "Score must be between 0 and 100.",
    "uq_incubation_application": "This application has already been admitted to incubation.",
    "pk_mentorship": "This mentor is already assigned to this startup.",
    "uq_milestone_title": "This startup already has a milestone with this title.",
    "chk_milestone_completion": "A completed milestone needs a completion date (and only then).",
    "chk_incubation_expected": "Expected end date must be after the start date.",
}


def error_message(error):
    """Turn a psycopg database error into a message for the user."""
    name = error.diag.constraint_name          # e.g. 'chk_evaluation_score', or None
    if name in CONSTRAINT_MESSAGES:
        return CONSTRAINT_MESSAGES[name]
    return "Database error: " + str(error.diag.message_primary)


# ---------------------------------------------------------------------
# Self-test: runs only when this file is executed directly
#     python app/db.py
# (not when another file does "import db")
# ---------------------------------------------------------------------
if __name__ == "__main__":
    print("1) Connecting and counting startups...")
    row = fetch_one("SELECT COUNT(*) AS total FROM startup")
    print("   Startups in database:", row["total"])

    print("2) Fetching AgriTech startups with a parameter...")
    rows = fetch_all(
        "SELECT startup_id, startup_name, city FROM startup WHERE sector = %s ORDER BY startup_name",
        ("AgriTech",),
    )
    for r in rows:
        print("  ", r)

    print("3) Trying an invalid insert (score 150) to test error handling...")
    try:
        execute(
            "INSERT INTO evaluation (application_id, evaluator_id, score, feedback) VALUES (%s, %s, %s, %s)",
            (10, 1, 150, "test"),
        )
    except psycopg.Error as e:
        print("   Caught error ->", error_message(e))

    print("Done.")
