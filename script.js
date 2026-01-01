// Database Configuration
const DB_NAME = 'InternshipTrackerDB';
const DB_VERSION = 1;
const STORES = {
    USERS: 'users',
    TASKS: 'tasks',
    SETTINGS: 'settings'
};

// Constants
const TOTAL_DAYS = 548;
const USERS = {
    'admin': { password: 'admin@asmath', role: 'admin' },
    'admin2': { password: 'admin@AHBETA', role: 'viewer' }
};

// Global Variables
let db = null;
let currentUser = null;
let currentRole = null;
let currentTaskId = null;
let selectedDate = new Date();
let filterDate = null;
let tasksLimit = 20;

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initializeDatabase();
    setupEventListeners();
    updateCurrentDate();
});

// Database Functions
function initializeDatabase() {
    const request = indexedDB.open(DB_NAME, DB_VERSION);

    request.onerror = (event) => {
        console.error('Database error:', event.target.error);
        showToast('Database initialization failed!', 'error');
    };

    request.onupgradeneeded = (event) => {
        const db = event.target.result;

        // Create users store
        if (!db.objectStoreNames.contains(STORES.USERS)) {
            const usersStore = db.createObjectStore(STORES.USERS, { keyPath: 'username' });
            usersStore.createIndex('username', 'username', { unique: true });
        }

        // Create tasks store
        if (!db.objectStoreNames.contains(STORES.TASKS)) {
            const tasksStore = db.createObjectStore(STORES.TASKS, { keyPath: 'id', autoIncrement: true });
            tasksStore.createIndex('date', 'date', { unique: true });
            tasksStore.createIndex('dayNumber', 'dayNumber');
        }

        // Create settings store
        if (!db.objectStoreNames.contains(STORES.SETTINGS)) {
            const settingsStore = db.createObjectStore(STORES.SETTINGS, { keyPath: 'key' });
            settingsStore.createIndex('key', 'key', { unique: true });
        }
    };

    request.onsuccess = (event) => {
        db = event.target.result;
        console.log('Database initialized successfully');
        initializeDefaultData();
        showToast('Database connected successfully!', 'success');
    };
}

function initializeDefaultData() {
    // Initialize default users
    Object.entries(USERS).forEach(([username, userData]) => {
        addUser(username, userData.password, userData.role);
    });

    // Initialize default settings
    setSetting('startDate', new Date().toISOString().split('T')[0]);
}

// CRUD Operations
function addUser(username, password, role) {
    const transaction = db.transaction([STORES.USERS], 'readwrite');
    const store = transaction.objectStore(STORES.USERS);
    
    const user = {
        username: username,
        password: password,
        role: role,
        createdAt: new Date().toISOString()
    };

    const request = store.put(user);

    request.onsuccess = () => {
        console.log(`User ${username} added/updated`);
    };

    request.onerror = (event) => {
        console.error('Error adding user:', event.target.error);
    };
}

async function getUser(username) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.USERS], 'readonly');
        const store = transaction.objectStore(STORES.USERS);
        const request = store.get(username);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function authenticateUser(username, password) {
    const user = await getUser(username);
    if (user && user.password === password) {
        return user;
    }
    return null;
}

// Task Operations
async function addOrUpdateTask(date, task) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readwrite');
        const store = transaction.objectStore(STORES.TASKS);
        const dateIndex = store.index('date');
        
        // Check if task exists for this date
        const request = dateIndex.get(date);

        request.onsuccess = () => {
            const existingTask = request.result;
            
            if (existingTask) {
                // Update existing task
                existingTask.task = task;
                existingTask.updatedAt = new Date().toISOString();
                
                const updateRequest = store.put(existingTask);
                updateRequest.onsuccess = () => resolve({ action: 'updated', task: existingTask });
                updateRequest.onerror = () => reject(updateRequest.error);
            } else {
                // Add new task
                const startDate = getSetting('startDate');
                const dayNumber = calculateDayNumber(date, startDate);
                
                const newTask = {
                    date: date,
                    task: task,
                    dayNumber: dayNumber,
                    createdAt: new Date().toISOString(),
                    updatedAt: new Date().toISOString()
                };

                const addRequest = store.add(newTask);
                addRequest.onsuccess = () => resolve({ action: 'added', task: newTask });
                addRequest.onerror = () => reject(addRequest.error);
            }
        };

        request.onerror = () => reject(request.error);
    });
}

async function getTaskByDate(date) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readonly');
        const store = transaction.objectStore(STORES.TASKS);
        const dateIndex = store.index('date');
        const request = dateIndex.get(date);

        request.onsuccess = () => resolve(request.result);
        request.onerror = () => reject(request.error);
    });
}

async function getAllTasks(filterDate = null) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readonly');
        const store = transaction.objectStore(STORES.TASKS);
        const request = store.getAll();

        request.onsuccess = () => {
            let tasks = request.result;
            
            if (filterDate) {
                tasks = tasks.filter(task => task.date === filterDate);
            }
            
            // Sort by date descending
            tasks.sort((a, b) => new Date(b.date) - new Date(a.date));
            resolve(tasks);
        };

        request.onerror = () => reject(request.error);
    });
}

async function getTasksByDayOrder() {
    const tasks = await getAllTasks();
    const startDate = getSetting('startDate');
    
    // Calculate day numbers and filter valid tasks
    const tasksWithDays = tasks.map(task => {
        const dayNumber = calculateDayNumber(task.date, startDate);
        return { ...task, dayNumber };
    }).filter(task => task.dayNumber > 0);
    
    // Sort by day number
    tasksWithDays.sort((a, b) => a.dayNumber - b.dayNumber);
    return tasksWithDays;
}

async function updateTask(id, task) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readwrite');
        const store = transaction.objectStore(STORES.TASKS);
        
        const getRequest = store.get(Number(id));
        
        getRequest.onsuccess = () => {
            const existingTask = getRequest.result;
            if (existingTask) {
                existingTask.task = task;
                existingTask.updatedAt = new Date().toISOString();
                
                const updateRequest = store.put(existingTask);
                updateRequest.onsuccess = () => resolve(true);
                updateRequest.onerror = () => reject(updateRequest.error);
            } else {
                reject(new Error('Task not found'));
            }
        };
        
        getRequest.onerror = () => reject(getRequest.error);
    });
}

async function deleteTask(id) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readwrite');
        const store = transaction.objectStore(STORES.TASKS);
        const request = store.delete(Number(id));

        request.onsuccess = () => resolve(true);
        request.onerror = () => reject(request.error);
    });
}

async function clearAllTasks() {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.TASKS], 'readwrite');
        const store = transaction.objectStore(STORES.TASKS);
        const request = store.clear();

        request.onsuccess = () => resolve(true);
        request.onerror = () => reject(request.error);
    });
}

async function getTaskCount() {
    const tasks = await getAllTasks();
    return tasks.length;
}

async function getActiveDays() {
    const tasks = await getAllTasks();
    const uniqueDates = new Set(tasks.map(task => task.date));
    return uniqueDates.size;
}

// Settings Operations
function setSetting(key, value) {
    const transaction = db.transaction([STORES.SETTINGS], 'readwrite');
    const store = transaction.objectStore(STORES.SETTINGS);
    
    const setting = {
        key: key,
        value: value,
        updatedAt: new Date().toISOString()
    };

    store.put(setting);
}

async function getSetting(key) {
    return new Promise((resolve, reject) => {
        const transaction = db.transaction([STORES.SETTINGS], 'readonly');
        const store = transaction.objectStore(STORES.SETTINGS);
        const request = store.get(key);

        request.onsuccess = () => resolve(request.result ? request.result.value : null);
        request.onerror = () => reject(request.error);
    });
}

// Helper Functions
function calculateDayNumber(date, startDate) {
    if (!startDate) return 0;
    
    const taskDate = new Date(date);
    const internshipStart = new Date(startDate);
    
    const diffTime = taskDate - internshipStart;
    const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24)) + 1;
    
    return diffDays > 0 ? diffDays : 0;
}

function calculateProgress(startDate) {
    const today = new Date();
    const start = new Date(startDate);
    
    const completed = Math.floor((today - start) / (1000 * 60 * 60 * 24));
    const remaining = TOTAL_DAYS - completed;
    const progress = Math.min(Math.max(completed, 0) / TOTAL_DAYS, 1) * 100;
    
    return {
        completed: Math.max(completed, 0),
        remaining: Math.max(remaining, 0),
        progress: progress
    };
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    return date.toLocaleDateString('en-US', options);
}

function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastIcon = toast.querySelector('.toast-icon');
    const toastMessage = toast.querySelector('.toast-message');
    
    // Set icon based on type
    let iconClass = 'fas fa-info-circle';
    switch (type) {
        case 'success':
            iconClass = 'fas fa-check-circle';
            break;
        case 'error':
            iconClass = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            iconClass = 'fas fa-exclamation-triangle';
            break;
    }
    
    toastIcon.className = `toast-icon ${iconClass}`;
    toastMessage.textContent = message;
    toast.className = `toast ${type} active`;
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

function showModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.add('active');
}

function hideModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('active');
}

function updateCurrentDate() {
    const today = new Date();
    const dateString = today.toLocaleDateString('en-US', { 
        weekday: 'short', 
        year: 'numeric', 
        month: 'short', 
        day: 'numeric' 
    });
    
    document.getElementById('current-date').textContent = dateString;
    document.getElementById('report-date').textContent = dateString;
}

function updateProgress(startDate) {
    const progress = calculateProgress(startDate);
    
    // Update progress bar
    const progressFill = document.getElementById('progress-fill');
    const progressText = document.getElementById('progress-text');
    
    progressFill.style.width = `${progress.progress}%`;
    progressText.textContent = `${Math.round(progress.progress)}%`;
    
    // Update metrics
    document.getElementById('completed-days').textContent = progress.completed;
    document.getElementById('remaining-days').textContent = progress.remaining;
}

// UI Update Functions
async function updateAdminDashboard() {
    const startDate = await getSetting('startDate');
    
    // Update date input
    if (startDate) {
        document.getElementById('start-date').value = startDate;
        document.getElementById('date-info').innerHTML = `
            <i class="fas fa-info-circle"></i>
            Current start date: ${formatDate(startDate)}
        `;
    }
    
    // Update progress
    if (startDate) {
        updateProgress(startDate);
    }
    
    // Update task date
    const taskDateInput = document.getElementById('task-date');
    taskDateInput.value = selectedDate.toISOString().split('T')[0];
    
    // Check if date has task
    const existingTask = await getTaskByDate(taskDateInput.value);
    const warningBox = document.getElementById('date-warning');
    const saveBtn = document.getElementById('save-task');
    
    if (existingTask) {
        warningBox.style.display = 'flex';
        document.getElementById('task-description').value = existingTask.task;
        saveBtn.innerHTML = '<i class="fas fa-sync-alt"></i> Update Task';
    } else {
        warningBox.style.display = 'none';
        document.getElementById('task-description').value = '';
        saveBtn.innerHTML = '<i class="fas fa-save"></i> Save Task';
    }
    
    // Update task list
    await updateTaskList();
    
    // Update statistics
    updateStatistics();
}

async function updateTaskList() {
    const tasksContainer = document.getElementById('tasks-container');
    const noTasks = document.getElementById('no-tasks');
    
    let tasks = await getAllTasks(filterDate);
    tasks = tasks.slice(0, tasksLimit);
    
    if (tasks.length === 0) {
        tasksContainer.innerHTML = '';
        noTasks.style.display = 'block';
        return;
    }
    
    noTasks.style.display = 'none';
    tasksContainer.innerHTML = '';
    
    const startDate = await getSetting('startDate');
    
    tasks.forEach(task => {
        const dayNumber = calculateDayNumber(task.date, startDate);
        const dayDisplay = dayNumber > 0 ? `<span class="day-badge">Day ${dayNumber}</span>` : '';
        
        const taskElement = document.createElement('div');
        taskElement.className = 'task-item';
        taskElement.innerHTML = `
            <div class="task-content">
                <div class="task-date">
                    ${dayDisplay}
                    <i class="fas fa-calendar"></i> ${task.date}
                </div>
                <div class="task-text">${task.task}</div>
            </div>
            <div class="task-actions">
                <button class="btn btn-secondary btn-edit" data-id="${task.id}">
                    <i class="fas fa-edit"></i> Edit
                </button>
            </div>
        `;
        
        tasksContainer.appendChild(taskElement);
    });
    
    // Add event listeners to edit buttons
    document.querySelectorAll('.btn-edit').forEach(button => {
        button.addEventListener('click', async (e) => {
            const taskId = e.currentTarget.getAttribute('data-id');
            await openEditModal(taskId);
        });
    });
}

async function updateReportDashboard() {
    const startDate = await getSetting('startDate');
    
    if (startDate) {
        document.getElementById('report-start-date').textContent = `Start Date: ${formatDate(startDate)}`;
        
        // Update current day
        const progress = calculateProgress(startDate);
        document.getElementById('report-current-day').textContent = progress.completed > 0 ? progress.completed : 'Not started';
    }
    
    // Update tasks in report view
    await updateReportTasks();
}

async function updateReportTasks() {
    const tasksContainer = document.getElementById('report-tasks-container');
    const noTasks = document.getElementById('no-report-tasks');
    
    let tasks = await getTasksByDayOrder();
    
    if (tasks.length === 0) {
        tasksContainer.innerHTML = '';
        noTasks.style.display = 'block';
        return;
    }
    
    noTasks.style.display = 'none';
    
    // Get filter values
    const minDay = parseInt(document.getElementById('day-range-min').value);
    const maxDay = parseInt(document.getElementById('day-range-max').value);
    const searchTerm = document.getElementById('search-tasks').value.toLowerCase();
    
    // Update range display
    document.getElementById('range-min').textContent = `Day ${minDay}`;
    document.getElementById('range-max').textContent = `Day ${maxDay}`;
    
    // Filter tasks
    const filteredTasks = tasks.filter(task => {
        const dayMatch = task.dayNumber >= minDay && task.dayNumber <= maxDay;
        const searchMatch = !searchTerm || task.task.toLowerCase().includes(searchTerm);
        return dayMatch && searchMatch;
    });
    
    // Update statistics
    document.getElementById('report-days').textContent = filteredTasks.length;
    
    // Display tasks
    tasksContainer.innerHTML = '';
    
    filteredTasks.forEach(task => {
        const taskElement = document.createElement('div');
        taskElement.className = 'report-task-item';
        taskElement.innerHTML = `
            <div class="report-task-header">
                <div class="day-badge">Day ${task.dayNumber}</div>
                <div class="report-task-date">${formatDate(task.date)}</div>
            </div>
            <div class="report-task-content">${task.task}</div>
        `;
        
        tasksContainer.appendChild(taskElement);
    });
}

async function updateStatistics() {
    const totalTasks = await getTaskCount();
    const activeDays = await getActiveDays();
    const startDate = await getSetting('startDate');
    
    document.getElementById('total-tasks').textContent = totalTasks;
    document.getElementById('active-days').textContent = activeDays;
    
    if (startDate) {
        const progress = calculateProgress(startDate);
        document.getElementById('current-day').textContent = progress.completed > 0 ? progress.completed : 'Not started';
    }
}

async function openEditModal(taskId) {
    const transaction = db.transaction([STORES.TASKS], 'readonly');
    const store = transaction.objectStore(STORES.TASKS);
    const request = store.get(Number(taskId));
    
    request.onsuccess = () => {
        const task = request.result;
        if (task) {
            currentTaskId = taskId;
            document.getElementById('edit-task-date').value = task.date;
            document.getElementById('edit-task-description').value = task.task;
            showModal('edit-modal');
        }
    };
}

// Export Functions
function exportToCSV(tasks) {
    const headers = ['Day Number', 'Date', 'Task'];
    const csvContent = [
        headers.join(','),
        ...tasks.map(task => [
            task.dayNumber,
            `"${formatDate(task.date)}"`,
            `"${task.task.replace(/"/g, '""')}"`
        ].join(','))
    ].join('\n');
    
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `internship_report_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

function exportToJSON(tasks) {
    const jsonData = {
        exportDate: new Date().toISOString(),
        totalTasks: tasks.length,
        tasks: tasks.map(task => ({
            dayNumber: task.dayNumber,
            date: task.date,
            formattedDate: formatDate(task.date),
            task: task.task
        }))
    };
    
    const jsonString = JSON.stringify(jsonData, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json;charset=utf-8;' });
    const link = document.createElement('a');
    const url = URL.createObjectURL(blob);
    
    link.setAttribute('href', url);
    link.setAttribute('download', `internship_report_${new Date().toISOString().split('T')[0]}.json`);
    link.style.visibility = 'hidden';
    
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Event Listeners Setup
function setupEventListeners() {
    // Login screen
    document.getElementById('login-btn').addEventListener('click', handleLogin);
    document.getElementById('clear-btn').addEventListener('click', () => {
        document.getElementById('username').value = '';
        document.getElementById('password').value = '';
    });
    
    // Logout buttons
    document.getElementById('logout-admin').addEventListener('click', handleLogout);
    document.getElementById('logout-report').addEventListener('click', handleLogout);
    
    // Admin dashboard
    document.getElementById('save-date').addEventListener('click', handleSaveDate);
    document.getElementById('prev-day').addEventListener('click', () => navigateDate(-1));
    document.getElementById('today').addEventListener('click', () => navigateDate(0));
    document.getElementById('next-day').addEventListener('click', () => navigateDate(1));
    document.getElementById('save-task').addEventListener('click', handleSaveTask);
    document.getElementById('clear-form').addEventListener('click', () => {
        document.getElementById('task-description').value = '';
    });
    document.getElementById('view-date').addEventListener('click', handleViewDate);
    
    // Task date change
    document.getElementById('task-date').addEventListener('change', (e) => {
        selectedDate = new Date(e.target.value);
        updateAdminDashboard();
    });
    
    // Filter controls
    document.getElementById('filter-date').addEventListener('change', async (e) => {
        filterDate = e.target.value || null;
        await updateTaskList();
    });
    
    document.getElementById('task-limit').addEventListener('input', async (e) => {
        tasksLimit = parseInt(e.target.value);
        document.getElementById('limit-value').textContent = tasksLimit;
        await updateTaskList();
    });
    
    document.getElementById('clear-filter').addEventListener('click', () => {
        document.getElementById('filter-date').value = '';
        filterDate = null;
        updateTaskList();
    });
    
    // Export buttons
    document.getElementById('export-csv').addEventListener('click', async () => {
        const tasks = await getTasksByDayOrder();
        if (tasks.length > 0) {
            exportToCSV(tasks);
            showToast('CSV exported successfully!', 'success');
        } else {
            showToast('No tasks to export', 'warning');
        }
    });
    
    document.getElementById('export-json').addEventListener('click', async () => {
        const tasks = await getTasksByDayOrder();
        if (tasks.length > 0) {
            exportToJSON(tasks);
            showToast('JSON exported successfully!', 'success');
        } else {
            showToast('No tasks to export', 'warning');
        }
    });
    
    // Report export buttons
    document.getElementById('export-report-csv').addEventListener('click', async () => {
        const tasks = await getTasksByDayOrder();
        if (tasks.length > 0) {
            exportToCSV(tasks);
            showToast('CSV report exported successfully!', 'success');
        } else {
            showToast('No tasks to export', 'warning');
        }
    });
    
    document.getElementById('export-report-json').addEventListener('click', async () => {
        const tasks = await getTasksByDayOrder();
        if (tasks.length > 0) {
            exportToJSON(tasks);
            showToast('JSON report exported successfully!', 'success');
        } else {
            showToast('No tasks to export', 'warning');
        }
    });
    
    // Database management
    document.getElementById('clear-db').addEventListener('click', () => {
        showConfirmModal('Are you sure you want to delete all tasks? This action cannot be undone.', handleClearAllTasks);
    });
    
    document.getElementById('db-info').addEventListener('click', showDatabaseInfo);
    document.getElementById('backup-db').addEventListener('click', handleBackupDatabase);
    
    // Report filters
    document.getElementById('day-range-min').addEventListener('input', updateReportTasks);
    document.getElementById('day-range-max').addEventListener('input', updateReportTasks);
    document.getElementById('search-tasks').addEventListener('input', updateReportTasks);
    
    // Modals
    document.querySelectorAll('.close-modal').forEach(button => {
        button.addEventListener('click', () => {
            button.closest('.modal').classList.remove('active');
        });
    });
    
    // Edit modal buttons
    document.getElementById('save-edit').addEventListener('click', handleSaveEdit);
    document.getElementById('delete-task').addEventListener('click', handleDeleteTask);
    document.getElementById('cancel-edit').addEventListener('click', () => hideModal('edit-modal'));
    
    // Confirm modal
    document.getElementById('confirm-yes').addEventListener('click', () => {
        const callback = window.confirmCallback;
        if (callback) callback();
        hideModal('confirm-modal');
    });
    
    document.getElementById('confirm-no').addEventListener('click', () => {
        hideModal('confirm-modal');
    });
    
    // Close modals on outside click
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.remove('active');
            }
        });
    });
}

// Event Handlers
async function handleLogin() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    
    if (!username || !password) {
        showToast('Please enter username and password', 'warning');
        return;
    }
    
    const user = await authenticateUser(username, password);
    
    if (user) {
        currentUser = user.username;
        currentRole = user.role;
        
        // Switch to appropriate dashboard
        document.getElementById('login-screen').classList.remove('active');
        
        if (currentRole === 'admin') {
            document.getElementById('admin-dashboard').classList.add('active');
            document.getElementById('current-user').textContent = currentUser;
            updateAdminDashboard();
        } else {
            document.getElementById('report-dashboard').classList.add('active');
            document.getElementById('report-user').textContent = currentUser;
            updateReportDashboard();
        }
        
        showToast(`Welcome ${currentUser}!`, 'success');
    } else {
        showToast('Invalid username or password', 'error');
    }
}

function handleLogout() {
    currentUser = null;
    currentRole = null;
    
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    
    document.getElementById('login-screen').classList.add('active');
    
    // Clear form
    document.getElementById('username').value = '';
    document.getElementById('password').value = '';
    
    showToast('Logged out successfully', 'success');
}

async function handleSaveDate() {
    const startDate = document.getElementById('start-date').value;
    
    if (!startDate) {
        showToast('Please select a start date', 'warning');
        return;
    }
    
    await setSetting('startDate', startDate);
    await updateAdminDashboard();
    showToast('Start date saved successfully!', 'success');
}

function navigateDate(days) {
    selectedDate.setDate(selectedDate.getDate() + days);
    document.getElementById('task-date').value = selectedDate.toISOString().split('T')[0];
    updateAdminDashboard();
}

async function handleSaveTask() {
    const date = document.getElementById('task-date').value;
    const task = document.getElementById('task-description').value.trim();
    
    if (!task) {
        showToast('Please enter task description', 'warning');
        return;
    }
    
    try {
        const result = await addOrUpdateTask(date, task);
        showToast(`Task ${result.action} successfully!`, 'success');
        updateAdminDashboard();
    } catch (error) {
        showToast('Error saving task: ' + error.message, 'error');
    }
}

function handleViewDate() {
    const taskDate = document.getElementById('task-date').value;
    document.getElementById('filter-date').value = taskDate;
    filterDate = taskDate;
    updateTaskList();
}

async function handleSaveEdit() {
    const task = document.getElementById('edit-task-description').value.trim();
    
    if (!task) {
        showToast('Please enter task description', 'warning');
        return;
    }
    
    try {
        await updateTask(currentTaskId, task);
        showToast('Task updated successfully!', 'success');
        hideModal('edit-modal');
        updateAdminDashboard();
        if (currentRole === 'viewer') {
            updateReportDashboard();
        }
    } catch (error) {
        showToast('Error updating task: ' + error.message, 'error');
    }
}

async function handleDeleteTask() {
    try {
        await deleteTask(currentTaskId);
        showToast('Task deleted successfully!', 'success');
        hideModal('edit-modal');
        updateAdminDashboard();
        if (currentRole === 'viewer') {
            updateReportDashboard();
        }
    } catch (error) {
        showToast('Error deleting task: ' + error.message, 'error');
    }
}

async function handleClearAllTasks() {
    try {
        await clearAllTasks();
        showToast('All tasks deleted successfully!', 'success');
        updateAdminDashboard();
        if (currentRole === 'viewer') {
            updateReportDashboard();
        }
    } catch (error) {
        showToast('Error clearing tasks: ' + error.message, 'error');
    }
}

async function showDatabaseInfo() {
    const totalTasks = await getTaskCount();
    const activeDays = await getActiveDays();
    
    document.getElementById('info-tasks').textContent = totalTasks;
    document.getElementById('info-active-days').textContent = activeDays;
    
    showModal('info-modal');
}

function showConfirmModal(message, callback) {
    document.getElementById('confirm-message').textContent = message;
    window.confirmCallback = callback;
    showModal('confirm-modal');
}

function handleBackupDatabase() {
    // This would typically export all data
    // For simplicity, we'll export tasks as JSON
    getAllTasks().then(tasks => {
        if (tasks.length > 0) {
            exportToJSON(tasks.map(task => ({
                ...task,
                dayNumber: calculateDayNumber(task.date, getSetting('startDate'))
            })));
            showToast('Database backup created!', 'success');
        } else {
            showToast('No data to backup', 'warning');
        }
    });
}
