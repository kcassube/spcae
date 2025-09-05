// Modern UI Interactions
document.addEventListener('DOMContentLoaded', () => {
  // Theme Switching
  const themeToggle = document.getElementById('themeToggle');
  if (themeToggle) {
    themeToggle.addEventListener('click', () => {
      const html = document.documentElement;
      const currentTheme = html.getAttribute('data-theme');
      const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
      html.setAttribute('data-theme', newTheme);
      localStorage.setItem('theme', newTheme);
      themeToggle.textContent = newTheme === 'dark' ? '☀️' : '🌙';
    });
  }

  // Mobile Menu Toggle
  const menuBtn = document.getElementById('menuBtn');
  const sidebar = document.getElementById('sidebar');
  if (menuBtn && sidebar) {
    menuBtn.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close sidebar when clicking outside
    document.addEventListener('click', (e) => {
      if (sidebar.classList.contains('open') && 
          !sidebar.contains(e.target) && 
          e.target !== menuBtn) {
        sidebar.classList.remove('open');
      }
    });
  }

  // Smooth Scrolling
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      e.preventDefault();
      const target = document.querySelector(this.getAttribute('href'));
      if (target) {
        target.scrollIntoView({
          behavior: 'smooth'
        });
      }
    });
  });

  // Cards Animation
  const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  };

  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('fade-in');
        observer.unobserve(entry.target);
      }
    });
  }, observerOptions);

  document.querySelectorAll('.card').forEach(card => {
    observer.observe(card);
  });

  // Table Row Hover Effects
  document.querySelectorAll('table tbody tr').forEach(row => {
    row.addEventListener('mouseenter', () => {
      row.style.backgroundColor = 'var(--color-surface)';
      row.style.transition = 'background-color 0.2s ease';
    });

    row.addEventListener('mouseleave', () => {
      row.style.backgroundColor = '';
    });
  });

  // Input Animations
  document.querySelectorAll('.input').forEach(input => {
    const wrapper = document.createElement('div');
    wrapper.classList.add('input-wrapper');
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    input.addEventListener('focus', () => {
      wrapper.classList.add('focused');
    });

    input.addEventListener('blur', () => {
      wrapper.classList.remove('focused');
    });
  });

  // Flash Message Animations
  document.querySelectorAll('.flash').forEach(flash => {
    flash.style.animation = 'slideIn 0.3s ease-out';
    
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '×';
    closeBtn.classList.add('flash-close');
    closeBtn.addEventListener('click', () => {
      flash.style.animation = 'slideOut 0.3s ease-out forwards';
      setTimeout(() => flash.remove(), 300);
    });
    
    flash.appendChild(closeBtn);
  });
});

// Utility Functions
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// Animations
const animations = `
@keyframes slideIn {
  from { transform: translateY(-100%); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

@keyframes slideOut {
  from { transform: translateY(0); opacity: 1; }
  to { transform: translateY(-100%); opacity: 0; }
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
`;

// Add animations to document
const style = document.createElement('style');
style.textContent = animations;
document.head.appendChild(style);
