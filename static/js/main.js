// Function to fetch and display user stats including login streak
function updateUserStats() {
    fetch('/api/user/stats')
        .then(response => response.json())
        .then(data => {
            // Update user rank, level and exp
            document.querySelectorAll('.user-rank').forEach(el => {
                el.textContent = data.rank || 'E';
            });
            document.querySelectorAll('.user-level').forEach(el => {
                el.textContent = data.level || '1';
            });

            // Update exp bars if present
            const expBars = document.querySelectorAll('.exp-bar-fill');
            if (expBars.length > 0) {
                const nextRankExp = data.next_rank_exp || 100;
                const monthlyExp = data.monthly_exp || 0;
                const percentage = Math.min(100, (monthlyExp / (monthlyExp + nextRankExp)) * 100);

                expBars.forEach(bar => {
                    bar.style.width = `${percentage}%`;
                });
            }

            // Update exp counters if present
            document.querySelectorAll('.exp-counter').forEach(el => {
                el.textContent = data.monthly_exp || '0';
            });

            // Update next rank exp if present
            document.querySelectorAll('.next-rank-exp').forEach(el => {
                el.textContent = data.next_rank_exp || '100';
            });

            // Update login streak if present
            const loginStreakElement = document.getElementById('loginStreak');
            if (loginStreakElement) {
                loginStreakElement.textContent = data.login_streak || '1';
            }

            // Update HP and coins if present
            if (data.hp !== undefined) {
                document.querySelectorAll('#userHP, [data-user-hp]').forEach(el => el.textContent = data.hp);
            }
            if (data.max_hp !== undefined) {
                document.querySelectorAll('#userMaxHP, [data-user-maxhp]').forEach(el => el.textContent = data.max_hp);

                // Update HP bars
                document.querySelectorAll('.hp-bar .hp-fill').forEach(el => {
                    const percentage = (data.hp / data.max_hp) * 100;
                    el.style.width = `${percentage}%`;
                });

                // Update progress bars that show HP
                document.querySelectorAll('.progress-bar[aria-valuenow]').forEach(el => {
                    if (el.closest('.progress')?.getAttribute('data-type') === 'hp') {
                        const percentage = (data.hp / data.max_hp) * 100;
                        el.style.width = `${percentage}%`;
                        el.setAttribute('aria-valuenow', data.hp);
                        el.setAttribute('aria-valuemax', data.max_hp);
                    }
                });
            }


            const userCoinsElement = document.getElementById('userCoins');
            if (userCoinsElement) {
                userCoinsElement.textContent = data.coins || '0';
            }

            // Update HP progress bar if present
            const hpBar = document.querySelector('.progress-bar.bg-danger');
            if (hpBar && data.hp !== undefined && data.max_hp > 0) {
                const hpPercentage = Math.min(100, (data.hp / data.max_hp) * 100);
                hpBar.style.width = `${hpPercentage}%`;
                hpBar.setAttribute('aria-valuenow', data.hp);
                hpBar.setAttribute('aria-valuemax', data.max_hp);
            }
        })
        .catch(err => {
            console.error("Error updating stats:", err);
        });
}

// Call the function when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Only fetch user stats if the user is logged in
    // (Check for elements that only exist when logged in)
    if (document.getElementById('loginStreak') || 
        document.querySelector('.profile-summary')) {
        updateUserStats();
    }
});

// Global utility functions and sound effects
const hoverSound = new Audio('/static/sounds/hover.mp3');
const completeSound = new Audio('/static/sounds/complete.mp3');

// Theme management
let currentTheme = localStorage.getItem('theme') || 'dark';
document.body.className = `${currentTheme}-theme`;

function toggleTheme() {
    currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
    document.body.className = `${currentTheme}-theme`;
    localStorage.setItem('theme', currentTheme);
}

// Sound Management
hoverSound.volume = 0.3;
completeSound.volume = 0.4;

// Space Background Animation
function createSpaceBackground() {
    const container = document.querySelector('.space-background');
    if (!container) return;

    const objects = ['⭐', '✨', '💫', '🌟', '⚡'];
    const numObjects = 20;

    for (let i = 0; i < numObjects; i++) {
        const obj = document.createElement('span');
        obj.className = 'floating-object';
        obj.textContent = objects[Math.floor(Math.random() * objects.length)];
        obj.style.left = `${Math.random() * 100}%`;
        obj.style.top = `${Math.random() * 100}%`;
        obj.style.animationDelay = `${Math.random() * 20}s`;
        container.appendChild(obj);
    }
}

// Task rank selection
function initializeRankSelector() {
    const rankOptions = document.querySelectorAll('.rank-option');
    rankOptions.forEach(option => {
        option.addEventListener('click', () => {
            rankOptions.forEach(opt => opt.classList.remove('selected'));
            option.classList.add('selected');
            document.getElementById('taskRank').value = option.dataset.rank;
            hoverSound.currentTime = 0;
            hoverSound.play().catch(() => {});
        });
    });
}

// Achievement badge animation
function animateAchievementUnlock(badgeId) {
    const badge = document.querySelector(`#badge-${badgeId}`);
    if (badge) {
        badge.classList.add('animate__animated', 'animate__bounce');
        setTimeout(() => badge.classList.remove('animate__animated', 'animate__bounce'), 1000);
    }
}

// Stats and progress bar functions
// Store DOM elements for better performance
const domElements = {
    progressBar: document.getElementById('progress-bar'),
    completedTasksCount: document.getElementById('completed-tasks-count'),
    monthlyExp: document.getElementById('monthlyExp'),
    lifetimeExp: document.getElementById('lifetimeExp'),
    userLevel: document.getElementById('userLevel'),
    userRank: document.getElementById('userRank'),
    monthlyExpProgress: document.getElementById('monthlyExpProgress'),
    lifetimeExpProgress: document.getElementById('lifetimeExpProgress')
};

// Update progress bar
async function updateProgressBar() {
    try {
        // Skip API calls if we're already on the login page
        if (window.location.pathname === '/login') {
            return;
        }

        const response = await fetch('/api/tasks/stats');

        if (response.status === 401) {
            window.location.href = '/login';
            return;
        }

        if (!response.ok) {
            throw new Error('Failed to fetch task stats');
        }

        const data = await response.json();

        const progressBar = document.getElementById('progress-bar');
        const completedTasksCount = document.getElementById('completed-tasks-count');

        if (progressBar && completedTasksCount) {
            const progress = data.total > 0 ? (data.completed / data.total) * 100 : 0;
            progressBar.style.width = `${progress}%`;
            completedTasksCount.textContent = `${data.completed}/${data.total}`;
        }
    } catch (error) {
        console.error('Error updating progress bar:', error);
        // Don't show error to user, just log it
    }
}

// Add this debugging function at the top of the file
function debugLog(message, data = null) {
    if (process.env.NODE_ENV !== 'production') {
        console.log(`[Debug] ${message}`, data || '');
    }
}

// Update the updateStats function
async function updateStats() {
    try {
        debugLog('Fetching stats updates...');

        // Get responses in parallel
        const [taskResponse, userResponse] = await Promise.all([
            fetch('/api/tasks/stats'),
            fetch('/api/user/stats')
        ]);

        // Check for authentication errors
        if (taskResponse.status === 401 || userResponse.status === 401) {
            debugLog('Authentication required, redirecting to login');
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

        debugLog('Received stats update:', { taskStats, userStats });

        // Check if we're on the leaderboard page
        const isLeaderboardPage = window.location.pathname === '/leaderboard';
        if (isLeaderboardPage) {
            debugLog('Skipping rank updates on leaderboard page');
            return; // Skip updating ranks on leaderboard page
        }

        // Update all level displays
        document.querySelectorAll('[id="userLevel"], .level-info h4, .level-display h2').forEach(el => {
            el.textContent = userStats.level || 1;
        });

        // Update all EXP displays - using the correct property name from the API
        document.querySelectorAll('[id="monthlyExp"]').forEach(el => {
            // The API now only uses 'exp' instead of 'monthly_exp'
            el.textContent = userStats.exp || 0;
        });

        document.querySelectorAll('[id="lifetimeExp"]').forEach(el => {
            // Consistently use the same 'exp' property from API
            el.textContent = userStats.exp || 0;
        });

        // Update HP and max HP displays
        document.querySelectorAll('.hp-display, .current-hp').forEach(el => {
            el.textContent = userStats.hp || 0;
        });
        
        document.querySelectorAll('.max-hp').forEach(el => {
            // Formula: 500 + (level-1) * 10
            const maxHp = userStats.max_hp || 500;
            el.textContent = maxHp;
        });
        
        // Update HP bar if it exists
        const hpBar = document.querySelector('.hp-bar');
        if (hpBar) {
            const hpPercent = Math.min(100, Math.max(0, (userStats.hp / userStats.max_hp) * 100));
            hpBar.style.width = `${hpPercent}%`;
        }
        
        // Update buff/debuff effect display if it exists
        const buffDisplay = document.querySelector('.buff-effect');
        if (buffDisplay && userStats.buff_effect !== undefined) {
            const buffEffect = userStats.buff_effect;
            if (buffEffect > 0) {
                buffDisplay.textContent = `+${buffEffect}%`;
                buffDisplay.className = 'buff-effect buff-positive';
                buffDisplay.title = 'Active buff: Gain extra EXP';
            } else if (buffEffect < 0) {
                buffDisplay.textContent = `${buffEffect}%`;
                buffDisplay.className = 'buff-effect buff-negative';
                buffDisplay.title = 'Active debuff: Reduced EXP gain';
            } else {
                buffDisplay.textContent = '';
                buffDisplay.className = 'buff-effect';
                buffDisplay.title = '';
            }
        }

        // Update user's rank only in profile/header sections, not leaderboard
        document.querySelectorAll('.profile-rank #userRank, .user-rank-display h3').forEach(el => {
            el.textContent = `Rank ${userStats.rank}`;
            if (el.className) {
                el.className = el.className.replace(/rank-[a-zA-Z+-]+/, `rank-${userStats.rank.toLowerCase()}`);
            }
        });

        // Update coins display
        document.querySelectorAll('.coins-display').forEach(el => {
            el.textContent = userStats.coins || 0;
        });

        // Update progress bars with smooth animation using the correct property names
        // Calculate EXP progress to next level: (exp % 50) / 50 * 100
        const lifetimeProgress = userStats.exp ? (userStats.exp % 50) / 50 * 100 : 0;

        requestAnimationFrame(() => {
            document.querySelectorAll('.profile-progress .progress-bar').forEach(bar => {
                bar.style.width = `${lifetimeProgress}%`;
                bar.setAttribute('aria-valuenow', lifetimeProgress);
                bar.textContent = '';  // Remove numerals from bar
            });
        });

        debugLog('Stats update completed successfully');
    } catch (error) {
        console.error('Error updating stats:', error);
        debugLog('Failed to update stats:', error);
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

// Show level up notification
function showLevelUpNotification(newLevel, newMaxHp) {
    // Create a more prominent notification for level up
    const notification = document.createElement('div');
    notification.className = 'level-up-notification animate__animated animate__bounceIn';
    notification.innerHTML = `
        <div class="level-up-container">
            <div class="level-up-icon">
                <i data-feather="arrow-up-circle"></i>
            </div>
            <div class="level-up-text">
                <h3>Level Up!</h3>
                <p>You've reached level ${newLevel}</p>
                <p>Max HP increased to ${newMaxHp}</p>
            </div>
        </div>
    `;
    document.body.appendChild(notification);

    // Update feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Play level up sound if available
    if (window.completeSound) {
        // Play twice for a more special effect
        completeSound.currentTime = 0;
        completeSound.play().catch(() => {});

        setTimeout(() => {
            completeSound.currentTime = 0;
            completeSound.play().catch(() => {});
        }, 300);
    }

    // Add confetti effect if available
    if (window.confettiCelebration) {
        window.confettiCelebration.startConfetti();
        setTimeout(() => {
            window.confettiCelebration.stopConfetti();
        }, 3000);
    }

    // Remove notification after animation completes
    setTimeout(() => {
        notification.classList.remove('animate__bounceIn');
        notification.classList.add('animate__bounceOut');
        setTimeout(() => notification.remove(), 1000);
    }, 4000);
}

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

        // First update all stats
        await updateStats();

        const taskElement = document.getElementById(`task-${taskId}`);
        if (!taskElement) return;

        // Remove action buttons immediately
        const actionsDiv = taskElement.querySelector('.task-actions');
        if (actionsDiv) {
            actionsDiv.remove();
        }

        // Add animation and move to completed section
        taskElement.classList.add('animate__fadeOut');

        setTimeout(() => {
            taskElement.classList.remove('animate__fadeOut');
            taskElement.classList.add('completed');

            // Add completed text if not exists
            const metaDiv = taskElement.querySelector('.task-meta');
            if (metaDiv && !metaDiv.querySelector('.text-muted')) {
                const completedText = document.createElement('small');
                completedText.className = 'text-muted';
                completedText.textContent = ' Completed';
                metaDiv.appendChild(completedText);
            }

            // Move to completed section
            const completedList = document.getElementById('completedTasksList');
            if (completedList) {
                taskElement.classList.add('animate__fadeIn');
                completedList.insertBefore(taskElement, completedList.firstChild);
            }

            // Show EXP notification
            if (data.exp_gained) {
                showExpNotification(data.exp_gained);
            }

            // Show level up notification if applicable
            if (data.level_up && data.new_level) {
                showLevelUpNotification(data.new_level, data.new_max_hp);
            }

            // Update all stats
            Promise.all([updateProgressBar(), updateStats()]);
        }, 500);
    } catch (error) {
        console.error('Error completing task:', error);
    }
}

// Handle task deletion
async function handleTaskDelete(taskId) {
    if (!confirm('Are you sure you want to delete this task?')) return;

    try {
        const response = await fetch(`/api/tasks/${taskId}/delete`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error('Failed to delete task');
        }

        const taskElement = document.getElementById(`task-${taskId}`);
        if (!taskElement) return;

        taskElement.classList.add('animate__fadeOut');

        setTimeout(() => {
            taskElement.remove();
            Promise.all([updateProgressBar(), updateStats()]);
        }, 500);
    } catch (error) {
        console.error('Error deleting task:', error);
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    // Initialize theme
    const themeToggle = document.querySelector('.theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Initialize space background
    createSpaceBackground();

    // Initialize rank selector if present
    initializeRankSelector();

    // Initialize Feather icons
    if (typeof feather !== 'undefined') {
        feather.replace();
    }

    // Add hover sound to all interactive elements
    document.querySelectorAll('.hover-sound').forEach(element => {
        element.addEventListener('mouseenter', () => {
            if (window.hoverSound) {
                hoverSound.currentTime = 0;
                hoverSound.play().catch(() => {});
            }
        });
    });

    // Optimized audio setup - initialize immediately for faster response
    (function initAudio() {
        // Initialize audio as early as possible with minimal overhead
        const bgMusic = document.getElementById('bgMusic');
        if (!bgMusic) {
            // If element isn't available yet, retry with minimal delay (5ms)
            return setTimeout(initAudio, 5);
        }

        // Fast audio initialization with minimal processing
        if (localStorage.getItem('bgMusicMuted') !== 'true') {
            try {
                // Apply stored volume with minimal overhead
                bgMusic.volume = parseFloat(localStorage.getItem('bgMusicVolume') || '0.3');

                // Calculate position - simple and efficient
                const savedPosition = localStorage.getItem('bgMusicPosition') || '0';
                const position = parseFloat(savedPosition);

                // Set position - no complex calculations during initial load for better performance
                bgMusic.currentTime = isNaN(position) ? 0 : position;

                // Start playing immediately - critical for UX
                const playPromise = bgMusic.play();

                // Handle autoplay restrictions efficiently
                if (playPromise !== undefined) {
                    playPromise.catch(() => {
                        // Simplified one-click resume
                        const resumeAudio = () => {
                            bgMusic.play().catch(() => {});
                            document.removeEventListener('click', resumeAudio);
                        };
                        document.addEventListener('click', resumeAudio);

                        // Simple loading screen activation
                        document.querySelector('.loading-overlay')?.addEventListener('click', resumeAudio, {once: true});
                    });
                }

                // Update last play timestamp
                localStorage.setItem('bgMusicLastPlay', Date.now().toString());

            } catch (err) {
                // Silently fail - no console logs to reduce performance overhead
            }
        }
    })();

    // Setup global audio control system (this will run later, after DOM is ready)
    const bgMusic = document.getElementById('bgMusic');
    if (bgMusic) {
        const playBgMusic = () => {
            if (localStorage.getItem('bgMusicMuted') !== 'true') {
                try {
                    // Only adjust volume and UI here since playback already started
                    const storedVolume = localStorage.getItem('bgMusicVolume');
                    bgMusic.volume = parseFloat(storedVolume || '0.3');

                    // If it's not playing for some reason, restart it
                    if (bgMusic.paused) {
                        const savedPosition = localStorage.getItem('bgMusicPosition') || '0';
                        const position = parseFloat(savedPosition);

                        if (!isNaN(position)) {
                            bgMusic.currentTime = position;
                        }

                        bgMusic.play().catch(err => {
                            console.log('BGM autoplay prevented in main init:', err);
                        });
                    }

                    // Update last play time
                    localStorage.setItem('bgMusicLastPlay', Date.now().toString());

                    // Initialize audio player UI
                    updateAudioPlayerUI(!bgMusic.paused);
                } catch (err) {
                    console.error('Error in BGM playback:', err);
                }
            } else {
                updateAudioPlayerUI(false);
            }
        };

        // Handle browser/tab visibility changes to keep consistent state
        document.addEventListener('visibilitychange', () => {
            // When returning to the page, we need to check audio state
            if (!document.hidden && localStorage.getItem('bgMusicMuted') !== 'true' && bgMusic.paused) {
                playBgMusic();
            }
        });

        // Save current time and last play time when audio is playing
        bgMusic.addEventListener('timeupdate', () => {
            if (!bgMusic.paused) {
                localStorage.setItem('bgMusicPosition', bgMusic.currentTime.toString());
                localStorage.setItem('bgMusicLastPlay', Date.now().toString());
            }
        });

        // Save current time when page is about to unload/navigate away
        window.addEventListener('beforeunload', () => {
            if (!bgMusic.paused) {
                localStorage.setItem('bgMusicPosition', bgMusic.currentTime.toString());
                localStorage.setItem('bgMusicLastPlay', Date.now().toString());
            }
        });

        // Update status of audio player UI
        function updateAudioPlayerUI(isPlaying) {
            const audioToggle = document.getElementById('toggleAudio');
            if (audioToggle) {
                const statusText = audioToggle.querySelector('.audio-status');
                const icon = audioToggle.querySelector('.audio-icon');

                if (isPlaying) {
                    statusText.textContent = 'Music: ON';
                    audioToggle.classList.remove('muted');
                    if (icon) icon.setAttribute('data-feather', 'music');
                } else {
                    statusText.textContent = 'Music: OFF';
                    audioToggle.classList.add('muted');
                    if (icon) icon.setAttribute('data-feather', 'volume-x');
                }

                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            }
        }

        // Initialize music
        playBgMusic();

        // Set up a more robust timing mechanism to ensure audio position is saved
        setInterval(() => {
            if (!bgMusic.paused) {
                localStorage.setItem('bgMusicPosition', bgMusic.currentTime.toString());
                localStorage.setItem('bgMusicVolume', bgMusic.volume.toString());
            }
        }, 300);

        // Set up audio toggle button events
        const audioToggleBtn = document.getElementById('toggleAudio');
        if (audioToggleBtn) {
            audioToggleBtn.addEventListener('click', () => {
                if (bgMusic.paused) {
                    // Resume music
                    const savedPosition = localStorage.getItem('bgMusicPosition');
                    if (savedPosition && !isNaN(parseFloat(savedPosition))) {
                        bgMusic.currentTime = parseFloat(savedPosition);
                    }
                    bgMusic.play().then(() => {
                        localStorage.setItem('bgMusicMuted', 'false');
                        updateAudioPlayerUI(true);
                    }).catch(err => {
                        console.log('Cannot play audio:', err);
                    });
                } else {
                    // Pause music
                    localStorage.setItem('bgMusicPosition', bgMusic.currentTime.toString());
                    bgMusic.pause();
                    localStorage.setItem('bgMusicMuted', 'true');
                    updateAudioPlayerUI(false);
                }
            });
        }

        // Compatibility with existing navbar control
        const navbarNav = document.querySelector('#navbarNav .navbar-nav');
        if (navbarNav) {
            const musicControl = document.createElement('li');
            musicControl.className = 'nav-item ms-2';
            musicControl.innerHTML = `
                <button id="toggleMusic" class="btn btn-sm btn-outline-light hover-sound">
                    <i data-feather="${localStorage.getItem('bgMusicMuted') === 'true' ? 'volume-x' : 'volume-2'}"></i>
                </button>
            `;
            navbarNav.appendChild(musicControl);

            if (typeof feather !== 'undefined') {
                feather.replace();
            }

            document.getElementById('toggleMusic').addEventListener('click', () => {
                if (bgMusic.paused) {
                    const savedPosition = localStorage.getItem('bgMusicPosition');
                    if (savedPosition) {
                        bgMusic.currentTime = parseFloat(savedPosition);
                    }
                    bgMusic.play();
                    localStorage.setItem('bgMusicMuted', 'false');
                    document.querySelector('#toggleMusic i').setAttribute('data-feather', 'volume-2');
                    updateAudioPlayerUI(true);
                } else {
                    localStorage.setItem('bgMusicPosition', bgMusic.currentTime.toString());
                    bgMusic.pause();
                    localStorage.setItem('bgMusicMuted', 'true');
                    document.querySelector('#toggleMusic i').setAttribute('data-feather', 'volume-x');
                    updateAudioPlayerUI(false);
                }
                if (typeof feather !== 'undefined') {
                    feather.replace();
                }
            });
        }
    }

    // Add periodic stats update
    setInterval(() => {
        if (!document.hidden) {
            Promise.all([updateStats(), updateProgressBar()]);
        }
    }, 30000);
    Promise.all([updateStats(), updateProgressBar()]);

    // Initial stats update
    updateStats();
    updateProgressBar();
});