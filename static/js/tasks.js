// The edited code replaces the original `handleTaskSubmit` function entirely, adding a submission lock to prevent duplicate submissions.  The rest of the original functions remain unchanged, as they are not directly related to the form submission issue.  The changes consolidate task creation logic, add a submission lock, and remove duplicate event listeners.

// Handle task completion
async function handleTaskComplete(taskId) {
    try {
        const response = await fetch(`/api/tasks/${taskId}/complete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });

        if (!response.ok) {
            throw new Error('Failed to complete task');
        }

        const data = await response.json();
        const taskElement = document.getElementById(`task-${taskId}`);

        if (taskElement) {
            taskElement.classList.add('animate__fadeOut');

            setTimeout(() => {
                const completedContainer = document.querySelector('#completedTasksList');
                if (completedContainer) {
                    taskElement.classList.remove('animate__fadeOut');
                    taskElement.classList.add('completed', 'animate__fadeIn');

                    // Remove action buttons
                    const actionsDiv = taskElement.querySelector('.task-actions');
                    if (actionsDiv) {
                        actionsDiv.remove();
                    }

                    // Add completed text
                    const metaDiv = taskElement.querySelector('.task-meta');
                    if (metaDiv && !metaDiv.querySelector('.text-muted')) {
                        const completedText = document.createElement('small');
                        completedText.className = 'text-muted';
                        completedText.textContent = ' Completed';
                        metaDiv.appendChild(completedText);
                    }

                    completedContainer.insertBefore(taskElement, completedContainer.firstChild);
                }

                // Update stats and progress after UI changes
                Promise.all([updateProgressBar(), updateStats()]);
            }, 500);

            // Show EXP notification
            if (data.exp_gained) {
                showExpNotification(data.exp_gained);
            }
        }
    } catch (error) {
        console.error('Error completing task:', error);
    }
}

// Handle task deletion
async function handleTaskDelete(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) {
        return;
    }

    try {
        const response = await fetch(`/api/tasks/${taskId}/delete`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete task');
        }

        const taskElement = document.getElementById(`task-${taskId}`);
        if (taskElement) {
            taskElement.classList.add('animate__fadeOut');
            setTimeout(() => {
                taskElement.remove();
                // Update stats and progress after removal
                Promise.all([updateProgressBar(), updateStats()]);
            }, 500);
        }
    } catch (error) {
        console.error('Error deleting task:', error);
    }
}

// Update progress bar
async function updateProgressBar() {
    try {
        const response = await fetch('/api/tasks/stats');
        if (!response.ok) throw new Error('Failed to fetch task stats');

        const stats = await response.json();
        const progressBar = document.getElementById('progress-bar');
        const completedCount = document.getElementById('completed-tasks-count');

        if (progressBar && completedCount) {
            const percentage = stats.total > 0 ? (stats.completed / stats.total) * 100 : 0;
            progressBar.style.width = `${percentage}%`;
            completedCount.textContent = `${stats.completed}/${stats.total}`;
        }
    } catch (error) {
        console.error('Error updating progress bar:', error);
    }
}

// Update stats - using the improved implementation
async function updateStats() {
    try {
        // Skip API calls if we're already on the login page
        if (window.location.pathname === '/login') {
            return;
        }
        
        // Get responses in parallel
        const [taskResponse, userResponse] = await Promise.all([
            fetch('/api/tasks/stats'),
            fetch('/api/user/stats')
        ]);

        // Check for authentication errors
        if (taskResponse.status === 401 || userResponse.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (!taskResponse.ok || !userResponse.ok) {
            throw new Error('Failed to fetch stats');
        }

        const [taskStats, userStats] = await Promise.all([
            taskResponse.json(),
            userResponse.json()
        ]);

        // Check if we're on the leaderboard page
        const isLeaderboardPage = window.location.pathname === '/leaderboard';
        if (isLeaderboardPage) {
            return; // Skip updating ranks on leaderboard page
        }

        // Update all level displays
        document.querySelectorAll('[id="userLevel"], .level-info h4, .level-display h2').forEach(el => {
            el.textContent = userStats.level || 1;
        });

        // Update user rank badges
        document.querySelectorAll('[id="userRank"], .rank-badge span').forEach(el => {
            el.textContent = userStats.rank || 'E';
        });

        // Update exp displays
        document.querySelectorAll('[id="lifetimeExp"]').forEach(el => {
            el.textContent = userStats.exp || 0;
        });

        // Update progress bars with proper calculations
        // Progress to next level = (exp % 50) / 50
        const nextLevelProgress = userStats.exp ? 
            (userStats.exp % 50) / 50 * 100 : 0;
            
        // Update progress bar for exp
        const lifetimeExpProgress = document.getElementById('lifetimeExpProgress');
        if (lifetimeExpProgress) {
            lifetimeExpProgress.style.width = `${nextLevelProgress}%`;
        }
        
        // Update HP display if present
        const hpDisplay = document.getElementById('userHP');
        const maxHpDisplay = document.getElementById('userMaxHP');
        const hpProgressBar = document.getElementById('hpProgressBar');
        
        if (hpDisplay && userStats.hp !== undefined) {
            hpDisplay.textContent = userStats.hp;
        }
        
        if (maxHpDisplay && userStats.max_hp !== undefined) {
            maxHpDisplay.textContent = userStats.max_hp;
        }
        
        if (hpProgressBar && userStats.hp !== undefined && userStats.max_hp !== undefined) {
            const hpPercentage = (userStats.hp / userStats.max_hp) * 100;
            hpProgressBar.style.width = `${hpPercentage}%`;
        }
        
        // Update coins display if present
        const coinsDisplay = document.getElementById('userCoins');
        if (coinsDisplay && userStats.coins !== undefined) {
            coinsDisplay.textContent = userStats.coins;
        }
    } catch (error) {
        console.error('Error updating stats:', error);
    }
}

// Show EXP notification
function showExpNotification(expGained) {
    const notification = document.createElement('div');
    notification.className = 'exp-notification animate__animated animate__fadeInUp';
    notification.innerHTML = `
        <div class="exp-gain">
            <i data-feather="zap"></i>
            <span class="exp-text">+${expGained} EXP</span>
        </div>
    `;
    document.body.appendChild(notification);
    feather.replace();

    setTimeout(() => {
        notification.classList.remove('animate__fadeInUp');
        notification.classList.add('animate__fadeOutDown');
        setTimeout(() => notification.remove(), 1000);
    }, 2000);
}

// Show error dialog
function showErrorDialog(title, message) {
    const dialog = document.createElement('div');
    dialog.className = 'error-dialog animate__animated animate__fadeIn';
    dialog.innerHTML = `
        <div class="error-content">
            <h4>${title}</h4>
            <p>${message}</p>
            <button class="btn btn-primary" onclick="this.parentElement.parentElement.remove()">OK</button>
        </div>
    `;
    document.body.appendChild(dialog);
}

// Add new task to the list
function addTaskToList(task) {
    const taskList = document.querySelector('.task-list');
    if (!taskList) return;

    const taskHtml = `
        <div class="task-item animate__animated animate__fadeIn" id="task-${task.id}">
            <div class="task-content">
                <h5>${task.title}</h5>
                ${task.description ? `<p class="task-description">${task.description}</p>` : ''}
                <div class="task-meta">
                    <span class="rank-badge rank-${task.rank.toLowerCase()}">${task.rank}</span>
                </div>
            </div>
            <div class="task-actions">
                <button class="btn btn-success btn-sm hover-sound" onclick="handleTaskComplete(${task.id})">
                    <i data-feather="check"></i> Complete
                </button>
                <button class="btn btn-danger btn-sm hover-sound" onclick="handleTaskDelete(${task.id})">
                    <i data-feather="trash-2"></i> Delete
                </button>
            </div>
        </div>
    `;
    taskList.insertAdjacentHTML('afterbegin', taskHtml);
    if (typeof feather !== 'undefined') {
        feather.replace();
    }
}

// Initialize auto-refresh
let refreshInterval;

// Start auto-refresh
function startAutoRefresh() {
    if (!refreshInterval) {
        refreshInterval = setInterval(async () => {
            await Promise.all([updateProgressBar(), updateStats()]);
        }, 30000);
    }
}

// Stop auto-refresh
function stopAutoRefresh() {
    if (refreshInterval) {
        clearInterval(refreshInterval);
        refreshInterval = null;
    }
}

// Handle page visibility
document.addEventListener('visibilitychange', () => {
    if (document.hidden) {
        stopAutoRefresh();
    } else {
        startAutoRefresh();
    }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    startAutoRefresh();
    Promise.all([updateProgressBar(), updateStats()]);

    // Add event listener for task creation form
    const newTaskForm = document.getElementById('new-task-form');
    if (newTaskForm) {
        let isSubmitting = false; // Add submission lock

        newTaskForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            if (isSubmitting) return; // Prevent double submission
            isSubmitting = true;

            const formData = new FormData(e.target);
            const taskRank = formData.get('rank');

            try {
                // Check daily limit and rank restrictions
                const limitResponse = await fetch(`/api/tasks/can_create?rank=${taskRank}`);
                const limitData = await limitResponse.json();

                if (!limitData.can_create) {
                    showErrorDialog('Task Creation Limit', limitData.reason || 'Cannot create more tasks today. Please try again tomorrow.');
                    return;
                }

                const response = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        title: formData.get('title'),
                        description: formData.get('description'),
                        rank: taskRank
                    })
                });

                if (!response.ok) {
                    throw new Error('Failed to create task');
                }

                const task = await response.json();
                addTaskToList(task);
                e.target.reset();

                // Reset rank selector
                document.querySelectorAll('.rank-option').forEach(option => {
                    option.classList.remove('selected');
                });
                document.querySelector('.rank-option.rank-e').classList.add('selected');
                document.getElementById('taskRank').value = 'E';

                // Update stats after successful creation
                await Promise.all([updateProgressBar(), updateStats()]);
            } catch (error) {
                console.error('Error creating task:', error);
                showErrorDialog('Error', 'Failed to create task. Please try again.');
            } finally {
                isSubmitting = false; // Reset submission lock
            }
        });
    }
});

const styles = `
.error-dialog {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.8);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 1000;
}

.error-content {
    background: #fff;
    padding: 20px;
    border-radius: 10px;
    max-width: 400px;
    text-align: center;
}

.error-content h4 {
    color: #dc3545;
    margin-bottom: 10px;
}

.error-content p {
    color: #333;
    margin-bottom: 20px;
}
`;

document.head.insertAdjacentHTML('beforeend', `<style>${styles}</style>`);