import streamlit as st
import sqlite3
from datetime import date

# ---------------- CONFIG ----------------
TOTAL_DAYS = 548
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@asmath"

# ---------------- DYNAMIC CSS ----------------
def apply_custom_css():
    st.markdown("""
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Card-like styling for metrics */
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 10px;
        border-left: 4px solid #4CAF50;
        margin-bottom: 1rem;
    }
    
    /* Task cards */
    .task-card {
        background: white;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        border-left: 4px solid #2196F3;
        transition: all 0.3s ease;
    }
    
    .task-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Edit form styling */
    .edit-form {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        border: 1px solid #dee2e6;
    }
    
    /* Button styling */
    .stButton button {
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: scale(1.05);
    }
    
    /* Progress bar animation */
    .stProgress > div > div > div > div {
        background-image: linear-gradient(45deg, 
            rgba(255,255,255,0.15) 25%, 
            transparent 25%, 
            transparent 50%, 
            rgba(255,255,255,0.15) 50%, 
            rgba(255,255,255,0.15) 75%, 
            transparent 75%, 
            transparent);
        background-size: 1rem 1rem;
        animation: progress-bar-stripes 1s linear infinite;
    }
    
    @keyframes progress-bar-stripes {
        from { background-position: 1rem 0; }
        to { background-position: 0 0; }
    }
    
    /* Success/Error messages */
    .stAlert {
        border-radius: 8px;
    }
    
    /* Header styling */
    .st-emotion-cache-1kyxreq {
        justify-content: center;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .metric-card {
            margin-bottom: 0.5rem;
        }
    }
    </style>
    """, unsafe_allow_html=True)

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
    task TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

# ---------------- HELPER FUNCTIONS ----------------
def calculate_progress(start_date):
    completed = (date.today() - start_date).days
    remaining = TOTAL_DAYS - completed
    progress = min(max(completed, 0) / TOTAL_DAYS, 1) * 100
    
    return {
        "completed": max(completed, 0),
        "remaining": max(remaining, 0),
        "progress": progress
    }

def get_all_tasks(limit=50):
    c.execute("SELECT id, task_date, task FROM tasks ORDER BY task_date DESC LIMIT ?", (limit,))
    return c.fetchall()

def update_task(task_id, new_task):
    c.execute("UPDATE tasks SET task = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
              (new_task, task_id))
    conn.commit()

def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Admin Login")
    
    # Login form with styling
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="edit-form">', unsafe_allow_html=True)
            username = st.text_input("👤 Username")
            password = st.text_input("🔑 Password", type="password")
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🚀 Login", use_container_width=True):
                    c.execute("SELECT * FROM users WHERE username=? AND password=?", 
                             (username, password))
                    if c.fetchone():
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("Login Successful")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with col_btn2:
                if st.button("🔄 Clear", use_container_width=True):
                    st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------- DASHBOARD ----------------
def dashboard():
    # Header with user info
    col_title, col_user = st.columns([3, 1])
    with col_title:
        st.title("📅 Internship Tracker")
    with col_user:
        st.markdown(f"""
        <div style="text-align: right; padding: 10px;">
            👤 <strong>{st.session_state.username}</strong><br>
            <small>{date.today().strftime('%d %b %Y')}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Start date configuration
    st.subheader("📅 Settings")
    c.execute("SELECT start_date FROM settings")
    row = c.fetchone()
    
    start_date = st.date_input(
        "🎯 Internship Start Date",
        value=date.fromisoformat(row[0]) if row else date.today(),
        help="Set the start date of your internship"
    )
    
    col_save, col_info = st.columns([1, 3])
    with col_save:
        if st.button("💾 Save Date", use_container_width=True):
            c.execute("DELETE FROM settings")
            c.execute("INSERT INTO settings VALUES (?)", (start_date.isoformat(),))
            conn.commit()
            st.success("Start date saved successfully!")
    
    with col_info:
        if row:
            st.info(f"Current start date: {row[0]}")
    
    # Progress metrics with dynamic CSS
    st.divider()
    st.subheader("📊 Progress Overview")
    
    progress_data = calculate_progress(start_date)
    
    # Progress bar with animation
    st.progress(progress_data["progress"] / 100)
    
    # Metrics in cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3 style="margin:0; color:#4CAF50;">{TOTAL_DAYS}</h3>
            <p style="margin:0; color:#666;">Total Days</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color:#2196F3;">
            <h3 style="margin:0; color:#2196F3;">{progress_data['completed']}</h3>
            <p style="margin:0; color:#666;">Completed Days</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color:#FF9800;">
            <h3 style="margin:0; color:#FF9800;">{progress_data['remaining']}</h3>
            <p style="margin:0; color:#666;">Remaining Days</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Task Entry
    st.divider()
    st.subheader("📝 Add New Task")
    
    task_date = st.date_input("Select Date", value=date.today())
    task = st.text_area("Task Description", 
                       placeholder="Enter your task details here...",
                       height=100)
    
    col_add, col_clear = st.columns(2)
    with col_add:
        if st.button("💾 Save Task", use_container_width=True, type="primary"):
            if task.strip():
                c.execute(
                    "INSERT INTO tasks (task_date, task) VALUES (?,?)",
                    (task_date.isoformat(), task)
                )
                conn.commit()
                st.success("✅ Task saved successfully!")
                st.rerun()
            else:
                st.warning("⚠️ Task cannot be empty")
    
    with col_clear:
        if st.button("🗑️ Clear", use_container_width=True):
            st.rerun()
    
    # Task History with Edit Functionality
    st.divider()
    st.subheader("📚 Task History")
    
    # Filter options
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        filter_date = st.date_input("Filter by Date", value=None)
    with col_filter2:
        limit = st.slider("Show tasks", min_value=5, max_value=100, value=20)
    
    # Get tasks based on filter
    if filter_date:
        c.execute("SELECT id, task_date, task FROM tasks WHERE task_date = ? ORDER BY id DESC", 
                 (filter_date.isoformat(),))
    else:
        c.execute("SELECT id, task_date, task FROM tasks ORDER BY id DESC LIMIT ?", (limit,))
    
    tasks = c.fetchall()
    
    if tasks:
        for task_id, task_date, task_text in tasks:
            # Display each task in a card
            st.markdown(f"""
            <div class="task-card">
                <div style="display: flex; justify-content: space-between; align-items: start;">
                    <div>
                        <strong>📅 {task_date}</strong>
                        <p style="margin: 5px 0;">{task_text}</p>
                    </div>
                    <div style="display: flex; gap: 5px;">
                        <button style="background: #4CAF50; color: white; border: none; 
                                     padding: 3px 8px; border-radius: 4px; cursor: pointer;"
                                onclick="document.getElementById('edit_{task_id}').style.display='block'">
                            ✏️
                        </button>
                        <button style="background: #f44336; color: white; border: none; 
                                     padding: 3px 8px; border-radius: 4px; cursor: pointer;"
                                onclick="if(confirm('Delete this task?')) 
                                         window.location.href='?delete={task_id}'">
                            🗑️
                        </button>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Edit form (hidden by default)
            edit_expander = st.expander(f"✏️ Edit Task - {task_date}")
            with edit_expander:
                with st.form(key=f"edit_form_{task_id}"):
                    new_task = st.text_area("Edit Task", value=task_text, height=100)
                    col_save_edit, col_cancel = st.columns(2)
                    
                    with col_save_edit:
                        if st.form_submit_button("💾 Save Changes", use_container_width=True):
                            update_task(task_id, new_task)
                            st.success("Task updated successfully!")
                            st.rerun()
                    
                    with col_cancel:
                        if st.form_submit_button("❌ Cancel", use_container_width=True):
                            st.rerun()
    else:
        st.info("📭 No tasks found. Add your first task above!")
    
    # Statistics
    st.divider()
    st.subheader("📈 Statistics")
    c.execute("SELECT COUNT(*) FROM tasks")
    total_tasks = c.fetchone()[0]
    
    c.execute("SELECT COUNT(DISTINCT task_date) FROM tasks")
    active_days = c.fetchone()[0]
    
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Total Tasks", total_tasks)
    with col_stat2:
        st.metric("Active Days", active_days)
    
    # Logout button
    st.divider()
    if st.button("🚪 Logout", type="secondary"):
        st.session_state.logged_in = False
        st.session_state.pop('username', None)
        st.rerun()

# ---------------- MAIN ----------------
if __name__ == "__main__":
    # Page configuration
    st.set_page_config(
        page_title="Internship Tracker",
        page_icon="📅",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    # Apply custom CSS
    apply_custom_css()
    
    # Initialize session state
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    # Check for delete action
    query_params = st.query_params
    if "delete" in query_params:
        task_id = query_params["delete"]
        delete_task(int(task_id))
        st.query_params.clear()
        st.rerun()
    
    # Route to login or dashboard
    if not st.session_state.logged_in:
        login()
    else:
        dashboard()
