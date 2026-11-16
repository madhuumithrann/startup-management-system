"""
progress_module.py - Module 5: Progress Management

Part 1 (database functions): run SQL through db.py and return Python data.
Part 2 (screens): Streamlit forms and tables that call the Part 1 functions.

Requirements covered: FR-5.1 to FR-5.5, business rule BR-10, reports R8, R9, R11.
"""

from datetime import date, timedelta

import psycopg
import streamlit as st

import db

MILESTONE_STATUSES = ["Pending", "In Progress", "Completed"]


# =====================================================================
# PART 1: DATABASE FUNCTIONS
# =====================================================================

def get_dashboard(startup_id=None):
    """Report R11 (query Q21): one row per incubation from the view, with % complete."""
    sql = """SELECT incubation_id, startup_name, sector, status, start_date, expected_end_date,
                    active_mentors, completed_milestones, total_milestones,
                    ROUND(100.0 * completed_milestones / NULLIF(total_milestones, 0), 1) AS percent_complete
             FROM vw_incubation_dashboard"""
    params = []
    if startup_id is not None:
        sql += " WHERE startup_id = %s"
        params.append(startup_id)
    sql += " ORDER BY incubation_id"
    return db.fetch_all(sql, params)


def get_incubation_choices(only_active=False):
    """Incubations with startup names, for dropdowns."""
    sql = """SELECT i.incubation_id, s.startup_name, i.status
             FROM incubation i
             JOIN application a ON a.application_id = i.application_id
             JOIN startup s     ON s.startup_id = a.startup_id"""
    if only_active:
        sql += " WHERE i.status = 'Active'"
    sql += " ORDER BY s.startup_name"
    return db.fetch_all(sql)


def get_milestones(incubation_id):
    """FR-5.4: all milestones of one incubation, earliest target first."""
    return db.fetch_all(
        """SELECT milestone_id, title, description, target_date, status, completed_on
           FROM milestone
           WHERE incubation_id = %s
           ORDER BY target_date""",
        (incubation_id,),
    )


def create_milestone(incubation_id, title, description, target_date):
    """
    FR-5.1: add a milestone to an ACTIVE incubation (INSERT ... SELECT).
    status defaults to 'Pending'. uq_milestone_title blocks duplicate titles
    within the same incubation. Returns True if created.
    """
    rows_inserted = db.execute(
        """INSERT INTO milestone (incubation_id, title, description, target_date)
           SELECT i.incubation_id, %s, %s, %s
           FROM incubation i
           WHERE i.incubation_id = %s
             AND i.status = 'Active'""",
        (title, description, target_date, incubation_id),
    )
    return rows_inserted == 1


def update_milestone_status(milestone_id, new_status, completed_on, mentor_id=None):
    """
    FR-5.2 / FR-5.3: change a milestone's status.
    completed_on is stored only when the status is Completed, otherwise NULL,
    so chk_milestone_completion is always satisfied.

    If mentor_id is given (Mentor role), the update only happens when that
    mentor has an ACTIVE mentorship for the milestone's incubation (EXISTS).
    Returns True if one row was updated.
    """
    if new_status != "Completed":
        completed_on = None

    sql = """UPDATE milestone m
             SET status = %s, completed_on = %s
             WHERE m.milestone_id = %s"""
    params = [new_status, completed_on, milestone_id]

    if mentor_id is not None:
        sql += """ AND EXISTS (SELECT 1
                               FROM mentorship ms
                               WHERE ms.incubation_id = m.incubation_id
                                 AND ms.mentor_id = %s
                                 AND ms.status = 'Active')"""
        params.append(mentor_id)

    return db.execute(sql, params) == 1


def delete_milestone(milestone_id):
    """Admin: remove a milestone (e.g. created by mistake)."""
    return db.execute("DELETE FROM milestone WHERE milestone_id = %s", (milestone_id,))


def get_progress_report():
    """Report R8 (query Q17): completed vs total milestones and % per incubation."""
    return db.fetch_all(
        """SELECT i.incubation_id, s.startup_name, i.status,
                  COUNT(m.milestone_id)                                   AS total_milestones,
                  SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END) AS completed,
                  ROUND(100.0 * SUM(CASE WHEN m.status = 'Completed' THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(m.milestone_id), 0), 1)            AS percent_complete
           FROM incubation i
           JOIN application a    ON a.application_id = i.application_id
           JOIN startup s        ON s.startup_id = a.startup_id
           LEFT JOIN milestone m ON m.incubation_id = i.incubation_id
           GROUP BY i.incubation_id, s.startup_name, i.status
           ORDER BY percent_complete DESC, s.startup_name"""
    )


def get_overdue_milestones():
    """Report R9 (query Q18): milestones past their target date, not completed, in Active incubations."""
    return db.fetch_all(
        """SELECT s.startup_name, m.title, m.target_date, m.status,
                  CURRENT_DATE - m.target_date AS days_overdue
           FROM milestone m
           JOIN incubation i  ON i.incubation_id = m.incubation_id
           JOIN application a ON a.application_id = i.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           WHERE m.status <> 'Completed'
             AND m.target_date < CURRENT_DATE
             AND i.status = 'Active'
           ORDER BY days_overdue DESC"""
    )


def get_mentor_milestones(mentor_id):
    """Mentor role: milestones of the incubations this mentor ACTIVELY mentors."""
    return db.fetch_all(
        """SELECT m.milestone_id, s.startup_name, m.title, m.target_date, m.status, m.completed_on
           FROM milestone m
           JOIN mentorship ms ON ms.incubation_id = m.incubation_id
           JOIN incubation i  ON i.incubation_id = m.incubation_id
           JOIN application a ON a.application_id = i.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           WHERE ms.mentor_id = %s
             AND ms.status = 'Active'
           ORDER BY s.startup_name, m.target_date""",
        (mentor_id,),
    )


# =====================================================================
# PART 2: SCREENS (Streamlit)
# =====================================================================

def choose_incubation(label, key, only_active=False):
    """Dropdown of incubations. Returns incubation_id or None."""
    rows = get_incubation_choices(only_active)
    if not rows:
        st.info("No incubations found.")
        return None
    labels = {r["incubation_id"]: f"#{r['incubation_id']} - {r['startup_name']} ({r['status']})" for r in rows}
    return st.selectbox(label, list(labels.keys()), format_func=lambda iid: labels[iid], key=key)


def status_update_widget(milestones, key, mentor_id=None):
    """
    Shared by the Admin and Mentor screens: pick a milestone, pick a new status,
    pick a completion date (only used for 'Completed'), then save.
    """
    if not milestones:
        return
    labels = {m["milestone_id"]: f"{m.get('startup_name', '')} {m['title']} ({m['status']})".strip()
              for m in milestones}
    milestone_id = st.selectbox("Milestone", list(labels.keys()),
                                format_func=lambda mid: labels[mid], key=key + "_ms")
    current = next(m for m in milestones if m["milestone_id"] == milestone_id)

    k = f"{key}_{milestone_id}"
    col1, col2 = st.columns(2)
    new_status = col1.selectbox("New status", MILESTONE_STATUSES,
                                index=MILESTONE_STATUSES.index(current["status"]), key=k + "_status")
    completed_on = None
    if new_status == "Completed":
        completed_on = col2.date_input("Completed on", value=current["completed_on"] or date.today(),
                                       max_value=date.today(), key=k + "_date")

    if st.button("Update milestone", key=k + "_btn"):
        try:
            if update_milestone_status(milestone_id, new_status, completed_on, mentor_id):
                st.success(f"Milestone is now {new_status}.")
            else:
                st.error("You can only update milestones of startups you actively mentor.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


# ---------- Admin sections ----------

def dashboard_section():
    rows = get_dashboard()
    st.caption("From the view vw_incubation_dashboard (mentors and milestones counted in separate subqueries).")
    st.dataframe(rows, hide_index=True)


def milestones_section():
    incubation_id = choose_incubation("Incubation", key="ms_inc")
    if not incubation_id:
        return
    milestones = get_milestones(incubation_id)
    if not milestones:
        st.info("No milestones yet for this incubation.")
        return
    st.dataframe(milestones, hide_index=True)

    st.markdown("**Update status**")
    status_update_widget(milestones, key="admin_" + str(incubation_id))

    with st.expander("Delete a milestone"):
        labels = {m["milestone_id"]: m["title"] for m in milestones}
        milestone_id = st.selectbox("Milestone to delete", list(labels.keys()),
                                    format_func=lambda mid: labels[mid], key="del_ms_" + str(incubation_id))
        if st.button("Delete milestone", key="del_ms_btn_" + str(incubation_id)):
            delete_milestone(milestone_id)
            st.success("Milestone deleted.")


def add_milestone_section():
    incubation_id = choose_incubation("Incubation (active only)", key="add_ms_inc", only_active=True)
    if not incubation_id:
        return
    with st.form("add_milestone_" + str(incubation_id)):
        title = st.text_input("Title *")
        description = st.text_area("Description")
        target = st.date_input("Target date *", value=date.today() + timedelta(days=90))
        submitted = st.form_submit_button("Add milestone")
    if submitted:
        if not title.strip():
            st.error("Please enter a title.")
            return
        try:
            if create_milestone(incubation_id, title.strip(), description.strip() or None, target):
                st.success(f"Milestone '{title.strip()}' added (status: Pending).")
            else:
                st.error("This incubation is no longer active.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def progress_report_section():
    rows = get_progress_report()
    st.caption("SUM(CASE WHEN status = 'Completed' THEN 1 ELSE 0 END) / COUNT(*) with LEFT JOIN.")
    st.dataframe(rows, hide_index=True)
    # NUMERIC values arrive as Decimal; the chart library needs plain floats.
    chart_rows = [{"startup_name": r["startup_name"], "percent_complete": float(r["percent_complete"] or 0)}
                  for r in rows]
    st.bar_chart(chart_rows, x="startup_name", y="percent_complete")


def overdue_section():
    rows = get_overdue_milestones()
    st.caption(f"Target date before today ({date.today()}), not Completed, incubation Active.")
    if rows:
        st.warning(f"{len(rows)} overdue milestone(s).")
        st.dataframe(rows, hide_index=True)
    else:
        st.success("No overdue milestones.")


# ---------- Entry points called from app.py ----------

def admin_page():
    """Administrator: milestones and progress reports."""
    action = st.radio(
        "Choose an action",
        ["Dashboard", "Milestones", "Add milestone", "Progress report", "Overdue milestones"],
        horizontal=True,
        key="progress_action",
    )
    if action == "Dashboard":
        dashboard_section()
    elif action == "Milestones":
        milestones_section()
    elif action == "Add milestone":
        add_milestone_section()
    elif action == "Progress report":
        progress_report_section()
    elif action == "Overdue milestones":
        overdue_section()


def startup_progress_page(startup_id):
    """Startup / Founder role: progress of their own incubation(s)."""
    rows = get_dashboard(startup_id)
    if not rows:
        st.info("This startup has not been admitted to incubation yet.")
        return
    for r in rows:
        st.subheader(f"Incubation #{r['incubation_id']} ({r['status']})")
        st.write(f"**Mentors:** {r['active_mentors'] or 'none assigned yet'}")
        percent = r["percent_complete"] or 0
        st.progress(float(percent) / 100,
                    text=f"{r['completed_milestones']} of {r['total_milestones']} milestones completed ({percent}%)")
        st.dataframe(get_milestones(r["incubation_id"]), hide_index=True)


def mentor_milestones_page(mentor_id):
    """Mentor role: milestones of the startups this mentor actively mentors, with status updates."""
    milestones = get_mentor_milestones(mentor_id)
    if not milestones:
        st.info("You have no active mentorships, so there are no milestones to update.")
        return
    st.dataframe(milestones, hide_index=True)
    st.markdown("**Update status**")
    status_update_widget(milestones, key="mentor_" + str(mentor_id), mentor_id=mentor_id)
