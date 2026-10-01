// Shared UI & API Utilities for RAG Retrieval Quality Evaluator

function getCookie(name) {
  let cookieValue = null;
  if (document.cookie && document.cookie !== '') {
    const cookies = document.cookie.split(';');
    for (let i = 0; i < cookies.length; i++) {
      const cookie = cookies[i].trim();
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
        break;
      }
    }
  }
  return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Mobile Sidebar Toggle
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('mobileSidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('show');
    });
  }
});

// Toast / Notification helper
function showToast(message, type = 'info') {
  const toastContainer = document.getElementById('toastContainer');
  if (!toastContainer) return;

  const toast = document.createElement('div');
  toast.className = `alert alert-${type === 'error' ? 'danger' : type === 'success' ? 'success' : 'info'} alert-dismissible fade show card-dark text-white mb-2 shadow-lg`;
  toast.role = 'alert';
  toast.style.borderLeft = `4px solid ${type === 'error' ? '#ef4444' : type === 'success' ? '#10b981' : '#3b82f6'}`;
  toast.innerHTML = `
    <div class="d-flex align-items-center justify-content-between">
      <div><i class="bi ${type === 'error' ? 'bi-exclamation-triangle-fill text-danger' : type === 'success' ? 'bi-check-circle-fill text-success' : 'bi-info-circle-fill text-primary'} me-2"></i> ${message}</div>
      <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert" aria-label="Close"></button>
    </div>
  `;

  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => toast.remove(), 200);
  }, 4000);
}
