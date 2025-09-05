// Enterprise UI Framework
class EnterpriseUI {
  constructor() {
    this.initTheme();
    this.initSidebar();
    this.initDropdowns();
    this.initCards();
    this.initNotifications();
    this.initDataTables();
    this.initCharts();
  }

  // Theme Management
  initTheme() {
    const theme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', theme);

    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.addEventListener('click', () => {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        this.updateThemeIcon(newTheme);
      });

      this.updateThemeIcon(theme);
    }
  }

  updateThemeIcon(theme) {
    const themeToggle = document.getElementById('themeToggle');
    if (themeToggle) {
      themeToggle.innerHTML = theme === 'dark' 
        ? '<i class="fas fa-sun"></i>' 
        : '<i class="fas fa-moon"></i>';
    }
  }

  // Responsive Sidebar
  initSidebar() {
    const menuBtn = document.getElementById('menuBtn');
    const sidebar = document.getElementById('sidebar');
    const overlay = document.createElement('div');
    overlay.classList.add('sidebar-overlay');
    document.body.appendChild(overlay);

    if (menuBtn && sidebar) {
      menuBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open');
        overlay.classList.toggle('active');
        document.body.classList.toggle('sidebar-open');
      });

      overlay.addEventListener('click', () => {
        sidebar.classList.remove('open');
        overlay.classList.remove('active');
        document.body.classList.remove('sidebar-open');
      });

      // Close sidebar on navigation
      const navLinks = sidebar.querySelectorAll('a');
      navLinks.forEach(link => {
        link.addEventListener('click', () => {
          if (window.innerWidth < 1024) {
            sidebar.classList.remove('open');
            overlay.classList.remove('active');
            document.body.classList.remove('sidebar-open');
          }
        });
      });
    }
  }

  // Dropdown Menus
  initDropdowns() {
    document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
      toggle.addEventListener('click', (e) => {
        e.preventDefault();
        const dropdown = toggle.nextElementSibling;
        dropdown.classList.toggle('show');

        // Close other dropdowns
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
          if (menu !== dropdown) {
            menu.classList.remove('show');
          }
        });
      });
    });

    // Close dropdowns when clicking outside
    document.addEventListener('click', (e) => {
      if (!e.target.matches('.dropdown-toggle')) {
        document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
          menu.classList.remove('show');
        });
      }
    });
  }

  // Card Animations
  initCards() {
    const cards = document.querySelectorAll('.card');
    const observer = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('card-animated');
          observer.unobserve(entry.target);
        }
      });
    }, {
      threshold: 0.1,
      rootMargin: '0px 0px -50px 0px'
    });

    cards.forEach(card => observer.observe(card));
  }

  // Notification System
  initNotifications() {
    this.notifications = [];
    const container = document.createElement('div');
    container.classList.add('notification-container');
    document.body.appendChild(container);
  }

  showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.classList.add('notification', `notification-${type}`);
    notification.innerHTML = `
      <i class="fas fa-${this.getNotificationIcon(type)}"></i>
      <span>${message}</span>
      <button class="notification-close"><i class="fas fa-times"></i></button>
    `;

    const container = document.querySelector('.notification-container');
    container.appendChild(notification);

    // Auto dismiss after 5 seconds
    setTimeout(() => {
      notification.classList.add('notification-hide');
      setTimeout(() => notification.remove(), 300);
    }, 5000);

    // Close button
    notification.querySelector('.notification-close').addEventListener('click', () => {
      notification.classList.add('notification-hide');
      setTimeout(() => notification.remove(), 300);
    });
  }

  getNotificationIcon(type) {
    const icons = {
      success: 'check-circle',
      error: 'exclamation-circle',
      warning: 'exclamation-triangle',
      info: 'info-circle'
    };
    return icons[type] || icons.info;
  }

  // Enhanced DataTables
  initDataTables() {
    document.querySelectorAll('.datatable').forEach(table => {
      const headers = table.querySelectorAll('th');
      headers.forEach(header => {
        if (header.dataset.sortable !== 'false') {
          header.classList.add('sortable');
          header.addEventListener('click', () => this.sortTable(table, header));
        }
      });
    });
  }

  sortTable(table, header) {
    const index = Array.from(header.parentElement.children).indexOf(header);
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const direction = header.classList.contains('sort-asc') ? -1 : 1;

    // Remove sort classes from all headers
    table.querySelectorAll('th').forEach(th => {
      th.classList.remove('sort-asc', 'sort-desc');
    });

    // Add sort class to clicked header
    header.classList.add(direction === 1 ? 'sort-asc' : 'sort-desc');

    // Sort rows
    rows.sort((a, b) => {
      const aValue = a.children[index].textContent;
      const bValue = b.children[index].textContent;
      return direction * this.compareValues(aValue, bValue);
    });

    // Reorder table rows
    const tbody = table.querySelector('tbody');
    rows.forEach(row => tbody.appendChild(row));
  }

  compareValues(a, b) {
    // Check if values are numbers
    const aNum = parseFloat(a);
    const bNum = parseFloat(b);
    if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
    
    // Compare as strings
    return a.localeCompare(b, 'de', { numeric: true });
  }

  // Chart Initialization
  initCharts() {
    document.querySelectorAll('[data-chart]').forEach(element => {
      const type = element.dataset.chart;
      const data = JSON.parse(element.dataset.chartData || '{}');
      
      // Initialize charts if a charting library is available
      if (window.Chart) {
        new Chart(element, {
          type,
          data,
          options: this.getChartOptions(type)
        });
      }
    });
  }

  getChartOptions(type) {
    return {
      responsive: true,
      maintainAspectRatio: false,
      animation: {
        duration: 1000,
        easing: 'easeInOutQuart'
      },
      plugins: {
        legend: {
          position: 'bottom'
        }
      }
    };
  }
}

// Initialize Enterprise UI
document.addEventListener('DOMContentLoaded', () => {
  window.enterpriseUI = new EnterpriseUI();
});
