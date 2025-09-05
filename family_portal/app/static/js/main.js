// Main JavaScript file for the Family Portal
document.addEventListener('DOMContentLoaded', function() {
    // Sidebar toggle for mobile
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        sidebarToggle.addEventListener('click', function() {
            sidebar.classList.toggle('active');
        });
        
        // Close sidebar when clicking outside
        document.addEventListener('click', function(event) {
            if (sidebar.classList.contains('active') && 
                !sidebar.contains(event.target) && 
                !sidebarToggle.contains(event.target)) {
                sidebar.classList.remove('active');
            }
        });
    }
    
    // Notification dropdown
    const notificationToggle = document.querySelector('.notification-toggle');
    const notificationDropdown = document.getElementById('notificationDropdown');
    
    if (notificationToggle && notificationDropdown) {
        notificationToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            notificationDropdown.classList.toggle('active');
            
            // If dropdown is now active, fetch notifications
            if (notificationDropdown.classList.contains('active')) {
                fetchNotifications();
            }
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(event) {
            if (notificationDropdown.classList.contains('active') && 
                !notificationDropdown.contains(event.target) && 
                !notificationToggle.contains(event.target)) {
                notificationDropdown.classList.remove('active');
            }
        });
    }
    
    // "Mark all as read" button
    const markAllRead = document.getElementById('markAllRead');
    if (markAllRead) {
        markAllRead.addEventListener('click', function(e) {
            e.preventDefault();
            markAllNotificationsAsRead();
        });
    }
    
    // Alert close buttons
    const alertCloseButtons = document.querySelectorAll('.close-alert');
    alertCloseButtons.forEach(function(button) {
        button.addEventListener('click', function() {
            const alert = button.parentElement;
            alert.style.opacity = '0';
            setTimeout(function() {
                alert.style.display = 'none';
            }, 300);
        });
    });
    
    // Set up Socket.IO connection if user is authenticated
    setupSocketConnection();
    
    // Initialize theme switcher if available
    initThemeSwitcher();
    
    // Initialize notification badge
    updateNotificationBadge();
});

// Socket.IO setup
function setupSocketConnection() {
    if (typeof io !== 'undefined') {
        // Connect to the socket server
        const socket = io();
        
        // Handle connection
        socket.on('connect', function() {
            console.log('Connected to socket server');
        });
        
        // Handle disconnection
        socket.on('disconnect', function() {
            console.log('Disconnected from socket server');
        });
        
        // Handle new notification
        socket.on('new_notification', function(data) {
            // Add notification to the list if dropdown is open
            if (document.getElementById('notificationDropdown').classList.contains('active')) {
                addNotificationToList(data);
            }
            
            // Update notification badge
            updateNotificationBadgeCount(1, true);
            
            // Show notification toast
            showNotificationToast(data);
        });
    }
}

// Theme switcher
function initThemeSwitcher() {
    const themeSwitcher = document.getElementById('themeSwitcher');
    if (themeSwitcher) {
        // Check for saved theme preference or respect OS preference
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            document.documentElement.setAttribute('data-theme', savedTheme);
            themeSwitcher.checked = (savedTheme === 'dark');
        } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
            document.documentElement.setAttribute('data-theme', 'dark');
            themeSwitcher.checked = true;
        }
        
        // Handle theme switch
        themeSwitcher.addEventListener('change', function() {
            const theme = this.checked ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('theme', theme);
        });
    }
}

// Fetch notifications from server
function fetchNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            const notificationList = document.getElementById('notificationList');
            
            // Clear current list
            notificationList.innerHTML = '';
            
            if (data.notifications && data.notifications.length > 0) {
                // Add each notification to the list
                data.notifications.forEach(notification => {
                    addNotificationToList(notification);
                });
            } else {
                // Show empty state
                notificationList.innerHTML = '<div class="notification-empty">Keine neuen Benachrichtigungen</div>';
            }
        })
        .catch(error => {
            console.error('Error fetching notifications:', error);
        });
}

// Add a notification to the dropdown list
function addNotificationToList(notification) {
    const notificationList = document.getElementById('notificationList');
    
    // Remove empty state if present
    const emptyState = notificationList.querySelector('.notification-empty');
    if (emptyState) {
        notificationList.removeChild(emptyState);
    }
    
    // Create notification element
    const notificationElement = document.createElement('div');
    notificationElement.className = `notification-item ${notification.read ? '' : 'unread'}`;
    notificationElement.dataset.id = notification.id;
    
    // Format the time
    const notificationTime = new Date(notification.timestamp);
    const timeString = formatNotificationTime(notificationTime);
    
    // Set the content
    notificationElement.innerHTML = `
        <div class="notification-content">${notification.message}</div>
        <div class="notification-time">${timeString}</div>
    `;
    
    // Add click handler to mark as read and navigate
    notificationElement.addEventListener('click', function() {
        markNotificationAsRead(notification.id);
        if (notification.link) {
            window.location.href = notification.link;
        }
    });
    
    // Add to the list
    notificationList.prepend(notificationElement);
}

// Format notification time relative to now
function formatNotificationTime(date) {
    const now = new Date();
    const diffMs = now - date;
    const diffSec = Math.floor(diffMs / 1000);
    const diffMin = Math.floor(diffSec / 60);
    const diffHour = Math.floor(diffMin / 60);
    const diffDay = Math.floor(diffHour / 24);
    
    if (diffSec < 60) {
        return 'gerade eben';
    } else if (diffMin < 60) {
        return `vor ${diffMin} ${diffMin === 1 ? 'Minute' : 'Minuten'}`;
    } else if (diffHour < 24) {
        return `vor ${diffHour} ${diffHour === 1 ? 'Stunde' : 'Stunden'}`;
    } else if (diffDay < 7) {
        return `vor ${diffDay} ${diffDay === 1 ? 'Tag' : 'Tagen'}`;
    } else {
        return date.toLocaleDateString();
    }
}

// Mark a notification as read
function markNotificationAsRead(notificationId) {
    fetch(`/api/notifications/${notificationId}/read`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => {
        if (response.ok) {
            // Update UI
            const notificationElement = document.querySelector(`.notification-item[data-id="${notificationId}"]`);
            if (notificationElement && notificationElement.classList.contains('unread')) {
                notificationElement.classList.remove('unread');
                updateNotificationBadgeCount(1, false);
            }
        }
    })
    .catch(error => {
        console.error('Error marking notification as read:', error);
    });
}

// Mark all notifications as read
function markAllNotificationsAsRead() {
    fetch('/api/notifications/read-all', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        }
    })
    .then(response => {
        if (response.ok) {
            // Update UI
            const unreadNotifications = document.querySelectorAll('.notification-item.unread');
            unreadNotifications.forEach(notification => {
                notification.classList.remove('unread');
            });
            
            // Reset badge
            updateNotificationBadgeCount(0, false);
        }
    })
    .catch(error => {
        console.error('Error marking all notifications as read:', error);
    });
}

// Update notification badge with count
function updateNotificationBadge() {
    fetch('/api/notifications/unread-count')
        .then(response => response.json())
        .then(data => {
            updateNotificationBadgeCount(data.count, false);
        })
        .catch(error => {
            console.error('Error fetching notification count:', error);
        });
}

// Update the notification badge display
function updateNotificationBadgeCount(count, increment) {
    const badge = document.getElementById('notificationBadge');
    if (!badge) return;
    
    let currentCount = parseInt(badge.textContent) || 0;
    
    if (increment) {
        currentCount += count;
    } else {
        currentCount = count;
    }
    
    if (currentCount > 0) {
        badge.textContent = currentCount > 99 ? '99+' : currentCount;
        badge.style.display = 'flex';
    } else {
        badge.style.display = 'none';
    }
}

// Show notification toast
function showNotificationToast(notification) {
    // Check if the toast container exists, create if not
    let toastContainer = document.getElementById('toastContainer');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toastContainer';
        toastContainer.className = 'toast-container';
        document.body.appendChild(toastContainer);
    }
    
    // Create toast element
    const toast = document.createElement('div');
    toast.className = 'toast';
    
    // Format the time
    const notificationTime = new Date(notification.timestamp);
    const timeString = formatNotificationTime(notificationTime);
    
    // Set content
    toast.innerHTML = `
        <div class="toast-header">
            <strong>Neue Benachrichtigung</strong>
            <span class="toast-time">${timeString}</span>
            <button class="toast-close">&times;</button>
        </div>
        <div class="toast-body">${notification.message}</div>
    `;
    
    // Add to container
    toastContainer.appendChild(toast);
    
    // Add click handler
    toast.addEventListener('click', function(e) {
        if (!e.target.classList.contains('toast-close')) {
            markNotificationAsRead(notification.id);
            if (notification.link) {
                window.location.href = notification.link;
            }
        }
    });
    
    // Add close button handler
    const closeButton = toast.querySelector('.toast-close');
    closeButton.addEventListener('click', function(e) {
        e.stopPropagation();
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    });
    
    // Auto hide after 5 seconds
    setTimeout(() => {
        toast.classList.add('toast-hiding');
        setTimeout(() => {
            toast.remove();
        }, 300);
    }, 5000);
    
    // Show toast with animation
    setTimeout(() => {
        toast.classList.add('toast-visible');
    }, 10);
}

// Get CSRF token from meta tag
function getCSRFToken() {
    return document.querySelector('meta[name="csrf-token"]').getAttribute('content');
}
