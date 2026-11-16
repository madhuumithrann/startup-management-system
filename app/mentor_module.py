"""
mentor_module.py - Module 4: Mentor Management

Part 1 (database functions): run SQL through db.py and return Python data.
Part 2 (screens): Streamlit forms and tables that call the Part 1 functions.

Requirements covered: FR-4.1 to FR-4.4, business rule BR-8 (decision D4),
reports R6 and R7.
"""

import psycopg
import streamlit as st

import db


# =====================================================================
# PART 1: DATABASE FUNCTIONS
# =====================================================================

def get_mentors():
    """FR-4.1 + R6 (query Q13): all mentors with their number of ACTIVE startups (incl. zero)."""
    return db.fetch_all(
        """SELECT me.mentor_id, me.full_name, me.email, me.expertise_area,
                  me.organization, me.years_experience,
                  COUNT(ms.incubation_id) AS active_startups
           FROM mentor me
           LEFT JOIN mentorship ms ON ms.mentor_id = me.mentor_id
                                  AND ms.status = 'Active'
           GROUP BY me.mentor_id, me.full_name, me.email, me.expertise_area,
                    me.organization, me.years_experience
           ORDER BY active_startups DESC, me.full_name"""
    )


def get_mentor(mentor_id):
    return db.fetch_one("SELECT * FROM mentor WHERE mentor_id = %s", (mentor_id,))


def add_mentor(m):
    return db.execute(
        """INSERT INTO mentor (full_name, email, expertise_area, organization, years_experience)
           VALUES (%s, %s, %s, %s, %s)""",
        (m["name"], m["email"], m["expertise"], m["organization"], m["years"]),
    )


def update_mentor(mentor_id, m):
    return db.execute(
        """UPDATE mentor
           SET full_name = %s, email = %s, expertise_area = %s,
               organization = %s, years_experience = %s
           WHERE mentor_id = %s""",
        (m["name"], m["email"], m["expertise"], m["organization"], m["years"], mentor_id),
    )


def delete_mentor(mentor_id):
    """Fails with fk_mentorship_mentor if the mentor has mentorship records (ON DELETE RESTRICT)."""
    return db.execute("DELETE FROM mentor WHERE mentor_id = %s", (mentor_id,))


def get_active_incubations():
    """Incubations that are still Active, with the startup name (for the assign dropdown)."""
    return db.fetch_all(
        """SELECT i.incubation_id, s.startup_name
           FROM incubation i
           JOIN application a ON a.application_id = i.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           WHERE i.status = 'Active'
           ORDER BY s.startup_name"""
    )


def assign_mentor(incubation_id, mentor_id, remarks):
    """
    FR-4.2 / BR-8: assign a mentor to an ACTIVE incubation.

    Mentorship references incubation (D4), so a startup that was never
    admitted cannot get a mentor at all (foreign key). INSERT ... SELECT
    additionally refuses incubations that are no longer Active.
    pk_mentorship (incubation_id, mentor_id) blocks assigning the same
    mentor to the same startup twice.
    Returns True if assigned, False if the incubation is not Active.
    """
    rows_inserted = db.execute(
        """INSERT INTO mentorship (incubation_id, mentor_id, remarks)
           SELECT i.incubation_id, %s, %s
           FROM incubation i
           WHERE i.incubation_id = %s
             AND i.status = 'Active'""",
        (mentor_id, remarks, incubation_id),
    )
    return rows_inserted == 1


def get_assignments(status="All"):
    """FR-4.3: all mentorships with startup and mentor names (3-table join through incubation)."""
    sql = """SELECT ms.incubation_id, s.startup_name, ms.mentor_id, me.full_name AS mentor,
                    ms.assigned_on, ms.end_date, ms.status, ms.remarks
             FROM mentorship ms
             JOIN mentor me     ON me.mentor_id = ms.mentor_id
             JOIN incubation i  ON i.incubation_id = ms.incubation_id
             JOIN application a ON a.application_id = i.application_id
             JOIN startup s     ON s.startup_id = a.startup_id"""
    params = []
    if status != "All":
        sql += " WHERE ms.status = %s"
        params.append(status)
    sql += " ORDER BY ms.status, s.startup_name, me.full_name"
    return db.fetch_all(sql, params)


def end_mentorship(incubation_id, mentor_id):
    """
    FR-4.4: mark an Active mentorship as Completed.
    status and end_date are set TOGETHER (chk_mentorship_end requires this).
    Returns True if one row was changed.
    """
    rows_changed = db.execute(
        """UPDATE mentorship
           SET status = 'Completed', end_date = CURRENT_DATE
           WHERE incubation_id = %s AND mentor_id = %s AND status = 'Active'""",
        (incubation_id, mentor_id),
    )
    return rows_changed == 1


def get_unmentored_incubations():
    """
    Report R7 (query Q12): Active incubations with NO Active mentor.
    The condition ms.status = 'Active' must be in ON, not in WHERE (Experiment 1).
    """
    return db.fetch_all(
        """SELECT i.incubation_id, s.startup_name, s.sector, i.start_date
           FROM incubation i
           JOIN application a      ON a.application_id = i.application_id
           JOIN startup s          ON s.startup_id = a.startup_id
           LEFT JOIN mentorship ms ON ms.incubation_id = i.incubation_id
                                  AND ms.status = 'Active'
           WHERE i.status = 'Active'
             AND ms.incubation_id IS NULL
           ORDER BY i.start_date"""
    )


def get_my_startups(mentor_id):
    """Mentor role: the startups this mentor is (or was) assigned to."""
    return db.fetch_all(
        """SELECT ms.incubation_id, s.startup_name, s.sector, i.status AS incubation_status,
                  ms.assigned_on, ms.status AS mentorship_status, ms.remarks
           FROM mentorship ms
           JOIN incubation i  ON i.incubation_id = ms.incubation_id
           JOIN application a ON a.application_id = i.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           WHERE ms.mentor_id = %s
           ORDER BY ms.status, s.startup_name""",
        (mentor_id,),
    )


def update_remarks(incubation_id, mentor_id, remarks):
    """FR-4.4: a mentor updates the remarks of their own mentorship."""
    return db.execute(
        "UPDATE mentorship SET remarks = %s WHERE incubation_id = %s AND mentor_id = %s",
        (remarks, incubation_id, mentor_id),
    )


# =====================================================================
# PART 2: SCREENS (Streamlit)
# =====================================================================

def choose_mentor(label, key):
    """Dropdown of all mentors. Returns mentor_id or None."""
    rows = db.fetch_all("SELECT mentor_id, full_name FROM mentor ORDER BY full_name")
    if not rows:
        st.info("No mentors yet.")
        return None
    names = {r["mentor_id"]: r["full_name"] for r in rows}
    return st.selectbox(label, list(names.keys()), format_func=lambda mid: names[mid], key=key)


def mentor_inputs(prefix, current=None):
    """The five mentor input boxes, reused by the add and edit forms."""
    current = current or {"full_name": "", "email": "", "expertise_area": "",
                          "organization": "", "years_experience": 0}
    return {
        "name": st.text_input("Full name *", value=current["full_name"], key=prefix + "_name"),
        "email": st.text_input("Email *", value=current["email"], key=prefix + "_email"),
        "expertise": st.text_input("Expertise area *", value=current["expertise_area"], key=prefix + "_exp"),
        "organization": st.text_input("Organization", value=current["organization"] or "", key=prefix + "_org"),
        "years": st.number_input("Years of experience *", min_value=0, step=1,
                                 value=current["years_experience"], key=prefix + "_years"),
    }


def clean_mentor(m):
    """Trim spaces; empty organization -> None. Returns None if a required field is blank."""
    name, email, expertise = m["name"].strip(), m["email"].strip(), m["expertise"].strip()
    if not name or not email or not expertise:
        return None
    return {"name": name, "email": email, "expertise": expertise,
            "organization": m["organization"].strip() or None, "years": m["years"]}


# ---------- Admin sections ----------

def mentor_list_section():
    st.caption("active_startups counts only Active mentorships (LEFT JOIN, so mentors with 0 are shown).")
    st.dataframe(get_mentors(), hide_index=True)


def add_mentor_section():
    with st.form("add_mentor"):
        m = mentor_inputs("add_me")
        submitted = st.form_submit_button("Add mentor")
    if submitted:
        m = clean_mentor(m)
        if m is None:
            st.error("Please fill in all fields marked *.")
            return
        try:
            add_mentor(m)
            st.success(f"Mentor '{m['name']}' added.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def edit_delete_mentor_section():
    mentor_id = choose_mentor("Mentor", key="edit_me")
    if not mentor_id:
        return
    current = get_mentor(mentor_id)
    k = str(mentor_id)

    with st.form("edit_mentor_" + k):
        m = mentor_inputs("edit_me_" + k, current)
        submitted = st.form_submit_button("Save changes")
    if submitted:
        m = clean_mentor(m)
        if m is None:
            st.error("Please fill in all fields marked *.")
        else:
            try:
                update_mentor(mentor_id, m)
                st.success("Mentor updated.")
            except psycopg.Error as e:
                st.error(db.error_message(e))

    st.divider()
    st.caption("A mentor with mentorship records cannot be deleted (ON DELETE RESTRICT).")
    if st.button("Delete this mentor", key="del_me_" + k):
        try:
            delete_mentor(mentor_id)
            st.success("Mentor deleted.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def assign_section():
    incubations = get_active_incubations()
    if not incubations:
        st.info("There are no active incubations to assign mentors to.")
        return
    labels = {r["incubation_id"]: f"#{r['incubation_id']} - {r['startup_name']}" for r in incubations}
    incubation_id = st.selectbox("Incubated startup", list(labels.keys()),
                                 format_func=lambda iid: labels[iid], key="assign_inc")
    mentor_id = choose_mentor("Mentor", key="assign_me")
    remarks = st.text_input("Remarks (optional)", key="assign_remarks")

    if st.button("Assign mentor"):
        try:
            if assign_mentor(incubation_id, mentor_id, remarks.strip() or None):
                st.success("Mentor assigned.")
            else:
                st.error("This incubation is no longer active.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def assignments_section():
    status = st.selectbox("Filter by status", ["All", "Active", "Completed"], key="ms_filter")
    rows = get_assignments(status)
    st.dataframe(rows, hide_index=True)

    active = [r for r in rows if r["status"] == "Active"]
    if not active:
        return
    st.divider()
    st.markdown("**End a mentorship**")
    labels = {(r["incubation_id"], r["mentor_id"]): f"{r['mentor']} -> {r['startup_name']}" for r in active}
    choice = st.selectbox("Active mentorship", list(labels.keys()),
                          format_func=lambda pair: labels[pair], key="end_ms")
    if st.button("Mark as Completed"):
        incubation_id, mentor_id = choice
        if end_mentorship(incubation_id, mentor_id):
            st.success("Mentorship marked as Completed (end date = today).")
        else:
            st.error("This mentorship is no longer active.")


def unmentored_section():
    rows = get_unmentored_incubations()
    st.caption("LEFT JOIN mentorship ON ... AND status = 'Active', then keep rows where no match was found.")
    if rows:
        st.warning(f"{len(rows)} active startup(s) have no active mentor.")
        st.dataframe(rows, hide_index=True)
    else:
        st.success("Every active startup has at least one active mentor.")


# ---------- Entry points called from app.py ----------

def admin_page():
    """Administrator: maintain mentors and mentorship assignments."""
    action = st.radio(
        "Choose an action",
        ["Mentors", "Add mentor", "Edit / delete mentor",
         "Assign mentor", "Assignments", "Startups without a mentor"],
        horizontal=True,
        key="mentor_action",
    )
    if action == "Mentors":
        mentor_list_section()
    elif action == "Add mentor":
        add_mentor_section()
    elif action == "Edit / delete mentor":
        edit_delete_mentor_section()
    elif action == "Assign mentor":
        assign_section()
    elif action == "Assignments":
        assignments_section()
    elif action == "Startups without a mentor":
        unmentored_section()


def my_startups_page(mentor_id):
    """Mentor role: own assignments, and editing the remarks of an active one."""
    rows = get_my_startups(mentor_id)
    if not rows:
        st.info("You have no mentorship assignments yet.")
        return
    st.dataframe(rows, hide_index=True)

    active = [r for r in rows if r["mentorship_status"] == "Active"]
    if not active:
        return
    st.divider()
    labels = {r["incubation_id"]: r["startup_name"] for r in active}
    incubation_id = st.selectbox("Update remarks for", list(labels.keys()),
                                 format_func=lambda iid: labels[iid], key="remarks_inc_" + str(mentor_id))
    current = next(r for r in active if r["incubation_id"] == incubation_id)
    k = f"{mentor_id}_{incubation_id}"
    with st.form("remarks_" + k):
        remarks = st.text_area("Remarks", value=current["remarks"] or "", key="remarks_" + k)
        submitted = st.form_submit_button("Save remarks")
    if submitted:
        update_remarks(incubation_id, mentor_id, remarks.strip() or None)
        st.success("Remarks saved.")
