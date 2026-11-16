"""
application_module.py - Module 2: Application Management

Part 1 (database functions): run SQL through db.py and return Python data.
Part 2 (screens): Streamlit forms and tables that call the Part 1 functions.

Requirements covered: FR-2.1 to FR-2.5, business rules BR-3 and BR-7, report R2.
"""

from datetime import date, timedelta

import psycopg
import streamlit as st

import db

STATUSES = ["Submitted", "Under Review", "Accepted", "Rejected"]

# Allowed manual status changes. "Accepted" is NOT here on purpose:
# accepting is only possible through admit_application() (BR-7).
NEXT_STATUSES = {
    "Submitted": ["Under Review"],
    "Under Review": ["Rejected"],
}


# =====================================================================
# PART 1: DATABASE FUNCTIONS
# =====================================================================

def get_applications(status="All"):
    """FR-2.2: all applications (from the view), optionally filtered by status."""
    sql = """SELECT application_id, startup_name, sector, submitted_on, status,
                    funding_requested, evaluation_count, avg_score, decision_date
             FROM vw_application_summary"""
    params = []
    if status != "All":
        sql += " WHERE status = %s"
        params.append(status)
    sql += " ORDER BY submitted_on DESC"
    return db.fetch_all(sql, params)


def get_applications_of_startup(startup_id):
    """FR-2.3: one startup's applications (Startup role)."""
    return db.fetch_all(
        """SELECT application_id, submitted_on, status, funding_requested,
                  evaluation_count, avg_score, decision_date
           FROM vw_application_summary
           WHERE startup_id = %s
           ORDER BY submitted_on DESC""",
        (startup_id,),
    )


def get_application(application_id):
    """One application with its startup name, or None."""
    return db.fetch_one(
        """SELECT a.*, s.startup_name
           FROM application a
           JOIN startup s ON s.startup_id = a.startup_id
           WHERE a.application_id = %s""",
        (application_id,),
    )


def get_feedback(application_id):
    """Evaluation scores and feedback for one application (shown to admin and startup)."""
    return db.fetch_all(
        """SELECT ev.full_name AS evaluator, ev.expertise_area, e.score, e.feedback, e.evaluated_on
           FROM evaluation e
           JOIN evaluator ev ON ev.evaluator_id = e.evaluator_id
           WHERE e.application_id = %s
           ORDER BY e.evaluated_on""",
        (application_id,),
    )


def submit_application(startup_id, pitch_summary, funding_requested):
    """
    FR-2.1: insert a new application (status defaults to 'Submitted').
    The partial unique index uq_one_open_application rejects it if the
    startup already has an open application (BR-3).
    """
    # INSERT ... RETURNING gives back a row, so fetch_one can run it (and commits it).
    row = db.fetch_one(
        """INSERT INTO application (startup_id, pitch_summary, funding_requested)
           VALUES (%s, %s, %s)
           RETURNING application_id""",
        (startup_id, pitch_summary, funding_requested),
    )
    return row["application_id"]


def change_status(application_id, old_status, new_status):
    """
    FR-2.4: move an application from old_status to new_status.
    'WHERE status = old_status' makes sure nobody changed it in the meantime.
    Returns True if one row was updated.
    """
    if new_status not in NEXT_STATUSES.get(old_status, []):
        raise ValueError(f"Cannot change status from {old_status} to {new_status}.")

    if new_status == "Rejected":
        sql = """UPDATE application SET status = %s, decision_date = CURRENT_DATE
                 WHERE application_id = %s AND status = %s"""
    else:
        sql = """UPDATE application SET status = %s
                 WHERE application_id = %s AND status = %s"""
    rows_changed = db.execute(sql, (new_status, application_id, old_status))
    return rows_changed == 1


def admit_application(application_id, start_date, expected_end_date):
    """
    FR-2.5 / BR-7: accept an application AND create its incubation record,
    as ONE transaction. Steps:
      1. lock the application row and read its status
      2. check it is 'Under Review'
      3. check it has at least one evaluation
      4. UPDATE application -> 'Accepted'
      5. INSERT incubation
    Any failure (a ValueError we raise, or a database error) -> ROLLBACK of all steps.
    Returns the new incubation_id.
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            # Step 1: FOR UPDATE locks this row until COMMIT/ROLLBACK,
            # so no other transaction can change it while we work.
            cur.execute(
                "SELECT status FROM application WHERE application_id = %s FOR UPDATE",
                (application_id,),
            )
            app = cur.fetchone()
            if app is None:
                raise ValueError("Application not found.")

            # Step 2
            if app["status"] != "Under Review":
                raise ValueError("Only applications that are Under Review can be accepted.")

            # Step 3
            cur.execute(
                "SELECT COUNT(*) AS total FROM evaluation WHERE application_id = %s",
                (application_id,),
            )
            if cur.fetchone()["total"] == 0:
                raise ValueError("An application needs at least one evaluation before it can be accepted.")

            # Step 4
            cur.execute(
                """UPDATE application SET status = 'Accepted', decision_date = CURRENT_DATE
                   WHERE application_id = %s""",
                (application_id,),
            )

            # Step 5
            cur.execute(
                """INSERT INTO incubation (application_id, start_date, expected_end_date)
                   VALUES (%s, %s, %s)
                   RETURNING incubation_id""",
                (application_id, start_date, expected_end_date),
            )
            incubation_id = cur.fetchone()["incubation_id"]
    # Leaving the "with" block normally -> COMMIT (steps 4 and 5 saved together).
    return incubation_id


def get_status_report():
    """Report R2 (query Q6): applications and funding requested by status."""
    return db.fetch_all(
        """SELECT status,
                  COUNT(*)                         AS applications,
                  SUM(funding_requested)           AS total_funding_requested,
                  ROUND(AVG(funding_requested), 2) AS avg_funding_requested
           FROM application
           GROUP BY status
           ORDER BY applications DESC"""
    )


# =====================================================================
# PART 2: SCREENS (Streamlit)
# =====================================================================

def choose_application(label, statuses, key):
    """Dropdown of applications whose status is in the given list. Returns application_id or None."""
    rows = db.fetch_all(
        """SELECT a.application_id, s.startup_name, a.status
           FROM application a
           JOIN startup s ON s.startup_id = a.startup_id
           WHERE a.status = ANY(%s)
           ORDER BY a.application_id""",
        (statuses,),
    )
    if not rows:
        st.info("No applications in this state.")
        return None
    labels = {r["application_id"]: f"#{r['application_id']} - {r['startup_name']} ({r['status']})"
              for r in rows}
    return st.selectbox(label, list(labels.keys()), format_func=lambda aid: labels[aid], key=key)


def show_application_details(application_id):
    """FR-2.3: pitch, status, dates and evaluator feedback of one application."""
    a = get_application(application_id)
    if a is None:
        st.warning("Application not found.")
        return
    st.subheader(f"Application #{a['application_id']} - {a['startup_name']}")
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Status:** {a['status']}")
    col2.write(f"**Submitted:** {a['submitted_on']}")
    col3.write(f"**Decision date:** {a['decision_date'] or '-'}")
    st.write(f"**Funding requested:** Rs. {a['funding_requested']:,}")
    st.write(f"**Pitch:** {a['pitch_summary']}")
    st.markdown("**Evaluations**")
    feedback = get_feedback(application_id)
    if feedback:
        st.dataframe(feedback, hide_index=True)
    else:
        st.write("No evaluations yet.")


# ---------- Admin sections ----------

def all_applications_section():
    status = st.selectbox("Filter by status", ["All"] + STATUSES)
    rows = get_applications(status)
    st.write(f"{len(rows)} application(s)")
    st.dataframe(rows, hide_index=True)
    st.divider()
    application_id = choose_application("View details of", STATUSES, key="view_app")
    if application_id:
        show_application_details(application_id)


def update_status_section():
    application_id = choose_application("Application", ["Submitted", "Under Review"], key="status_app")
    if not application_id:
        return
    a = get_application(application_id)
    st.write(f"Current status: **{a['status']}**")
    new_status = st.selectbox("New status", NEXT_STATUSES[a["status"]], key="new_status_" + str(application_id))
    st.caption("To accept an application, use 'Admit to incubation'.")
    if st.button("Update status"):
        try:
            if change_status(application_id, a["status"], new_status):
                st.success(f"Application #{application_id} is now {new_status}.")
            else:
                st.error("The application was changed by someone else. Please reload and try again.")
        except ValueError as e:
            st.error(str(e))
        except psycopg.Error as e:
            st.error(db.error_message(e))


def admit_section():
    application_id = choose_application("Application to accept", ["Under Review"], key="admit_app")
    if not application_id:
        return
    summary = db.fetch_one(
        "SELECT evaluation_count, avg_score FROM vw_application_summary WHERE application_id = %s",
        (application_id,),
    )
    st.write(f"Evaluations: **{summary['evaluation_count']}**, average score: **{summary['avg_score'] or '-'}**")

    col1, col2 = st.columns(2)
    start = col1.date_input("Incubation start date", value=date.today(), key="admit_start")
    end = col2.date_input("Expected end date", value=date.today() + timedelta(days=365), key="admit_end")

    if st.button("Accept and admit to incubation"):
        try:
            incubation_id = admit_application(application_id, start, end)
            st.success(f"Application #{application_id} accepted. Incubation #{incubation_id} created.")
        except ValueError as e:
            st.error(str(e))
        except psycopg.Error as e:
            st.error(db.error_message(e))


def status_report_section():
    rows = get_status_report()
    st.dataframe(rows, hide_index=True)
    st.bar_chart(rows, x="status", y="applications")


# ---------- Entry points called from app.py ----------

def admin_page():
    """Administrator: all application operations."""
    action = st.radio(
        "Choose an action",
        ["All applications", "Update status", "Admit to incubation", "Status report"],
        horizontal=True,
        key="app_action",
    )
    if action == "All applications":
        all_applications_section()
    elif action == "Update status":
        update_status_section()
    elif action == "Admit to incubation":
        admit_section()
    elif action == "Status report":
        status_report_section()


def startup_applications_page(startup_id):
    """Startup / Founder role: own applications, feedback, and submitting a new one."""
    rows = get_applications_of_startup(startup_id)
    st.dataframe(rows, hide_index=True)

    if rows:
        ids = [r["application_id"] for r in rows]
        application_id = st.selectbox("View details of application", ids,
                                      format_func=lambda aid: f"#{aid}", key="my_app_" + str(startup_id))
        show_application_details(application_id)

    st.divider()
    st.markdown("**Submit a new application**")
    with st.form("submit_application_" + str(startup_id)):
        pitch = st.text_area("Pitch summary *")
        funding = st.number_input("Funding requested (Rs.) *", min_value=0, step=50000, value=0)
        submitted = st.form_submit_button("Submit application")
    if submitted:
        if not pitch.strip():
            st.error("Please write a pitch summary.")
            return
        try:
            new_id = submit_application(startup_id, pitch.strip(), funding)
            st.success(f"Application #{new_id} submitted. Status: Submitted.")
        except psycopg.Error as e:
            st.error(db.error_message(e))
