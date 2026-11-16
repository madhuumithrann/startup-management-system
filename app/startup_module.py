"""
startup_module.py - Module 1: Startup Management

Part 1 (database functions): run SQL through db.py and return Python data.
Part 2 (screens): Streamlit forms and tables that call the Part 1 functions.

Requirements covered: FR-1.1 to FR-1.6, report R1.
"""

from datetime import date

import psycopg
import streamlit as st

import db

# Must match chk_startup_sector in sql/01_schema.sql (the database is the final judge).
SECTORS = ["FinTech", "HealthTech", "EdTech", "AgriTech",
           "CleanTech", "E-Commerce", "SaaS", "Other"]


# =====================================================================
# PART 1: DATABASE FUNCTIONS
# =====================================================================

def get_startups(search_text="", sector="All"):
    """FR-1.3: list startups, optionally filtered by search text and sector."""
    pattern = "%" + search_text + "%"
    sql = """
        SELECT startup_id, startup_name, sector, city, email, founded_date, registered_on
        FROM startup
        WHERE (startup_name ILIKE %s OR city ILIKE %s)
    """
    params = [pattern, pattern]
    if sector != "All":
        sql += " AND sector = %s"
        params.append(sector)
    sql += " ORDER BY startup_name"
    return db.fetch_all(sql, params)


def get_startup(startup_id):
    """FR-1.4: one startup's full row, or None if it does not exist."""
    return db.fetch_one("SELECT * FROM startup WHERE startup_id = %s", (startup_id,))


def get_founders(startup_id):
    """FR-1.4: founders of one startup."""
    return db.fetch_all(
        """SELECT founder_id, full_name, designation, email, phone
           FROM founder
           WHERE startup_id = %s
           ORDER BY founder_id""",
        (startup_id,),
    )


def register_startup(startup, founder):
    """
    FR-1.1 + FR-1.2: insert a startup AND its first founder in ONE transaction.
    If the founder insert fails, the startup insert is rolled back too (BR-1).
    Returns the new startup_id.
    """
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO startup (startup_name, sector, founded_date, city, email, phone, description)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING startup_id""",
                (startup["name"], startup["sector"], startup["founded_date"], startup["city"],
                 startup["email"], startup["phone"], startup["description"]),
            )
            new_id = cur.fetchone()["startup_id"]

            cur.execute(
                """INSERT INTO founder (startup_id, full_name, email, phone, designation)
                   VALUES (%s, %s, %s, %s, %s)""",
                (new_id, founder["name"], founder["email"], founder["phone"], founder["designation"]),
            )
    # Leaving the "with" block without an error -> COMMIT (both rows saved).
    return new_id


def update_startup(startup_id, startup):
    """FR-1.5: update a startup's details. Returns number of rows changed."""
    return db.execute(
        """UPDATE startup
           SET startup_name = %s, sector = %s, founded_date = %s, city = %s,
               email = %s, phone = %s, description = %s
           WHERE startup_id = %s""",
        (startup["name"], startup["sector"], startup["founded_date"], startup["city"],
         startup["email"], startup["phone"], startup["description"], startup_id),
    )


def delete_startup(startup_id):
    """
    FR-1.6: delete a startup.
    Founders are removed automatically (ON DELETE CASCADE).
    Fails if the startup has applications (ON DELETE RESTRICT).
    """
    return db.execute("DELETE FROM startup WHERE startup_id = %s", (startup_id,))


def add_founder(startup_id, founder):
    """FR-1.2: add another founder to an existing startup."""
    return db.execute(
        """INSERT INTO founder (startup_id, full_name, email, phone, designation)
           VALUES (%s, %s, %s, %s, %s)""",
        (startup_id, founder["name"], founder["email"], founder["phone"], founder["designation"]),
    )


def update_founder(founder_id, founder):
    """FR-1.5: update a founder's details."""
    return db.execute(
        """UPDATE founder
           SET full_name = %s, email = %s, phone = %s, designation = %s
           WHERE founder_id = %s""",
        (founder["name"], founder["email"], founder["phone"], founder["designation"], founder_id),
    )


def remove_founder(startup_id, founder_id):
    """
    Remove a founder, but never the LAST one (BR-1: a startup needs >= 1 founder).
    Returns True if removed, False if refused.
    """
    row = db.fetch_one("SELECT COUNT(*) AS total FROM founder WHERE startup_id = %s", (startup_id,))
    if row["total"] <= 1:
        return False
    db.execute("DELETE FROM founder WHERE founder_id = %s AND startup_id = %s", (founder_id, startup_id))
    return True


def get_sector_counts():
    """Report R1 (query Q5): number of startups in each sector."""
    return db.fetch_all(
        """SELECT sector, COUNT(*) AS number_of_startups
           FROM startup
           GROUP BY sector
           ORDER BY number_of_startups DESC, sector"""
    )


# =====================================================================
# PART 2: SCREENS (Streamlit)
# =====================================================================

def optional(text):
    """Empty input box -> None (stored as NULL), otherwise the trimmed text."""
    text = text.strip()
    return text if text else None


def choose_startup(label, key):
    """A dropdown of all startups. Returns the chosen startup_id (or None if none exist)."""
    rows = db.fetch_all("SELECT startup_id, startup_name FROM startup ORDER BY startup_name")
    if not rows:
        st.info("No startups registered yet.")
        return None
    names = {r["startup_id"]: r["startup_name"] for r in rows}
    return st.selectbox(label, options=list(names.keys()),
                        format_func=lambda sid: names[sid], key=key)


def show_startup_details(startup_id):
    """FR-1.4: show one startup and its founders."""
    s = get_startup(startup_id)
    if s is None:
        st.warning("This startup no longer exists.")
        return
    st.subheader(s["startup_name"])
    col1, col2, col3 = st.columns(3)
    col1.write(f"**Sector:** {s['sector']}")
    col1.write(f"**City:** {s['city']}")
    col2.write(f"**Founded:** {s['founded_date']}")
    col2.write(f"**Registered:** {s['registered_on']}")
    col3.write(f"**Email:** {s['email']}")
    col3.write(f"**Phone:** {s['phone'] or '-'}")
    st.write(f"**Description:** {s['description'] or '-'}")
    st.markdown("**Founders**")
    st.dataframe(get_founders(startup_id), hide_index=True)


def edit_startup_form(startup_id):
    """FR-1.5: a form pre-filled with the startup's current values."""
    s = get_startup(startup_id)
    if s is None:
        st.warning("This startup no longer exists.")
        return
    k = str(startup_id)   # makes widget keys unique per startup
    with st.form("edit_startup_" + k):
        name = st.text_input("Startup name *", value=s["startup_name"], key="name_" + k)
        sector = st.selectbox("Sector *", SECTORS, index=SECTORS.index(s["sector"]), key="sector_" + k)
        founded = st.date_input("Founded date *", value=s["founded_date"],
                                min_value=date(1990, 1, 1), max_value=date.today(), key="founded_" + k)
        city = st.text_input("City *", value=s["city"], key="city_" + k)
        email = st.text_input("Email *", value=s["email"], key="email_" + k)
        phone = st.text_input("Phone", value=s["phone"] or "", key="phone_" + k)
        description = st.text_area("Description", value=s["description"] or "", key="desc_" + k)
        submitted = st.form_submit_button("Save changes")

    if submitted:
        if not name.strip() or not city.strip() or not email.strip():
            st.error("Please fill in all fields marked *.")
            return
        startup = {"name": name.strip(), "sector": sector, "founded_date": founded,
                   "city": city.strip(), "email": email.strip(),
                   "phone": optional(phone), "description": optional(description)}
        try:
            update_startup(startup_id, startup)
            st.success("Startup details updated.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def founder_inputs(prefix, current=None):
    """The four founder input boxes, reused by the register / add / edit forms."""
    current = current or {"full_name": "", "email": "", "phone": "", "designation": "CEO"}
    return {
        "name": st.text_input("Founder full name *", value=current["full_name"], key=prefix + "_fname"),
        "email": st.text_input("Founder email *", value=current["email"], key=prefix + "_femail"),
        "phone": st.text_input("Founder phone", value=current["phone"] or "", key=prefix + "_fphone"),
        "designation": st.text_input("Designation *", value=current["designation"], key=prefix + "_fdesig"),
    }


def founder_is_complete(founder):
    """Basic check that the required founder fields are not blank."""
    return founder["name"].strip() and founder["email"].strip() and founder["designation"].strip()


def clean_founder(founder):
    return {"name": founder["name"].strip(), "email": founder["email"].strip(),
            "phone": optional(founder["phone"]), "designation": founder["designation"].strip()}


# ---------- Admin sections ----------

def view_and_search_section():
    col1, col2 = st.columns(2)
    search = col1.text_input("Search by name or city")
    sector = col2.selectbox("Filter by sector", ["All"] + SECTORS)
    rows = get_startups(search.strip(), sector)
    st.write(f"{len(rows)} startup(s) found")
    st.dataframe(rows, hide_index=True)

    if not rows:
        st.info("No startup matches your search.")
        return

    st.divider()
    if len(rows) == 1:
        # Exactly one match: show its details straight away.
        startup_id = rows[0]["startup_id"]
    else:
        # Several matches: let the user pick, but only from the search results.
        names = {r["startup_id"]: r["startup_name"] for r in rows}
        startup_id = st.selectbox("View full details of", list(names.keys()),
                                  format_func=lambda sid: names[sid],
                                  key=f"view_startup_{search.strip()}_{sector}")
    show_startup_details(startup_id)


def register_section():
    with st.form("register_startup"):
        st.markdown("**Startup details**")
        name = st.text_input("Startup name *")
        sector = st.selectbox("Sector *", SECTORS)
        founded = st.date_input("Founded date *", value=date.today(),
                                min_value=date(1990, 1, 1), max_value=date.today())
        city = st.text_input("City *")
        email = st.text_input("Startup email *")
        phone = st.text_input("Phone")
        description = st.text_area("Description")
        st.markdown("**First founder** (every startup must have at least one)")
        founder = founder_inputs("reg")
        submitted = st.form_submit_button("Register startup")

    if submitted:
        if not name.strip() or not city.strip() or not email.strip() or not founder_is_complete(founder):
            st.error("Please fill in all fields marked *.")
            return
        startup = {"name": name.strip(), "sector": sector, "founded_date": founded,
                   "city": city.strip(), "email": email.strip(),
                   "phone": optional(phone), "description": optional(description)}
        try:
            new_id = register_startup(startup, clean_founder(founder))
            st.success(f"Registered '{startup['name']}' with startup ID {new_id}.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def manage_founders_section():
    startup_id = choose_startup("Startup", key="founders_startup")
    if not startup_id:
        return
    founders = get_founders(startup_id)
    st.dataframe(founders, hide_index=True)

    with st.expander("Add a founder"):
        with st.form("add_founder_" + str(startup_id)):
            founder = founder_inputs("add_" + str(startup_id))
            if st.form_submit_button("Add founder"):
                if not founder_is_complete(founder):
                    st.error("Please fill in all fields marked *.")
                else:
                    try:
                        add_founder(startup_id, clean_founder(founder))
                        st.success("Founder added.")
                    except psycopg.Error as e:
                        st.error(db.error_message(e))

    names = {f["founder_id"]: f["full_name"] for f in founders}

    with st.expander("Edit a founder"):
        founder_id = st.selectbox("Founder to edit", list(names.keys()),
                                  format_func=lambda fid: names[fid], key="edit_fid_" + str(startup_id))
        current = next(f for f in founders if f["founder_id"] == founder_id)
        with st.form("edit_founder_" + str(founder_id)):
            founder = founder_inputs("edit_" + str(founder_id), current)
            if st.form_submit_button("Save founder"):
                if not founder_is_complete(founder):
                    st.error("Please fill in all fields marked *.")
                else:
                    try:
                        update_founder(founder_id, clean_founder(founder))
                        st.success("Founder updated.")
                    except psycopg.Error as e:
                        st.error(db.error_message(e))

    with st.expander("Remove a founder"):
        founder_id = st.selectbox("Founder to remove", list(names.keys()),
                                  format_func=lambda fid: names[fid], key="remove_fid_" + str(startup_id))
        if st.button("Remove founder", key="remove_btn_" + str(startup_id)):
            if remove_founder(startup_id, founder_id):
                st.success("Founder removed.")
            else:
                st.error("A startup must have at least one founder, so the last founder cannot be removed.")


def delete_section():
    startup_id = choose_startup("Startup to delete", key="delete_startup")
    if not startup_id:
        return
    st.warning("Deleting a startup also deletes its founders (ON DELETE CASCADE). "
               "A startup that has applications cannot be deleted (ON DELETE RESTRICT).")
    confirm = st.checkbox("Yes, I want to delete this startup", key="confirm_" + str(startup_id))
    if st.button("Delete startup", disabled=not confirm):
        try:
            delete_startup(startup_id)
            st.success("Startup and its founders deleted.")
        except psycopg.Error as e:
            st.error(db.error_message(e))


def sector_report_section():
    rows = get_sector_counts()
    st.dataframe(rows, hide_index=True)
    st.bar_chart(rows, x="sector", y="number_of_startups")


# ---------- Entry points called from app.py ----------

def admin_page():
    """Administrator: all startup operations."""
    action = st.radio(
        "Choose an action",
        ["View & search", "Register startup", "Update startup",
         "Manage founders", "Delete startup", "Sector report"],
        horizontal=True,
        key="startup_action",
    )
    if action == "View & search":
        view_and_search_section()
    elif action == "Register startup":
        register_section()
    elif action == "Update startup":
        startup_id = choose_startup("Startup to update", key="update_startup")
        if startup_id:
            edit_startup_form(startup_id)
    elif action == "Manage founders":
        manage_founders_section()
    elif action == "Delete startup":
        delete_section()
    elif action == "Sector report":
        sector_report_section()


def startup_profile_page(startup_id):
    """Startup / Founder role: see and update only their own startup."""
    show_startup_details(startup_id)
    with st.expander("Update my startup details"):
        edit_startup_form(startup_id)
