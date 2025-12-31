import streamlit as st
import sqlite3
from datetime import date, timedelta, datetime
import pandas as pd
import io
import csv

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
    
    /* Date exist warning */
    .date-warning {
        background-color: #fff3cd;
        border: 1px solid #ffeaa7;
        color: #856404;
        padding: 0.75rem;
        border-radius: 6px;
        margin-bottom: 1rem;
    }
    
    /* Download button */
    .download-btn {
        background: linear-gradient(45deg, #4CAF50, #2E7D32);
        color: white;
        border: none;
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        font-weight: bold;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    
    .download-btn:hover {
        background: linear-gradient(45deg, #2E7D32, #1B5E20);
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(46, 125, 50, 0.3);
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
    task_date TEXT UNIQUE,
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

def check_date_exists(selected_date):
    c.execute("SELECT id, task FROM tasks WHERE task_date = ?", (selected_date.isoformat(),))
    return c.fetchone()

def save_or_update_task(selected_date, task_text):
    existing_task = check_date_exists(selected_date)
    
    if existing_task:
        # Update existing task
        c.execute("""
            UPDATE tasks 
            SET task = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE task_date = ?
        """, (task_text, selected_date.isoformat()))
        action = "updated"
    else:
        # Insert new task
        c.execute(
            "INSERT OR REPLACE INTO tasks (task_date, task) VALUES (?,?)",
            (selected_date.isoformat(), task_text)
        )
        action = "saved"
    
    conn.commit()
    return action, existing_task is not None

def update_task(task_id, new_task):
    c.execute("UPDATE tasks SET task = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", 
              (new_task, task_id))
    conn.commit()

def delete_task(task_id):
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()

def get_tasks_for_download(start_date):
    c.execute("SELECT task_date, task FROM tasks ORDER BY task_date")
    all_tasks = c.fetchall()
    
    if not all_tasks:
        return None
    
    # Create DataFrame
    data = []
    for task_date_str, task_text in all_tasks:
        task_date = date.fromisoformat(task_date_str)
        
        # Calculate day number from start date
        c.execute("SELECT start_date FROM settings")
        row = c.fetchone()
        if row:
            start_date = date.fromisoformat(row[0])
            day_number = (task_date - start_date).days + 1
            if day_number < 1:
                day_number = None
        else:
            day_number = None
        
        # Format date nicely
        formatted_date = task_date.strftime("%A, %d %B %Y")
        
        data.append({
            "Day Number": day_number,
            "Date": formatted_date,
            "Task": task_text,
            "Raw Date": task_date_str  # For sorting
        })
    
    df = pd.DataFrame(data)
    
    # Sort by raw date
    if not df.empty:
        df = df.sort_values("Raw Date")
        df = df.drop(columns=["Raw Date"])
    
    return df

def create_csv_download(df):
    """Create CSV file for download"""
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')

def create_excel_download(df):
    """Create Excel file for download (if openpyxl is available)"""
    try:
        # Try to import openpyxl
        import openpyxl
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Internship Tasks')
            worksheet = writer.sheets['Internship Tasks']
            
            # Adjust column widths
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
        
        return output.getvalue(), True
    except ImportError:
        return None, False

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
        if st.button("💾 Save Date", use_container_width=True, key="save_date"):
            c.execute("DELETE FROM settings")
            c.execute("INSERT INTO settings VALUES (?)", (start_date.isoformat(),))
            conn.commit()
            st.success("Start date saved successfully!")
            st.rerun()
    
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
    
    # Task Entry with Update Functionality
    st.divider()
    st.subheader("📝 Add/Update Task")
    
    # Date selection with quick navigation
    col_date1, col_date2, col_date3 = st.columns(3)
    with col_date1:
        if st.button("⬅️ Previous Day", use_container_width=True):
            if 'selected_date' in st.session_state:
                st.session_state.selected_date = st.session_state.selected_date - timedelta(days=1)
            else:
                st.session_state.selected_date = date.today() - timedelta(days=1)
            st.rerun()
    
    with col_date2:
        if st.button("📅 Today", use_container_width=True):
            st.session_state.selected_date = date.today()
            st.rerun()
    
    with col_date3:
        if st.button("➡️ Next Day", use_container_width=True):
            if 'selected_date' in st.session_state:
                st.session_state.selected_date = st.session_state.selected_date + timedelta(days=1)
            else:
                st.session_state.selected_date = date.today() + timedelta(days=1)
            st.rerun()
    
    # Main date input
    if 'selected_date' not in st.session_state:
        st.session_state.selected_date = date.today()
    
    task_date = st.date_input(
        "Select Date for Task",
        value=st.session_state.selected_date,
        key="task_date_input"
    )
    
    # Update session state
    st.session_state.selected_date = task_date
    
    # Check if date already has a task
    existing_task = check_date_exists(task_date)
    
    # Show warning if date exists
    if existing_task:
        st.markdown(f"""
        <div class="date-warning">
            ⚠️ <strong>Date already has a task!</strong><br>
            Updating will replace the existing task for {task_date.strftime('%d %B %Y')}.
        </div>
        """, unsafe_allow_html=True)
    
    # Pre-fill task if date exists
    default_task = existing_task[1] if existing_task else ""
    task = st.text_area(
        "Task Description", 
        value=default_task,
        placeholder="Enter your task details here...",
        height=150,
        key="task_input"
    )
    
    # Action buttons
    col_add, col_clear, col_view = st.columns(3)
    
    with col_add:
        if existing_task:
            button_label = "🔄 Update Task"
            button_type = "primary"
        else:
            button_label = "💾 Save Task"
            button_type = "primary"
        
        if st.button(button_label, use_container_width=True, type=button_type, key="save_update_btn"):
            if task.strip():
                action, was_update = save_or_update_task(task_date, task)
                message = f"✅ Task {action} successfully!"
                if was_update:
                    message += " (Existing task updated)"
                st.success(message)
                st.rerun()
            else:
                st.warning("⚠️ Task cannot be empty")
    
    with col_clear:
        if st.button("🗑️ Clear Form", use_container_width=True, key="clear_form"):
            st.session_state.pop('task_input', None)
            st.rerun()
    
    with col_view:
        if st.button("👁️ View Date", use_container_width=True, key="view_date"):
            st.session_state.filter_date = task_date
            st.rerun()
    
    # Download Section
    st.divider()
    st.subheader("📥 Export Data")
    
    col_download1, col_download2 = st.columns([2, 1])
    
    with col_download1:
        st.info("Export all tasks with calculated day numbers based on your start date.")
    
    with col_download2:
        # Check if we have tasks to download
        c.execute("SELECT COUNT(*) FROM tasks")
        task_count = c.fetchone()[0]
        
        if task_count > 0:
            # Get data for download
            df = get_tasks_for_download(start_date)
            
            if df is not None and not df.empty:
                # Create download buttons
                col_csv, col_excel = st.columns(2)
                
                with col_csv:
                    # CSV Download
                    csv_data = create_csv_download(df)
                    st.download_button(
                        label="📥 CSV",
                        data=csv_data,
                        file_name=f"internship_tasks_{date.today().strftime('%Y%m%d')}.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="csv_download"
                    )
                
                with col_excel:
                    # Excel Download (if available)
                    excel_data, excel_available = create_excel_download(df)
                    if excel_available and excel_data:
                        st.download_button(
                            label="📊 Excel",
                            data=excel_data,
                            file_name=f"internship_tasks_{date.today().strftime('%Y%m%d')}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True,
                            key="excel_download"
                        )
                    else:
                        # Show disabled button or info
                        st.info("Excel export requires openpyxl package")
            else:
                st.warning("No tasks to download")
        else:
            st.warning("No tasks available for download")
    
    # Task History with Edit Functionality
    st.divider()
    st.subheader("📚 Task History")
    
    # Filter options
    col_filter1, col_filter2, col_filter3 = st.columns(3)
    with col_filter1:
        # Initialize filter_date in session state
        if 'filter_date' not in st.session_state:
            st.session_state.filter_date = None
        
        filter_date = st.date_input(
            "Filter by Date", 
            value=st.session_state.filter_date,
            key="filter_date_input"
        )
        if filter_date != st.session_state.filter_date:
            st.session_state.filter_date = filter_date
    
    with col_filter2:
        limit = st.slider("Show tasks", min_value=5, max_value=100, value=20, key="task_limit")
    
    with col_filter3:
        if st.button("🧹 Clear Filter", use_container_width=True):
            st.session_state.filter_date = None
            st.rerun()
    
    # Get tasks based on filter
    if st.session_state.filter_date:
        c.execute("""
            SELECT id, task_date, task 
            FROM tasks 
            WHERE task_date = ? 
            ORDER BY id DESC
        """, (st.session_state.filter_date.isoformat(),))
    else:
        c.execute("""
            SELECT id, task_date, task 
            FROM tasks 
            ORDER BY task_date DESC 
            LIMIT ?
        """, (limit,))
    
    tasks = c.fetchall()
    
    if tasks:
        for task_id, task_date_str, task_text in tasks:
            task_date_display = date.fromisoformat(task_date_str)
            
            # Calculate day number if start date exists
            day_number = ""
            c.execute("SELECT start_date FROM settings")
            row = c.fetchone()
            if row:
                start_date_for_calc = date.fromisoformat(row[0])
                day_num = (task_date_display - start_date_for_calc).days + 1
                if day_num > 0:
                    day_number = f"Day {day_num} • "
            
            # Display each task in a card
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.markdown(f"""
                    <div class="task-card">
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 4px;">
                            {day_number}📅 {task_date_str}
                        </div>
                        <p style="margin: 0; line-height: 1.5;">{task_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Edit button
                    if st.button("✏️ Edit", key=f"edit_btn_{task_id}", use_container_width=True):
                        st.session_state.selected_date = task_date_display
                        st.session_state[f"edit_{task_id}"] = True
                        st.rerun()
            
            # Edit form (show if edit button was clicked)
            if st.session_state.get(f"edit_{task_id}", False):
                with st.expander(f"Edit Task - {task_date_str}", expanded=True):
                    with st.form(key=f"edit_form_{task_id}"):
                        new_task = st.text_area("Edit Task", value=task_text, height=100, key=f"edit_text_{task_id}")
                        col_save_edit, col_cancel, col_delete = st.columns([2, 1, 1])
                        
                        with col_save_edit:
                            if st.form_submit_button("💾 Save", use_container_width=True):
                                update_task(task_id, new_task)
                                st.session_state.pop(f"edit_{task_id}", None)
                                st.success("Task updated successfully!")
                                st.rerun()
                        
                        with col_cancel:
                            if st.form_submit_button("❌ Cancel", use_container_width=True):
                                st.session_state.pop(f"edit_{task_id}", None)
                                st.rerun()
                        
                        with col_delete:
                            if st.form_submit_button("🗑️ Delete", use_container_width=True, type="secondary"):
                                delete_task(task_id)
                                st.session_state.pop(f"edit_{task_id}", None)
                                st.success("Task deleted successfully!")
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
    
    c.execute("SELECT MIN(task_date), MAX(task_date) FROM tasks")
    date_range = c.fetchone()
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Total Tasks", total_tasks)
    
    with col_stat2:
        st.metric("Active Days", active_days)
    
    with col_stat3:
        if date_range and date_range[0] and date_range[1]:
            first_date = date.fromisoformat(date_range[0]).strftime("%d %b")
            last_date = date.fromisoformat(date_range[1]).strftime("%d %b %Y")
            st.metric("Date Range", f"{first_date} - {last_date}")
        else:
            st.metric("Date Range", "N/A")
    
    # Logout button
    st.divider()
    col_logout, _ = st.columns([1, 3])
    with col_logout:
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.pop('username', None)
            st.session_state.pop('selected_date', None)
            st.session_state.pop('filter_date', None)
            # Clear all edit states
            for key in list(st.session_state.keys()):
                if key.startswith('edit_'):
                    st.session_state.pop(key, None)
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
    
    # Check for URL parameters
    query_params = st.query_params
    
    # Handle delete action
    if "delete" in query_params:
        task_id = query_params["delete"]
        delete_task(int(task_id))
        st.query_params.clear()
        st.rerun()
    
    # Handle date selection from URL
    if "date" in query_params:
        try:
            selected_date = date.fromisoformat(query_params["date"])
            st.session_state.selected_date = selected_date
            st.query_params.clear()
        except ValueError:
            pass
    
    # Route to login or dashboard
    if not st.session_state.logged_in:
        login()
    else:
        dashboard()
