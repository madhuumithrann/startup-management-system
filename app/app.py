"""
app.py - entry point of the Streamlit application.

Run from the project folder with:
    streamlit run app/app.py

It shows a sidebar "View as" selector (D5) and, for the chosen role,
the matching tabs. Each tab calls a function from one module file.
"""

import psycopg
import streamlit as st

import application_module
import db
import evaluation_module
import mentor_module
import progress_module
import startup_module

st.set_page_config(page_title="Startup Incubation System", layout="wide")
st.title("Startup Incubation and Management System")

# Stop early with a clear message if PostgreSQL is not reachable.
try:
    db.fetch_one("SELECT 1")
except psycopg.OperationalError:
    st.error("Cannot connect to PostgreSQL. Check that the postgresql-x64-18 service "
             "is running and the settings in app/db.py are correct.")
    st.stop()

# ---------------------------------------------------------------------
# Sidebar: choose a role (this is NOT a login - see docs/01_requirements.md)
# ---------------------------------------------------------------------
role = st.sidebar.radio("View as", ["Administrator", "Startup / Founder", "Evaluator", "Mentor"])

if role == "Administrator":
    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        ["Startups", "Applications", "Evaluations", "Mentors", "Progress"])
    with tab1:
        startup_module.admin_page()
    with tab2:
        application_module.admin_page()
    with tab3:
        evaluation_module.admin_page()
    with tab4:
        mentor_module.admin_page()
    with tab5:
        progress_module.admin_page()

elif role == "Startup / Founder":
    with st.sidebar:   # put the dropdown in the sidebar, under the role selector
        st.divider()
        startup_id = startup_module.choose_startup("Which startup are you?", key="role_startup")
    if startup_id:
        tab1, tab2, tab3 = st.tabs(["My startup", "My applications", "My progress"])
        with tab1:
            startup_module.startup_profile_page(startup_id)
        with tab2:
            application_module.startup_applications_page(startup_id)
        with tab3:
            progress_module.startup_progress_page(startup_id)

elif role == "Evaluator":
    with st.sidebar:
        st.divider()
        evaluator_id = evaluation_module.choose_evaluator("Which evaluator are you?", key="role_evaluator")
    if evaluator_id:
        tab1, tab2 = st.tabs(["Pending evaluations", "My evaluations"])
        with tab1:
            evaluation_module.pending_page(evaluator_id)
        with tab2:
            evaluation_module.my_evaluations_page(evaluator_id)

elif role == "Mentor":
    with st.sidebar:
        st.divider()
        mentor_id = mentor_module.choose_mentor("Which mentor are you?", key="role_mentor")
    if mentor_id:
        tab1, tab2 = st.tabs(["My startups", "Milestones"])
        with tab1:
            mentor_module.my_startups_page(mentor_id)
        with tab2:
            progress_module.mentor_milestones_page(mentor_id)
