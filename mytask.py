import streamlit as st
from datetime import date, timedelta, datetime
import pandas as pd
import io
import csv
import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor
import os

# ---------------- CONFIG ----------------
TOTAL_DAYS = 548
# User credentials
USERS = {
    "admin": "admin@asmath",  # Full admin access
    "admin2": "admin@AHBETA"  # Report-only access
}

# PostgreSQL Connection String (Neon Database)
DATABASE_URL = "postgresql://neondb_owner:npg_j3GtRpC7zoJr@ep-curly-glade-aha54euu-pooler.c-3.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"

# ---------------- POSTGRESQL DATABASE FUNCTIONS ----------------
@st.cache_resource
def get_db_connection():
    """Establish PostgreSQL connection"""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        create_tables(conn)
        st.success("✅ Connected to PostgreSQL (Neon Database)!")
        return conn
    except Exception as e:
        st.error(f"❌ Database Connection Failed: {str(e)}")
        st.info("⚠️ Falling back to local data storage...")
        return None

def create_tables(conn):
    """Create necessary tables if they don't exist"""
    try:
        with conn.cursor() as cursor:
            # Create users table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL DEFAULT 'viewer',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    task_date DATE UNIQUE NOT NULL,
                    task TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create settings table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    id SERIAL PRIMARY KEY,
                    setting_key VARCHAR(50) UNIQUE NOT NULL,
                    setting_value TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
            
            # Initialize default users
            for username, password in USERS.items():
                role = "admin" if username == "admin" else "viewer"
                cursor.execute("""
                    INSERT INTO users (username, password, role)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (username) DO NOTHING
                """, (username, password, role))
            
            conn.commit()
            
    except Exception as e:
        conn.rollback()
        st.error(f"Error creating tables: {str(e)}")

# Initialize database connection
conn = get_db_connection()

# ---------------- DYNAMIC CSS ----------------
def apply_custom_css():
    st.markdown("""
    <style>
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Report view specific styles */
    .report-view {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        color: white;
        margin-bottom: 20px;
    }
    
    .report-card {
        background: white;
        padding: 15px;
        margin: 10px 0;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border-left: 5px solid #4CAF50;
    }
    
    .day-header {
        background: #4CAF50;
        color: white;
        padding: 8px 15px;
        border-radius: 8px;
        margin: 15px 0 5px 0;
        font-weight: bold;
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
    
    /* Database status badge */
    .db-status {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .db-postgres {
        background-color: #336791;
        color: white;
    }
    
    .db-local {
        background-color: #4CAF50;
        color: white;
    }
    
    /* User role badge */
    .role-badge {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: bold;
        margin-left: 10px;
    }
    
    .role-admin {
        background-color: #2196F3;
        color: white;
    }
    
    .role-viewer {
        background-color: #FF9800;
        color: white;
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

# ---------------- HELPER FUNCTIONS ----------------
def execute_query(query, params=None, fetch=False):
    """Execute a database query"""
    if conn:
        try:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(query, params or ())
                if fetch:
                    result = cursor.fetchall()
                else:
                    conn.commit()
                    result = None
                return result
        except Exception as e:
            conn.rollback()
            st.error(f"Database error: {str(e)}")
            return None
    else:
        return None

def check_date_exists(selected_date):
    """Check if a task exists for the given date"""
    if conn:
        result = execute_query(
            "SELECT * FROM tasks WHERE task_date = %s",
            (selected_date,),
            fetch=True
        )
        return result[0] if result else None
    else:
        # Fallback to session state
        date_str = selected_date.isoformat()
        for task in st.session_state.get('local_tasks', []):
            if task.get("task_date") == date_str:
                return task
        return None

def save_or_update_task(selected_date, task_text):
    """Save or update task in PostgreSQL"""
    existing_task = check_date_exists(selected_date)
    
    if conn:
        if existing_task:
            # Update existing task
            execute_query(
                """
                UPDATE tasks 
                SET task = %s, updated_at = CURRENT_TIMESTAMP 
                WHERE task_date = %s
                """,
                (task_text, selected_date)
            )
            action = "updated"
            was_update = True
        else:
            # Insert new task
            execute_query(
                """
                INSERT INTO tasks (task_date, task) 
                VALUES (%s, %s)
                ON CONFLICT (task_date) DO UPDATE 
                SET task = EXCLUDED.task, updated_at = CURRENT_TIMESTAMP
                """,
                (selected_date, task_text)
            )
            action = "saved"
            was_update = False
    else:
        # Fallback to session state
        date_str = selected_date.isoformat()
        existing_task = None
        local_tasks = st.session_state.get('local_tasks', [])
        
        for i, task in enumerate(local_tasks):
            if task.get("task_date") == date_str:
                existing_task = task
                task_index = i
                break
        
        if existing_task:
            # Update existing task
            local_tasks[task_index]["task"] = task_text
            local_tasks[task_index]["updated_at"] = datetime.now().isoformat()
            action = "updated"
            was_update = True
        else:
            # Insert new task
            new_task = {
                "id": len(local_tasks) + 1,
                "task_date": date_str,
                "task": task_text,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            local_tasks.append(new_task)
            action = "saved"
            was_update = False
        
        st.session_state.local_tasks = local_tasks
    
    return action, was_update

def update_task(task_id, new_task):
    """Update task by ID"""
    if conn:
        execute_query(
            "UPDATE tasks SET task = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
            (new_task, task_id)
        )
    else:
        # Fallback to session state
        for task in st.session_state.get('local_tasks', []):
            if str(task.get("id")) == task_id:
                task["task"] = new_task
                task["updated_at"] = datetime.now().isoformat()
                break

def delete_task(task_id):
    """Delete task by ID"""
    if conn:
        execute_query("DELETE FROM tasks WHERE id = %s", (task_id,))
    else:
        # Fallback to session state
        local_tasks = st.session_state.get('local_tasks', [])
        st.session_state.local_tasks = [
            task for task in local_tasks 
            if str(task.get("id")) != task_id
        ]

def get_tasks_sorted_by_day(start_date):
    """Get all tasks sorted by day number"""
    if conn:
        tasks = execute_query(
            "SELECT id, task_date, task FROM tasks ORDER BY task_date",
            fetch=True
        )
        tasks = [dict(task) for task in tasks] if tasks else []
    else:
        # Fallback to session state
        tasks = st.session_state.get('local_tasks', [])
        tasks = sorted(tasks, key=lambda x: x.get("task_date", ""))
    
    if not tasks:
        return []
    
    # Get start date
    start_date_str = get_setting("start_date")
    
    # Calculate day numbers
    tasks_with_days = []
    for task in tasks:
        task_date = task.get("task_date")
        if isinstance(task_date, str):
            task_date = date.fromisoformat(task_date)
        
        # Calculate day number
        day_number = None
        if start_date_str:
            try:
                start_date_obj = date.fromisoformat(start_date_str)
                day_num = (task_date - start_date_obj).days + 1
                if day_num > 0:
                    day_number = day_num
            except:
                pass
        
        if day_number:
            tasks_with_days.append({
                "day_number": day_number,
                "date": task_date.isoformat() if isinstance(task_date, date) else task_date,
                "formatted_date": task_date.strftime("%A, %d %B %Y") if isinstance(task_date, date) else date.fromisoformat(task_date).strftime("%A, %d %B %Y"),
                "task": task.get("task", ""),
                "id": str(task.get("id", ""))
            })
    
    # Sort by day number
    tasks_with_days.sort(key=lambda x: x["day_number"])
    return tasks_with_days

def get_tasks_for_download(start_date):
    """Get all tasks for download with day numbers"""
    tasks_with_days = get_tasks_sorted_by_day(start_date)
    
    if not tasks_with_days:
        return None
    
    # Create DataFrame
    data = []
    for task in tasks_with_days:
        data.append({
            "Day Number": task["day_number"],
            "Date": task["formatted_date"],
            "Task": task["task"]
        })
    
    df = pd.DataFrame(data)
    return df

def create_csv_download(df):
    """Create CSV file for download"""
    output = io.StringIO()
    df.to_csv(output, index=False)
    return output.getvalue().encode('utf-8')

def create_excel_download(df):
    """Create Excel file for download (if openpyxl is available)"""
    try:
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

def get_task_count():
    """Get total task count"""
    if conn:
        result = execute_query("SELECT COUNT(*) as count FROM tasks", fetch=True)
        return result[0]['count'] if result else 0
    else:
        return len(st.session_state.get('local_tasks', []))

def get_active_days():
    """Get count of distinct task dates"""
    if conn:
        result = execute_query("SELECT COUNT(DISTINCT task_date) as count FROM tasks", fetch=True)
        return result[0]['count'] if result else 0
    else:
        dates = set(task.get("task_date") for task in st.session_state.get('local_tasks', []))
        return len(dates)

def get_setting(key):
    """Get a setting value"""
    if conn:
        result = execute_query(
            "SELECT setting_value FROM settings WHERE setting_key = %s",
            (key,),
            fetch=True
        )
        return result[0]['setting_value'] if result else None
    else:
        return st.session_state.get('local_settings', {}).get(key)

def save_setting(key, value):
    """Save a setting value"""
    if conn:
        execute_query(
            """
            INSERT INTO settings (setting_key, setting_value) 
            VALUES (%s, %s)
            ON CONFLICT (setting_key) DO UPDATE 
            SET setting_value = EXCLUDED.setting_value, updated_at = CURRENT_TIMESTAMP
            """,
            (key, value)
        )
    else:
        local_settings = st.session_state.get('local_settings', {})
        local_settings[key] = value
        st.session_state.local_settings = local_settings

def authenticate_user(username, password):
    """Authenticate user"""
    if conn:
        result = execute_query(
            "SELECT username, role FROM users WHERE username = %s AND password = %s",
            (username, password),
            fetch=True
        )
        return result[0] if result else None
    else:
        # Fallback: Check against USERS dictionary
        if username in USERS and USERS[username] == password:
            return {
                "username": username,
                "role": "admin" if username == "admin" else "viewer"
            }
        return None

# Initialize session state for fallback
if 'local_tasks' not in st.session_state:
    st.session_state.local_tasks = []
if 'local_settings' not in st.session_state:
    st.session_state.local_settings = {}

# ---------------- LOGIN ----------------
def login():
    st.title("🔐 Login")
    
    # Database status indicator
    db_class = "db-postgres" if conn else "db-local"
    db_text = "PostgreSQL (Neon) ✓" if conn else "Local Storage"
    
    st.markdown(f"""
    <div style="text-align: center; margin-bottom: 20px;">
        <span class="db-status {db_class}">{db_text}</span>
    </div>
    """, unsafe_allow_html=True)
    
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
                    user = authenticate_user(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user["username"]
                        st.session_state.role = user["role"]
                        st.success("Login Successful")
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
            
            with col_btn2:
                if st.button("🔄 Clear", use_container_width=True):
                    st.rerun()
            
            # User information
            st.markdown("---")
            st.markdown("""
            **Available Users:**
            - **admin** (password: admin@asmath) - Full access
            - **admin2** (password: admin@AHBETA) - Report view only
            """)
            
            st.markdown('</div>', unsafe_allow_html=True)

# ---------------- REPORT VIEW (for admin2/viewer) ----------------
def report_view():
    """View for admin2 - shows reports in day order only"""
    st.title("📊 Internship Reports")
    
    # User info with role badge
    role_class = "role-viewer"
    role_text = "Report Viewer"
    
    col_title, col_user = st.columns([3, 1])
    with col_title:
        st.markdown(f"""
        <div>
            <h1 style="display: inline;">📊 Internship Reports</h1>
            <span class="role-badge {role_class}">{role_text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_user:
        st.markdown(f"""
        <div style="text-align: right; padding: 10px;">
            👤 <strong>{st.session_state.username}</strong><br>
            <small>{date.today().strftime('%d %b %Y')}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Database status
    db_class = "db-postgres" if conn else "db-local"
    db_text = "PostgreSQL (Neon) ✓" if conn else "Local Storage"
    st.markdown(f'<div style="text-align: center;"><span class="db-status {db_class}">{db_text}</span></div>', 
               unsafe_allow_html=True)
    
    # Get start date for day calculation
    start_date_str = get_setting("start_date")
    if not start_date_str:
        st.warning("⚠️ Start date not set. Please ask admin to set the internship start date.")
        # Logout button
        st.divider()
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.pop('username', None)
            st.session_state.pop('role', None)
            st.rerun()
        return
    
    start_date = date.fromisoformat(start_date_str)
    
    # Get tasks sorted by day
    tasks_with_days = get_tasks_sorted_by_day(start_date)
    
    if not tasks_with_days:
        st.info("📭 No tasks found yet. Tasks will appear here once added by admin.")
        # Logout button
        st.divider()
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.pop('username', None)
            st.session_state.pop('role', None)
            st.rerun()
        return
    
    # Statistics
    col_stat1, col_stat2 = st.columns(2)
    with col_stat1:
        st.metric("Total Days with Tasks", len(tasks_with_days))
    
    with col_stat2:
        current_day = (date.today() - start_date).days + 1
        if current_day > 0:
            st.metric("Current Day", current_day)
        else:
            st.metric("Internship Start", "Not started")
    
    # Report Header
    st.divider()
    st.markdown(f"""
    <div class="report-view">
        <h3>📋 Internship Progress Report</h3>
        <p>Start Date: {start_date.strftime('%d %B %Y')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Display tasks grouped by day
    st.subheader("📅 Daily Tasks (Sorted by Day Number)")
    
    # Filter options
    col_filter1, col_filter2 = st.columns(2)
    with col_filter1:
        min_day = min(task["day_number"] for task in tasks_with_days)
        max_day = max(task["day_number"] for task in tasks_with_days)
        selected_range = st.slider(
            "Select Day Range",
            min_value=min_day,
            max_value=max_day,
            value=(min_day, max_day)
        )
    
    with col_filter2:
        search_term = st.text_input("🔍 Search in tasks", placeholder="Type to search...")
    
    # Filter tasks
    filtered_tasks = [
        task for task in tasks_with_days 
        if selected_range[0] <= task["day_number"] <= selected_range[1]
        and (not search_term or search_term.lower() in task["task"].lower())
    ]
    
    if filtered_tasks:
        # Display tasks
        for task in filtered_tasks:
            with st.container():
                st.markdown(f"""
                <div class="report-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <div>
                            <span style="background: #4CAF50; color: white; padding: 3px 10px; border-radius: 15px; font-weight: bold;">
                                Day {task['day_number']}
                            </span>
                            <span style="margin-left: 10px; color: #666;">
                                {task['formatted_date']}
                            </span>
                        </div>
                    </div>
                    <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; border-left: 3px solid #2196F3;">
                        {task['task']}
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No tasks found matching the selected criteria.")
    
    # Download Section
    st.divider()
    st.subheader("📥 Download Reports")
    
    col_download1, col_download2 = st.columns([2, 1])
    
    with col_download1:
        st.info("Download your internship reports in various formats.")
    
    with col_download2:
        # Create download data
        df = get_tasks_for_download(start_date)
        
        if df is not None and not df.empty:
            # Create download buttons
            col_csv, col_excel = st.columns(2)
            
            with col_csv:
                # CSV Download
                csv_data = create_csv_download(df)
                st.download_button(
                    label="📥 CSV Report",
                    data=csv_data,
                    file_name=f"internship_report_{date.today().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="csv_report"
                )
            
            with col_excel:
                # Excel Download (if available)
                excel_data, excel_available = create_excel_download(df)
                if excel_available and excel_data:
                    st.download_button(
                        label="📊 Excel Report",
                        data=excel_data,
                        file_name=f"internship_report_{date.today().strftime('%Y%m%d')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True,
                        key="excel_report"
                    )
                else:
                    # Show info about Excel export
                    st.info("Excel: Install openpyxl")
        else:
            st.warning("No reports available for download")
    
    # Logout button
    st.divider()
    if st.button("🚪 Logout", type="secondary", use_container_width=True):
        st.session_state.logged_in = False
        st.session_state.pop('username', None)
        st.session_state.pop('role', None)
        st.rerun()

# ---------------- ADMIN VIEW (for admin) ----------------
def admin_view():
    """Full admin view with all features"""
    # Header with user info and role badge
    role_class = "role-admin"
    role_text = "Administrator"
    
    col_title, col_user = st.columns([3, 1])
    with col_title:
        st.title("📅 Internship Tracker")
        st.markdown(f'<span class="role-badge {role_class}">{role_text}</span>', 
                   unsafe_allow_html=True)
    
    with col_user:
        st.markdown(f"""
        <div style="text-align: right; padding: 10px;">
            👤 <strong>{st.session_state.username}</strong><br>
            <small>{date.today().strftime('%d %b %Y')}</small>
        </div>
        """, unsafe_allow_html=True)
    
    # Database status
    db_class = "db-postgres" if conn else "db-local"
    db_text = "PostgreSQL (Neon) ✓" if conn else "Local Storage"
    st.markdown(f'<div style="text-align: center;"><span class="db-status {db_class}">{db_text}</span></div>', 
               unsafe_allow_html=True)
    
    # Start date configuration
    st.subheader("📅 Settings")
    
    start_date_str = get_setting("start_date")
    start_date_value = date.today()
    if start_date_str:
        start_date_value = date.fromisoformat(start_date_str)
    
    start_date = st.date_input(
        "🎯 Internship Start Date",
        value=start_date_value,
        help="Set the start date of your internship"
    )
    
    col_save, col_info = st.columns([1, 3])
    with col_save:
        if st.button("💾 Save Date", use_container_width=True, key="save_date"):
            save_setting("start_date", start_date.isoformat())
            st.success("Start date saved successfully!")
            st.rerun()
    
    with col_info:
        if start_date_str:
            st.info(f"Current start date: {start_date_str}")
    
    # Progress metrics
    st.divider()
    st.subheader("📊 Progress Overview")
    
    completed = (date.today() - start_date).days
    remaining = TOTAL_DAYS - completed
    progress = min(max(completed, 0) / TOTAL_DAYS, 1) * 100
    
    # Progress bar with animation
    st.progress(progress / 100)
    
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
            <h3 style="margin:0; color:#2196F3;">{max(completed, 0)}</h3>
            <p style="margin:0; color:#666;">Completed Days</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card" style="border-left-color:#FF9800;">
            <h3 style="margin:0; color:#FF9800;">{max(remaining, 0)}</h3>
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
    default_task = existing_task.get("task") if existing_task else ""
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
        task_count = get_task_count()
        
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
                        # Show info about Excel export
                        st.info("Excel: Install openpyxl")
            else:
                st.warning("No tasks to download")
        else:
            st.warning("No tasks available for download")
    
    # Task History
    st.divider()
    st.subheader("📚 Task History")
    
    # Quick navigation to report view
    st.info("💡 **Tip:** Use 'admin2' account (password: admin@AHBETA) to view reports in day order.")
    
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
    if conn:
        query = "SELECT id, task_date, task FROM tasks"
        params = []
        if st.session_state.filter_date:
            query += " WHERE task_date = %s"
            params.append(st.session_state.filter_date)
        query += " ORDER BY task_date DESC LIMIT %s"
        params.append(limit)
        
        tasks = execute_query(query, params, fetch=True)
        tasks = [dict(task) for task in tasks] if tasks else []
    else:
        # Fallback to session state
        tasks = st.session_state.get('local_tasks', [])
        
        # Apply filter
        if st.session_state.filter_date:
            filter_date_str = st.session_state.filter_date.isoformat()
            tasks = [task for task in tasks if task.get("task_date") == filter_date_str]
        
        # Sort and limit
        tasks = sorted(tasks, key=lambda x: x.get("task_date", ""), reverse=True)[:limit]
    
    if tasks:
        for task in tasks:
            task_id = str(task.get("id", ""))
            task_date_str = task.get("task_date", "")
            task_text = task.get("task", "")
            
            if not task_date_str:
                continue
            
            # Convert to date object if needed
            if isinstance(task_date_str, str):
                task_date_display = date.fromisoformat(task_date_str)
            else:
                task_date_display = task_date_str
            
            # Calculate day number if start date exists
            day_number = ""
            start_date_str = get_setting("start_date")
            if start_date_str:
                try:
                    start_date_for_calc = date.fromisoformat(start_date_str)
                    if isinstance(task_date_display, str):
                        task_date_for_calc = date.fromisoformat(task_date_display)
                    else:
                        task_date_for_calc = task_date_display
                    
                    day_num = (task_date_for_calc - start_date_for_calc).days + 1
                    if day_num > 0:
                        day_number = f"Day {day_num} • "
                except:
                    pass
            
            # Display each task in a card
            with st.container():
                col1, col2 = st.columns([4, 1])
                with col1:
                    date_str = task_date_display.isoformat() if isinstance(task_date_display, date) else task_date_display
                    st.markdown(f"""
                    <div class="task-card">
                        <div style="color: #666; font-size: 0.9em; margin-bottom: 4px;">
                            {day_number}📅 {date_str}
                        </div>
                        <p style="margin: 0; line-height: 1.5;">{task_text}</p>
                    </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    # Edit button
                    if st.button("✏️ Edit", key=f"edit_btn_{task_id}", use_container_width=True):
                        if isinstance(task_date_display, date):
                            st.session_state.selected_date = task_date_display
                        else:
                            st.session_state.selected_date = date.fromisoformat(task_date_display)
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
    
    total_tasks = get_task_count()
    active_days = get_active_days()
    
    col_stat1, col_stat2, col_stat3 = st.columns(3)
    with col_stat1:
        st.metric("Total Tasks", total_tasks)
    
    with col_stat2:
        st.metric("Active Days", active_days)
    
    with col_stat3:
        current_day = (date.today() - start_date).days + 1
        if current_day > 0:
            st.metric("Current Day", current_day)
        else:
            st.metric("Internship Start", "Not started")
    
    # Database Management (for PostgreSQL only)
    if conn:
        st.divider()
        st.subheader("🗄️ Database Management")
        
        col_db1, col_db2 = st.columns(2)
        
        with col_db1:
            if st.button("🗑️ Clear All Tasks", type="secondary", use_container_width=True):
                if st.checkbox("Confirm delete all tasks"):
                    execute_query("DELETE FROM tasks")
                    st.success("All tasks deleted!")
                    st.rerun()
        
        with col_db2:
            if st.button("📊 Show Database Stats", use_container_width=True):
                user_count = execute_query("SELECT COUNT(*) as count FROM users", fetch=True)[0]['count']
                task_count = execute_query("SELECT COUNT(*) as count FROM tasks", fetch=True)[0]['count']
                
                st.info(f"""
                **Database Statistics:**
                - Users: {user_count}
                - Tasks: {task_count}
                - Database: PostgreSQL (Neon)
                """)
    
    # Logout button
    st.divider()
    col_logout, _ = st.columns([1, 3])
    with col_logout:
        if st.button("🚪 Logout", type="secondary", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.pop('username', None)
            st.session_state.pop('role', None)
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
    if "role" not in st.session_state:
        st.session_state.role = None
    
    # Route based on login status and role
    if not st.session_state.logged_in:
        login()
    else:
        if st.session_state.role == "viewer" or st.session_state.username == "admin2":
            report_view()  # Show report-only view for admin2
        else:
            admin_view()  # Show full admin view for admin
