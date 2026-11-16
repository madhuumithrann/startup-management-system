"""
tests/test_app.py - automated tests for the whole application.

Run from the project folder (with .venv activated):
    python tests/test_app.py

What it does:
  1. Reloads the sample data before each group of tests, so every group
     starts from the same known state.
  2. Calls the module functions (the same ones the screens call) and
     checks the results and the database state.
  3. Opens every screen of every role with Streamlit's test tool to check
     that nothing crashes.
  4. Prints a summary and writes results/test_results.md.
  5. Reloads the sample data again at the end (database left clean).
"""

import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT / "app"))   # so "import db" finds app/db.py

import psycopg                                      # noqa: E402
from streamlit.testing.v1 import AppTest            # noqa: E402

import application_module as am                    # noqa: E402
import db                                          # noqa: E402
import evaluation_module as em                     # noqa: E402
import mentor_module as mm                         # noqa: E402
import progress_module as pm                       # noqa: E402
import startup_module as sm                        # noqa: E402

TODAY = date.today()
results = []   # one dictionary per test case


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def check(module, description, expected, actual, passed):
    """Record one test case result."""
    tc_id = f"TC-{len(results) + 1:02d}"
    results.append({"id": tc_id, "module": module, "description": description,
                    "expected": expected, "actual": str(actual), "passed": bool(passed)})
    print(f"{tc_id}  {'PASS' if passed else 'FAIL'}  {description}")


def reset_database():
    """Reload sql/02_sample_data.sql (psql-only lines starting with a backslash are skipped)."""
    text = (PROJECT / "sql" / "02_sample_data.sql").read_text(encoding="utf-8")
    sql = "\n".join(line for line in text.splitlines() if not line.strip().startswith("\\"))
    with db.get_connection() as conn:
        conn.autocommit = True      # the file has its own BEGIN ... COMMIT
        conn.execute(sql)


def constraint_violated(func, *args):
    """Run func(*args). Return the violated constraint name, or None if no database error."""
    try:
        func(*args)
        return None
    except psycopg.Error as e:
        return e.diag.constraint_name


def count(sql, params=None):
    return db.fetch_one(sql, params)["n"]


def new_startup(name, email, sector="SaaS"):
    return {"name": name, "sector": sector, "founded_date": date(2025, 1, 1), "city": "Surat",
            "email": email, "phone": None, "description": None}


def new_founder(email):
    return {"name": "Test Founder", "email": email, "phone": None, "designation": "CEO"}


# ---------------------------------------------------------------------
# Module 1: Startup Management
# ---------------------------------------------------------------------

def test_startup_module():
    reset_database()
    M = "1 Startup"

    sid = sm.register_startup(new_startup("Test Robotics", "hi@testrobotics.in"), new_founder("tf@testrobotics.in"))
    n = count("SELECT COUNT(*) AS n FROM founder WHERE startup_id = %s", (sid,))
    check(M, "Register startup with first founder (transaction)", "startup created with 1 founder",
          f"startup_id={sid}, founders={n}", n == 1)

    err = constraint_violated(sm.register_startup, new_startup("PaySetu", "x@new1.in"), new_founder("f1@new1.in"))
    n = count("SELECT COUNT(*) AS n FROM founder WHERE email = 'f1@new1.in'")
    check(M, "Duplicate startup name rejected; founder not saved (rollback)",
          "uq_startup_name, 0 founder rows", f"{err}, founder rows={n}", err == "uq_startup_name" and n == 0)

    err = constraint_violated(sm.register_startup, new_startup("Fresh Labs", "x@fresh.in"), new_founder("asha@greenleafagro.in"))
    n = count("SELECT COUNT(*) AS n FROM startup WHERE startup_name = 'Fresh Labs'")
    check(M, "Duplicate founder email rejected; startup not saved (rollback)",
          "uq_founder_email, 0 startup rows", f"{err}, startup rows={n}", err == "uq_founder_email" and n == 0)

    err = constraint_violated(sm.register_startup, new_startup("Coin Co", "x@coin.in", "Crypto"), new_founder("f@coin.in"))
    check(M, "Sector outside the allowed list rejected", "chk_startup_sector", err, err == "chk_startup_sector")

    err = constraint_violated(sm.register_startup, new_startup("Mail Co", "not-an-email"), new_founder("f@mail.in"))
    check(M, "Badly formatted email rejected", "chk_startup_email", err, err == "chk_startup_email")

    names = [r["startup_name"] for r in sm.get_startups("bengal")]
    check(M, "Search 'bengal' (ILIKE on city)", "CloudLedger, PaySetu", names, names == ["CloudLedger", "PaySetu"])

    names = [r["startup_name"] for r in sm.get_startups("", "AgriTech")]
    check(M, "Filter by sector AgriTech", "AquaSense, GreenLeaf Agro", names, names == ["AquaSense", "GreenLeaf Agro"])

    s = sm.get_startup(1)
    s_update = {"name": s["startup_name"], "sector": s["sector"], "founded_date": s["founded_date"], "city": "Mumbai",
                "email": s["email"], "phone": s["phone"], "description": s["description"]}
    rows = sm.update_startup(1, s_update)
    check(M, "Update startup city", "1 row updated, city = Mumbai",
          f"rows={rows}, city={sm.get_startup(1)['city']}", rows == 1 and sm.get_startup(1)["city"] == "Mumbai")

    err = constraint_violated(sm.delete_startup, 4)
    check(M, "Delete startup that has applications (ON DELETE RESTRICT)", "fk_application_startup",
          err, err == "fk_application_startup")

    sm.delete_startup(sid)
    n = count("SELECT COUNT(*) AS n FROM founder WHERE startup_id = %s", (sid,))
    check(M, "Delete startup without applications cascades to founders", "0 founders left", n, n == 0)

    sneha = db.fetch_one("SELECT founder_id FROM founder WHERE startup_id = 4")["founder_id"]
    removed = sm.remove_founder(4, sneha)
    check(M, "Removing the last founder is refused (BR-1)", "False", removed, removed is False)


# ---------------------------------------------------------------------
# Module 2: Application Management
# ---------------------------------------------------------------------

def app_status(aid):
    return db.fetch_one("SELECT status FROM application WHERE application_id = %s", (aid,))["status"]


def test_application_module():
    reset_database()
    M = "2 Application"

    aid = am.submit_application(10, "Coding club kits for schools", 600000)
    check(M, "Submit application (status defaults to Submitted)", "Submitted",
          app_status(aid), app_status(aid) == "Submitted")

    err = constraint_violated(am.submit_application, 10, "Second idea", 100000)
    check(M, "Second open application for the same startup rejected (BR-3)",
          "uq_one_open_application", err, err == "uq_one_open_application")

    aid2 = am.submit_application(6, "Pivot: B2B supply app", 900000)
    check(M, "Re-application after rejection allowed (D2)", "new application created",
          f"application_id={aid2}", aid2 is not None)

    ok = am.change_status(10, "Submitted", "Under Review")
    check(M, "Status change Submitted -> Under Review", "True, Under Review",
          f"{ok}, {app_status(10)}", ok and app_status(10) == "Under Review")

    try:
        am.change_status(aid, "Submitted", "Accepted")
        outcome = "allowed"
    except ValueError:
        outcome = "ValueError"
    check(M, "Direct change to Accepted is not allowed", "ValueError", outcome, outcome == "ValueError")

    stale = am.change_status(8, "Submitted", "Under Review")
    check(M, "Status change with stale old status updates nothing", "False", stale, stale is False)

    try:
        am.admit_application(10, TODAY, TODAY + timedelta(days=365))
        outcome = "admitted"
    except ValueError as e:
        outcome = str(e)
    check(M, "Admit application with no evaluations refused (BR-7)", "ValueError, still Under Review",
          f"{outcome} / {app_status(10)}", "evaluation" in outcome and app_status(10) == "Under Review")

    err = constraint_violated(am.admit_application, 9, TODAY, TODAY - timedelta(days=1))
    n = count("SELECT COUNT(*) AS n FROM incubation WHERE application_id = 9")
    check(M, "Admit with end date before start: whole transaction rolled back",
          "chk_incubation_expected, still Under Review, 0 incubations",
          f"{err}, {app_status(9)}, {n}", err == "chk_incubation_expected" and app_status(9) == "Under Review" and n == 0)

    inc_id = am.admit_application(9, TODAY, TODAY + timedelta(days=365))
    row = db.fetch_one("SELECT status, decision_date FROM application WHERE application_id = 9")
    n = count("SELECT COUNT(*) AS n FROM incubation WHERE application_id = 9")
    check(M, "Admit valid application: Accepted + incubation created (transaction)",
          "Accepted, decision_date = today, 1 incubation",
          f"{row['status']}, {row['decision_date']}, incubation_id={inc_id}",
          row["status"] == "Accepted" and row["decision_date"] == TODAY and n == 1)

    try:
        am.admit_application(9, TODAY, TODAY + timedelta(days=365))
        outcome = "admitted twice"
    except ValueError:
        outcome = "ValueError"
    check(M, "Admitting an already accepted application refused", "ValueError", outcome, outcome == "ValueError")

    am.change_status(8, "Under Review", "Rejected")
    row = db.fetch_one("SELECT status, decision_date FROM application WHERE application_id = 8")
    check(M, "Reject application sets decision_date", "Rejected, today",
          f"{row['status']}, {row['decision_date']}", row["status"] == "Rejected" and row["decision_date"] == TODAY)

    rows = am.get_status_report()
    report = {r["status"]: r["applications"] for r in rows}
    check(M, "Status report (GROUP BY status) adds up to all applications", "sum = total rows",
          report, sum(report.values()) == count("SELECT COUNT(*) AS n FROM application"))


# ---------------------------------------------------------------------
# Module 3: Evaluation Management
# ---------------------------------------------------------------------

def test_evaluation_module():
    reset_database()
    M = "3 Evaluation"

    names = [r["startup_name"] for r in em.get_strong_applications(80)]
    check(M, "HAVING AVG(score) >= 80", "CloudLedger, GreenLeaf Agro, MediQuick Health, PaySetu",
          names, names == ["CloudLedger", "GreenLeaf Agro", "MediQuick Health", "PaySetu"])

    overall, rows = em.get_above_overall_average()
    check(M, "Subquery: applications above the overall average", "overall 74.8, 6 applications",
          f"overall {overall}, {len(rows)} applications", str(overall) == "74.8" and len(rows) == 6)

    top = {r["application_id"]: (r["top_evaluator"], r["top_score"]) for r in em.get_top_evaluation_per_application()}
    check(M, "Correlated subquery: top evaluation per application", "9 applications; #2 -> Dr. Farhan Siddiqui 90",
          f"{len(top)} applications; #2 -> {top.get(2)}", len(top) == 9 and top.get(2) == ("Dr. Farhan Siddiqui", 90))

    workload = {r["full_name"]: r["evaluations_done"] for r in em.get_evaluators()}
    check(M, "Evaluator list (LEFT JOIN + COUNT)", "5 evaluators, Rahul Bhatia 7",
          workload, len(workload) == 5 and workload["Rahul Bhatia"] == 7)

    pending = [r["application_id"] for r in em.get_pending_for_evaluator(5)]
    check(M, "Pending queue for evaluator 5 (NOT EXISTS)", "[9]", pending, pending == [9])

    saved = em.record_evaluation(9, 5, 73, "Good water-saving data")
    pending = [r["application_id"] for r in em.get_pending_for_evaluator(5)]
    check(M, "Record evaluation; queue becomes empty", "True, []", f"{saved}, {pending}", saved and pending == [])

    err = constraint_violated(em.record_evaluation, 9, 5, 60, "Again")
    check(M, "Second evaluation by same evaluator rejected (composite PK, BR-5)", "pk_evaluation",
          err, err == "pk_evaluation")

    err = constraint_violated(em.record_evaluation, 8, 1, 150, "Too high")
    check(M, "Score 150 rejected (CHECK, BR-6)", "chk_evaluation_score", err, err == "chk_evaluation_score")

    saved = em.record_evaluation(1, 3, 70, "Late")
    check(M, "Evaluation of an Accepted application refused (INSERT ... SELECT)", "False", saved, saved is False)

    err = constraint_violated(em.delete_evaluator, 1)
    check(M, "Delete evaluator with evaluations (ON DELETE RESTRICT)", "fk_evaluation_evaluator",
          err, err == "fk_evaluation_evaluator")

    em.add_evaluator({"name": "Temp Eval", "email": "temp@eval.in", "expertise": "SaaS", "organization": None})
    temp_id = db.fetch_one("SELECT evaluator_id FROM evaluator WHERE email = 'temp@eval.in'")["evaluator_id"]
    rows = em.delete_evaluator(temp_id)
    check(M, "Add then delete an evaluator with no evaluations", "1 row deleted", rows, rows == 1)


# ---------------------------------------------------------------------
# Module 4: Mentor Management
# ---------------------------------------------------------------------

def test_mentor_module():
    reset_database()
    M = "4 Mentor"

    workload = {r["full_name"]: r["active_startups"] for r in mm.get_mentors()}
    check(M, "Mentor workload (LEFT JOIN, condition in ON) includes zeros",
          "Rohan Desai 2, Kavita Rao 0, Sanjay Gupta 0",
          workload, workload["Rohan Desai"] == 2 and workload["Kavita Rao"] == 0 and workload["Sanjay Gupta"] == 0)

    names = [r["startup_name"] for r in mm.get_unmentored_incubations()]
    check(M, "Active incubations without an active mentor", "SolarNest Energy", names, names == ["SolarNest Energy"])

    ok = mm.assign_mentor(4, 6, "Marketing plan")
    names = [r["startup_name"] for r in mm.get_unmentored_incubations()]
    check(M, "Assign mentor to SolarNest; it leaves the unmentored list", "True, []",
          f"{ok}, {names}", ok and names == [])

    err = constraint_violated(mm.assign_mentor, 4, 6, None)
    check(M, "Same mentor assigned twice rejected (composite PK)", "pk_mentorship", err, err == "pk_mentorship")

    ok = mm.assign_mentor(3, 6, None)
    check(M, "Assign mentor to an Exited incubation refused", "False", ok, ok is False)

    err = constraint_violated(db.execute, "INSERT INTO mentorship (incubation_id, mentor_id) VALUES (999, 6)")
    check(M, "Mentorship for a non-existent incubation rejected (FK, D4)", "fk_mentorship_incubation",
          err, err == "fk_mentorship_incubation")

    ok = mm.end_mentorship(4, 6)
    row = db.fetch_one("SELECT status, end_date FROM mentorship WHERE incubation_id = 4 AND mentor_id = 6")
    check(M, "End mentorship sets Completed and end_date together", "True, Completed, today",
          f"{ok}, {row['status']}, {row['end_date']}", ok and row["status"] == "Completed" and row["end_date"] == TODAY)

    err = constraint_violated(mm.delete_mentor, 1)
    check(M, "Delete mentor with mentorships (ON DELETE RESTRICT)", "fk_mentorship_mentor",
          err, err == "fk_mentorship_mentor")

    names = [r["startup_name"] for r in mm.get_my_startups(1)]
    check(M, "Mentor role: Rohan's startups", "CloudLedger, GreenLeaf Agro, MediQuick Health (any order)",
          names, sorted(names) == ["CloudLedger", "GreenLeaf Agro", "MediQuick Health"])


# ---------------------------------------------------------------------
# Module 5: Progress Management
# ---------------------------------------------------------------------

def ms_row(mid):
    return db.fetch_one("SELECT status, completed_on FROM milestone WHERE milestone_id = %s", (mid,))


def test_progress_module():
    reset_database()
    M = "5 Progress"

    progress = {r["startup_name"]: (r["completed"], r["total_milestones"], str(r["percent_complete"]))
                for r in pm.get_progress_report()}
    check(M, "Progress report (CASE inside SUM, percentage)", "GreenLeaf 2/4 = 50.0, CloudLedger 3/3 = 100.0",
          progress, progress["GreenLeaf Agro"] == (2, 4, "50.0") and progress["CloudLedger"] == (3, 3, "100.0"))

    dash = {r["startup_name"]: r["total_milestones"] for r in pm.get_dashboard()}
    check(M, "Dashboard view: milestone counts not multiplied by mentors (no fan-out)",
          "5 incubations, GreenLeaf 4 milestones", dash, len(dash) == 5 and dash["GreenLeaf Agro"] == 4)

    overdue = pm.get_overdue_milestones()
    titles = [r["title"] for r in overdue]
    valid = all(r["target_date"] < TODAY and r["status"] != "Completed" for r in overdue)
    check(M, "Overdue milestones (date arithmetic; depends on today's date)",
          "includes 'Partner with 10 clinics' and 'Reach 100 subscribed homes'; all past target and not completed",
          titles, "Partner with 10 clinics" in titles and "Reach 100 subscribed homes" in titles and valid)

    ok = pm.create_milestone(4, "Launch referral scheme", None, TODAY + timedelta(days=60))
    status = db.fetch_one("SELECT status FROM milestone WHERE title = 'Launch referral scheme'")["status"]
    check(M, "Create milestone (status defaults to Pending)", "True, Pending", f"{ok}, {status}", ok and status == "Pending")

    err = constraint_violated(pm.create_milestone, 4, "Launch referral scheme", None, TODAY)
    check(M, "Duplicate milestone title in same incubation rejected", "uq_milestone_title",
          err, err == "uq_milestone_title")

    ok = pm.create_milestone(3, "Late idea", None, TODAY)
    check(M, "Create milestone for an Exited incubation refused", "False", ok, ok is False)

    pm.update_milestone_status(3, "Completed", TODAY)
    first = ms_row(3)
    pm.update_milestone_status(3, "In Progress", TODAY)
    second = ms_row(3)
    check(M, "Complete a milestone, then revert it (completed_on set, then cleared)",
          "Completed/today, then In Progress/None",
          f"{first['status']}/{first['completed_on']}, then {second['status']}/{second['completed_on']}",
          first["completed_on"] == TODAY and second["completed_on"] is None)

    ok = pm.update_milestone_status(6, "Completed", TODAY, mentor_id=1)
    check(M, "Mentor updates a milestone of a startup they mentor", "True", ok, ok is True)

    ok = pm.update_milestone_status(11, "Completed", TODAY, mentor_id=1)
    check(M, "Mentor cannot update another startup's milestone (EXISTS)", "False, milestone unchanged",
          f"{ok}, {ms_row(11)['status']}", ok is False and ms_row(11)["status"] == "In Progress")

    err = constraint_violated(db.execute, "UPDATE milestone SET status = 'Completed' WHERE milestone_id = 4")
    check(M, "Completed without completion date rejected (CHECK, BR-10)", "chk_milestone_completion",
          err, err == "chk_milestone_completion")


# ---------------------------------------------------------------------
# User interface: every screen of every role opens without errors
# ---------------------------------------------------------------------

def test_user_interface():
    reset_database()
    M = "UI"
    app_file = str(PROJECT / "app" / "app.py")

    def open_app():
        at = AppTest.from_file(app_file, default_timeout=30)
        at.run()
        return at

    admin_actions = {
        "startup_action": ["View & search", "Register startup", "Update startup",
                           "Manage founders", "Delete startup", "Sector report"],
        "app_action": ["All applications", "Update status", "Admit to incubation", "Status report"],
        "eval_action": ["Evaluators", "Add evaluator", "Edit / delete evaluator", "Results"],
        "mentor_action": ["Mentors", "Add mentor", "Edit / delete mentor", "Assign mentor",
                          "Assignments", "Startups without a mentor"],
        "progress_action": ["Dashboard", "Milestones", "Add milestone", "Progress report", "Overdue milestones"],
    }
    failures = []
    at = open_app()
    for key, actions in admin_actions.items():
        for action in actions:
            at.radio(key=key).set_value(action).run()
            if at.exception:
                failures.append(action)
    total = sum(len(a) for a in admin_actions.values())
    check(M, "Administrator: every action of all 5 modules opens", f"{total} screens, 0 errors",
          f"{total} screens, errors: {failures or 0}", not failures)

    role_ids = {"Startup / Founder": [1, 4, 10], "Evaluator": [1, 5], "Mentor": [1, 3, 6]}
    failures = []
    for role, ids in role_ids.items():
        for rid in ids:
            at = open_app()
            at.sidebar.radio[0].set_value(role).run()
            at.sidebar.selectbox[0].set_value(rid).run()
            if at.exception:
                failures.append(f"{role} {rid}")
    check(M, "Startup, Evaluator and Mentor roles open for several users", "8 role views, 0 errors",
          f"errors: {failures or 0}", not failures)

    at = open_app()
    at.radio(key="startup_action").set_value("Register startup").run()
    boxes = {t.label: t for t in at.text_input}
    boxes["Startup name *"].input("PaySetu")
    boxes["City *"].input("Pune")
    boxes["Startup email *"].input("ui@test.in")
    boxes["Founder full name *"].input("UI Tester")
    boxes["Founder email *"].input("ui.founder@test.in")
    [b for b in at.button if b.label == "Register startup"][0].click().run()
    errors = [e.value for e in at.error]
    check(M, "Register form shows a readable error for a duplicate name",
          "'A startup with this name already exists.'", errors,
          "A startup with this name already exists." in errors)


# ---------------------------------------------------------------------
# Run everything and save the results
# ---------------------------------------------------------------------

def write_results_file():
    passed = sum(r["passed"] for r in results)
    lines = [
        "# Automated Test Results",
        "",
        f"- Run on: {datetime.now():%Y-%m-%d %H:%M}",
        "- Command: `python tests/test_app.py`",
        f"- Result: **{passed} of {len(results)} passed**",
        "",
        "| ID | Module | Test case | Expected | Actual | Result |",
        "|---|---|---|---|---|---|",
    ]
    for r in results:
        actual = r["actual"].replace("|", "/")
        lines.append(f"| {r['id']} | {r['module']} | {r['description']} | {r['expected']} | {actual} | "
                     f"{'PASS' if r['passed'] else 'FAIL'} |")
    out = PROJECT / "results" / "test_results.md"
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out, passed


if __name__ == "__main__":
    try:
        test_startup_module()
        test_application_module()
        test_evaluation_module()
        test_mentor_module()
        test_progress_module()
        test_user_interface()
    finally:
        reset_database()     # always leave the sample data clean
    path, passed = write_results_file()
    print(f"\n{passed} of {len(results)} tests passed. Results saved to {path}")
