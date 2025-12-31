import streamlit as st
import sqlite3
from datetime import date

# ---------------- CONFIG ----------------
TOTAL_DAYS = 548
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@asmath"

# ---------------- DB ----------------
conn = sqlite3.connect("internship.db", check_same_thread=False)
c = conn.cursor()

c.execute("""
CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_date TEXT,
    task TEXT
)
""")

c.execute("""
CREATE TABLE IF NOT EXISTS settings (
    start_date TEXT
)
""")

# Insert admin once
c.execute("SELECT * FROM users WHERE username=?", (ADMIN_USERNAME,))
if not c.fetchone():
    c.execute("INSERT INTO users VALUES (?,?)", (ADMIN_USERNAME, ADMIN_PASSWORD))
    conn.commit()

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Admin Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        if c.fetchone():
            st.session_state.logged_in = True
            st.success("Login Successful")
            st.rerun()
        else:
            st.error("Invalid credentials")

# ---------------- DASHBOARD ----------------
def dashboard():
    st.title("📅 Internship Tracker (Admin)")

    # Start date
    c.execute("SELECT start_date FROM settings")
    row = c.fetchone()

    start_date = st.date_input(
        "Internship Start Date",
        value=date.fromisoformat(row[0]) if row else date.today()
    )

    if st.button("Save Start Date"):
        c.execute("DELETE FROM settings")
        c.execute("INSERT INTO settings VALUES (?)", (start_date.isoformat(),))
        conn.commit()
        st.success("Start date saved")

    # Calculate days
    completed = (date.today() - start_date).days
    remaining = TOTAL_DAYS - completed

    st.metric("Total Days", TOTAL_DAYS)
    st.metric("Completed Days", max(completed, 0))
    st.metric("Remaining Days", max(remaining, 0))

    st.divider()

    # Task Entry
    st.subheader("📝 Today's Task")
    task = st.text_area("Enter task")

    if st.button("Save Task"):
        if task.strip():
            c.execute(
                "INSERT INTO tasks (task_date, task) VALUES (?,?)",
                (date.today().isoformat(), task)
            )
            conn.commit()
            st.success("Task saved")
        else:
            st.warning("Task cannot be empty")

    # Task History
    st.subheader("📚 Task History")
    c.execute("SELECT task_date, task FROM tasks ORDER BY id DESC LIMIT 10")
    tasks = c.fetchall()

    if tasks:
        for t in tasks:
            st.write(f"**{t[0]}** → {t[1]}")
    else:
        st.info("No tasks added yet")

    # Logout
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

# ---------------- MAIN ----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    login()
else:
    dashboard()
