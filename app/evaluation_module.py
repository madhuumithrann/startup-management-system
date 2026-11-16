"""
evaluation_module.py - Module 3: Evaluation Management

Part 1 (database functions): run SQL through db.py and return Python data.
Part 2 (screens): Streamlit forms and tables that call the Part 1 functions.

Requirements covered: FR-3.1 to FR-3.4, business rules BR-5 and BR-6,
reports R3, R4 and R10.
"""

import psycopg
import streamlit as st

import db


# =====================================================================
# PART 1: DATABASE FUNCTIONS
# =====================================================================

def get_evaluators():
    """FR-3.1: all evaluators with how many evaluations each has done (incl. zero)."""
    return db.fetch_all(
        """SELECT ev.evaluator_id, ev.full_name, ev.email, ev.expertise_area, ev.organization,
                  COUNT(e.application_id) AS evaluations_done
           FROM evaluator ev
           LEFT JOIN evaluation e ON e.evaluator_id = ev.evaluator_id
           GROUP BY ev.evaluator_id, ev.full_name, ev.email, ev.expertise_area, ev.organization
           ORDER BY ev.full_name"""
    )


def get_evaluator(evaluator_id):
    return db.fetch_one("SELECT * FROM evaluator WHERE evaluator_id = %s", (evaluator_id,))


def add_evaluator(ev):
    return db.execute(
        """INSERT INTO evaluator (full_name, email, expertise_area, organization)
           VALUES (%s, %s, %s, %s)""",
        (ev["name"], ev["email"], ev["expertise"], ev["organization"]),
    )


def update_evaluator(evaluator_id, ev):
    return db.execute(
        """UPDATE evaluator
           SET full_name = %s, email = %s, expertise_area = %s, organization = %s
           WHERE evaluator_id = %s""",
        (ev["name"], ev["email"], ev["expertise"], ev["organization"], evaluator_id),
    )


def delete_evaluator(evaluator_id):
    """Fails with fk_evaluation_evaluator if the evaluator has evaluations (ON DELETE RESTRICT)."""
    return db.execute("DELETE FROM evaluator WHERE evaluator_id = %s", (evaluator_id,))


def get_pending_for_evaluator(evaluator_id):
    """
    Query Q16 (D5 Evaluator view): applications Under Review that THIS
    evaluator has NOT evaluated yet. NOT EXISTS = correlated subquery.
    """
    return db.fetch_all(
        """SELECT a.application_id, s.startup_name, s.sector, a.submitted_on, a.funding_requested
           FROM application a
           JOIN startup s ON s.startup_id = a.startup_id
           WHERE a.status = 'Under Review'
             AND NOT EXISTS (SELECT 1
                             FROM evaluation e
                             WHERE e.application_id = a.application_id
                               AND e.evaluator_id = %s)
           ORDER BY a.submitted_on""",
        (evaluator_id,),
    )


def record_evaluation(application_id, evaluator_id, score, feedback):
    """
    FR-3.2 / FR-3.3: save a score and feedback.

    INSERT ... SELECT inserts the row ONLY IF the application is still
    'Under Review' (the SELECT returns 0 rows otherwise -> nothing inserted).
    The database also checks:
      chk_evaluation_score (0..100) and pk_evaluation (one per evaluator per application).
    Returns True if saved, False if the application is not Under Review.
    """
    rows_inserted = db.execute(
        """INSERT INTO evaluation (application_id, evaluator_id, score, feedback)
           SELECT a.application_id, %s, %s, %s
           FROM application a
           WHERE a.application_id = %s
             AND a.status = 'Under Review'""",
        (evaluator_id, score, feedback, application_id),
    )
    return rows_inserted == 1


def get_my_evaluations(evaluator_id):
    """Evaluations already done by one evaluator."""
    return db.fetch_all(
        """SELECT e.application_id, s.startup_name, a.status AS application_status,
                  e.score, e.feedback, e.evaluated_on
           FROM evaluation e
           JOIN application a ON a.application_id = e.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           WHERE e.evaluator_id = %s
           ORDER BY e.evaluated_on DESC""",
        (evaluator_id,),
    )


# ---------- Result reports ----------

def get_evaluation_summary():
    """Report R3 (query Q7): count / average / lowest / highest score per application."""
    return db.fetch_all(
        """SELECT a.application_id, s.startup_name, a.status,
                  COUNT(e.evaluator_id)  AS evaluators,
                  ROUND(AVG(e.score), 1) AS avg_score,
                  MIN(e.score)           AS lowest,
                  MAX(e.score)           AS highest
           FROM application a
           JOIN startup s    ON s.startup_id = a.startup_id
           JOIN evaluation e ON e.application_id = a.application_id
           GROUP BY a.application_id, s.startup_name, a.status
           ORDER BY avg_score DESC"""
    )


def get_strong_applications(min_average):
    """Query Q8: applications whose AVERAGE score is at least min_average (HAVING)."""
    return db.fetch_all(
        """SELECT a.application_id, s.startup_name, a.status, ROUND(AVG(e.score), 1) AS avg_score
           FROM application a
           JOIN startup s    ON s.startup_id = a.startup_id
           JOIN evaluation e ON e.application_id = a.application_id
           GROUP BY a.application_id, s.startup_name, a.status
           HAVING AVG(e.score) >= %s
           ORDER BY avg_score DESC""",
        (min_average,),
    )


def get_above_overall_average():
    """Report R4 (query Q14): applications above the average of ALL scores (subquery)."""
    overall = db.fetch_one("SELECT ROUND(AVG(score), 1) AS overall FROM evaluation")["overall"]
    rows = db.fetch_all(
        """SELECT a.application_id, s.startup_name, a.status, ROUND(AVG(e.score), 1) AS avg_score
           FROM application a
           JOIN startup s    ON s.startup_id = a.startup_id
           JOIN evaluation e ON e.application_id = a.application_id
           GROUP BY a.application_id, s.startup_name, a.status
           HAVING AVG(e.score) > (SELECT AVG(score) FROM evaluation)
           ORDER BY avg_score DESC"""
    )
    return overall, rows


def get_top_evaluation_per_application():
    """Report R10 (query Q15): highest-scoring evaluation of each application (correlated subquery)."""
    return db.fetch_all(
        """SELECT e1.application_id, s.startup_name, ev.full_name AS top_evaluator,
                  e1.score AS top_score
           FROM evaluation e1
           JOIN application a ON a.application_id = e1.application_id
           JOIN startup s     ON s.startup_id = a.startup_id
           JOIN evaluator ev  ON ev.evaluator_id = e1.evaluator_id
           WHERE e1.score = (SELECT MAX(e2.score)
                             FROM evaluation e2
                             WHERE e2.application_id = e1.application_id)
           ORDER BY e1.application_id"""
    )


# =====================================================================
# PART 2: SCREENS (Streamlit)
# =====================================================================

def choose_evaluator(label, key):
    """Dropdown of all evaluators. Returns evaluator_id or None."""
    rows = db.fetch_all("SELECT evaluator_id, full_name FROM evaluator ORDER BY full_name")
    if not rows:
        st.info("No evaluators yet.")
        return None
    names = {r["evaluator_id"]: r["full_name"] for r in rows}
    return st.selectbox(label, list(names.keys()), format_func=lambda eid: names[eid], key=key)


def evaluator_inputs(prefix, current=None):
    """The four evaluator input boxes, reused by the add and edit forms."""
    current = current or {"full_name": "", "email": "", "expertise_area": "", "organization": ""}
    return {
        "name": st.text_input("Full name *", value=current["full_name"], key=prefix + "_name"),
        "email": st.text_input("Email *", value=current["email"], key=prefix + "_email"),
        "expertise": st.text_input("Expertise area *", value=current["expertise_area"], key=prefix + "_exp"),
        "organization": st.text_input("Organization", value=current["organization"] or "", key=prefix + "_org"),
    }


def clean_evaluator(ev):
    """Trim spaces; empty organization -> None (NULL). Returns None if a required field is blank."""
    name, email, expertise = ev["name"].strip(), ev["email"].strip(), ev["expertise"].strip()
    if not name or not email or not expertise:
        return None
    return {"name": name, "email": email, "expertise": expertise,
            "organization": ev["organization"].strip() or None}


# ---------- Admin sections ----------

def evaluator_list_section():
    st.dataframe(get_evaluators(), hide_index=True)


def add_evaluator_section():
    with st.form("add_evaluator"):
        ev = evaluator_inputs("add_ev")
        submitted = st.form_submit_button("Add evaluator")
    if submitted:
        ev = clean_evaluator(ev)
        if ev is None:
            st.error("Please fill in all fields marked *.")
            return
        try:
            add_evaluator(ev)
            st.success(f"Evaluator '{ev['name']}' added.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def edit_delete_evaluator_section():
    evaluator_id = choose_evaluator("Evaluator", key="edit_ev")
    if not evaluator_id:
        return
    current = get_evaluator(evaluator_id)
    k = str(evaluator_id)

    with st.form("edit_evaluator_" + k):
        ev = evaluator_inputs("edit_ev_" + k, current)
        submitted = st.form_submit_button("Save changes")
    if submitted:
        ev = clean_evaluator(ev)
        if ev is None:
            st.error("Please fill in all fields marked *.")
        else:
            try:
                update_evaluator(evaluator_id, ev)
                st.success("Evaluator updated.")
            except psycopg.Error as e:
                st.error(db.error_message(e))

    st.divider()
    st.caption("An evaluator who has recorded evaluations cannot be deleted (ON DELETE RESTRICT).")
    if st.button("Delete this evaluator", key="del_ev_" + k):
        try:
            delete_evaluator(evaluator_id)
            st.success("Evaluator deleted.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def results_section():
    report = st.selectbox(
        "Report",
        ["Summary per application",
         "Strong applications (minimum average)",
         "Above the overall average",
         "Top evaluation of each application"],
        key="eval_report",
    )
    if report == "Summary per application":
        st.caption("COUNT, AVG, MIN, MAX with GROUP BY (applications with no evaluations are not shown).")
        st.dataframe(get_evaluation_summary(), hide_index=True)

    elif report == "Strong applications (minimum average)":
        min_avg = st.slider("Minimum average score", 0, 100, 80, key="min_avg")
        st.caption("GROUP BY ... HAVING AVG(score) >= the chosen value.")
        st.dataframe(get_strong_applications(min_avg), hide_index=True)

    elif report == "Above the overall average":
        overall, rows = get_above_overall_average()
        st.caption(f"Subquery: overall average of all scores = {overall}")
        st.dataframe(rows, hide_index=True)

    elif report == "Top evaluation of each application":
        st.caption("Correlated subquery: MAX(score) computed separately for each application.")
        st.dataframe(get_top_evaluation_per_application(), hide_index=True)


# ---------- Entry points called from app.py ----------

def admin_page():
    """Administrator: maintain evaluators and view evaluation results."""
    action = st.radio(
        "Choose an action",
        ["Evaluators", "Add evaluator", "Edit / delete evaluator", "Results"],
        horizontal=True,
        key="eval_action",
    )
    if action == "Evaluators":
        evaluator_list_section()
    elif action == "Add evaluator":
        add_evaluator_section()
    elif action == "Edit / delete evaluator":
        edit_delete_evaluator_section()
    elif action == "Results":
        results_section()


def pending_page(evaluator_id):
    """Evaluator role: applications waiting for this evaluator, and the scoring form."""
    pending = get_pending_for_evaluator(evaluator_id)
    if not pending:
        st.success("Nothing pending - you have evaluated every application that is Under Review.")
        return
    st.dataframe(pending, hide_index=True)

    labels = {p["application_id"]: f"#{p['application_id']} - {p['startup_name']}" for p in pending}
    application_id = st.selectbox("Application to evaluate", list(labels.keys()),
                                  format_func=lambda aid: labels[aid], key="pending_app_" + str(evaluator_id))
    a = db.fetch_one("SELECT pitch_summary, funding_requested FROM application WHERE application_id = %s",
                     (application_id,))
    st.write(f"**Pitch:** {a['pitch_summary']}")
    st.write(f"**Funding requested:** Rs. {a['funding_requested']:,}")

    k = f"{evaluator_id}_{application_id}"
    with st.form("evaluate_" + k):
        score = st.slider("Score (0-100) *", 0, 100, 50, key="score_" + k)
        feedback = st.text_area("Feedback *", key="feedback_" + k)
        submitted = st.form_submit_button("Submit evaluation")
    if submitted:
        if not feedback.strip():
            st.error("Please write some feedback.")
            return
        try:
            if record_evaluation(application_id, evaluator_id, score, feedback.strip()):
                st.success(f"Evaluation for application #{application_id} saved.")
            else:
                st.error("This application is no longer Under Review, so it cannot be evaluated.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def my_evaluations_page(evaluator_id):
    """Evaluator role: evaluations this evaluator has already submitted."""
    rows = get_my_evaluations(evaluator_id)
    st.write(f"{len(rows)} evaluation(s) submitted")
    st.dataframe(rows, hide_index=True)
