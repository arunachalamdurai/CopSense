/* ==============================================
   CopSense — common.js v2.1
   Shared utilities: sidebar, RBAC, datetime, navbar
   Auth unified to localStorage (via api.js Auth object)
   ============================================== */

'use strict';

// ---- RBAC page access rules ----
// Citizens may only visit feedback.html and index.html
// Field Officers: duty, custody (read), alerts, feedback (read)
// Station Officer + District Head: full access
const PAGE_ROLES = {
  'dashboard.html': ['district_head', 'station_officer', 'field_officer'],
  'fir.html': ['district_head', 'station_officer', 'field_officer'],
  'complaints.html': ['district_head', 'station_officer', 'field_officer'],
  'custody.html': ['district_head', 'station_officer', 'field_officer'],
  'duty.html': ['district_head', 'station_officer', 'field_officer'],
  'crowd-planning.html': ['district_head', 'station_officer'],
  'deployment.html': ['district_head', 'station_officer', 'field_officer'],
  'alerts.html': ['district_head', 'station_officer', 'field_officer'],
  'reports.html': ['district_head', 'station_officer'],
  'settings.html': ['district_head', 'station_officer', 'field_officer'],
  'emergency.html': ['district_head', 'station_officer', 'field_officer'],
  'feedback.html': ['district_head', 'station_officer', 'field_officer', 'citizen'],
};

function enforceRBAC() {
  const path = window.location.pathname;
  const currentPage = path.split('/').pop() || 'index.html';

  // Public pages don't need RBAC
  if (currentPage === 'index.html' || currentPage === 'register.html') return;

  const allowedRoles = PAGE_ROLES[currentPage];
  if (!allowedRoles) return;

  const user = getAuthUser();
  if (!user || !user.role) {
    if (typeof Auth !== 'undefined') Auth.clear();
    window.location.href = 'index.html';
    return;
  }

  if (!allowedRoles.includes(user.role)) {
    window.location.href = user.role === 'citizen' ? 'feedback.html' : 'dashboard.html';
  }
}

// ---- Unified auth getter (prefers localStorage via Auth object, falls back to sessionStorage) ----
function getAuthUser() {
  // Try localStorage first (api.js standard)
  try {
    if (typeof Auth !== 'undefined' && Auth.getUser) {
      const u = Auth.getUser();
      if (u) return u;
    }
  } catch (e) { }
  // Fallback: sessionStorage (legacy compatibility)
  try {
    const s = JSON.parse(sessionStorage.getItem('copsense_user') || 'null');
    if (s) return _normalizeUser(s);
  } catch (e) { }
  return null;
}

function _normalizeUser(u) {
  // Normalize sessionStorage format to match localStorage format
  if (!u) return null;
  // sessionStorage stores role as label ("District Head (SSP)"), localStorage as key ("district_head")
  const roleMap = {
    'District Head (SSP)': 'district_head', 'Station Officer': 'station_officer',
    'Field Officer': 'field_officer', 'Citizen': 'citizen',
  };
  if (u.role && roleMap[u.role]) u.role = roleMap[u.role];
  if (!u.full_name && u.name) u.full_name = u.name;
  return u;
}

// ---- Sidebar Toggle ----
function initSidebar() {
  const sidebar = document.getElementById('sidebar');
  const mainContent = document.getElementById('mainContent');
  const topNavbar = document.getElementById('topNavbar');
  const toggleBtn = document.getElementById('sidebarToggle');

  if (!sidebar || !toggleBtn) return;

  const COLLAPSED_KEY = 'copsense_sidebar_collapsed';
  let isCollapsed = localStorage.getItem(COLLAPSED_KEY) === 'true';

  function applyCollapsed() {
    sidebar.classList.toggle('collapsed', isCollapsed);
    if (mainContent) mainContent.classList.toggle('sidebar-collapsed', isCollapsed);
    if (topNavbar) topNavbar.classList.toggle('sidebar-collapsed', isCollapsed);
  }
  applyCollapsed();

  toggleBtn.addEventListener('click', function () {
    isCollapsed = !isCollapsed;
    localStorage.setItem(COLLAPSED_KEY, isCollapsed);
    applyCollapsed();
  });

  document.addEventListener('click', function (e) {
    if (window.innerWidth <= 768) {
      if (!sidebar.contains(e.target) && !toggleBtn.contains(e.target)) {
        sidebar.classList.remove('mobile-open');
      }
    }
  });

  if (window.innerWidth <= 768) {
    toggleBtn.addEventListener('click', function () {
      sidebar.classList.toggle('mobile-open');
    });
  }
}

// ---- Active Nav Item ----
function setActiveNavItem() {
  const currentPage = window.location.pathname.split('/').pop() || 'dashboard.html';
  document.querySelectorAll('.nav-item[data-page]').forEach(function (item) {
    item.classList.toggle('active', item.dataset.page === currentPage);
  });
}

// ---- Live DateTime ----
function initDateTime() {
  const el = document.getElementById('navDatetime');
  if (!el) return;
  function update() {
    const now = new Date();
    el.textContent = now.toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
  }
  update();
  setInterval(update, 1000);
}

// ---- Notification Dropdown ----
function initNotifications() {
  const btn = document.getElementById('notifBtn');
  const dropdown = document.getElementById('notifDropdown');
  if (!btn || !dropdown) return;
  btn.addEventListener('click', function (e) { e.stopPropagation(); dropdown.classList.toggle('open'); });
  document.addEventListener('click', function () { dropdown.classList.remove('open'); });
}

// ---- Modal Helpers ----
function openModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) overlay.classList.add('open');
}
function closeModal(modalId) {
  const overlay = document.getElementById(modalId);
  if (overlay) overlay.classList.remove('open');
}
function initModals() {
  document.querySelectorAll('[data-modal-open]').forEach(function (btn) {
    btn.addEventListener('click', function () { openModal(btn.dataset.modalOpen); });
  });
  document.querySelectorAll('[data-modal-close]').forEach(function (btn) {
    btn.addEventListener('click', function () { closeModal(btn.dataset.modalClose); });
  });
  document.querySelectorAll('.modal-overlay').forEach(function (overlay) {
    overlay.addEventListener('click', function (e) { if (e.target === overlay) overlay.classList.remove('open'); });
  });
}

// ---- Toast Notifications ----
let toastContainer;
function showToast(message, type = 'info', duration = 3500) {
  if (!toastContainer) {
    toastContainer = document.createElement('div');
    toastContainer.id = 'toast-container';
    toastContainer.style.cssText = 'position:fixed;bottom:24px;right:24px;z-index:99999;display:flex;flex-direction:column;gap:8px;';
    document.body.appendChild(toastContainer);
  }
  const colors = {
    success: { bg: '#E8F5E9', text: '#2E7D32', border: 'rgba(46,125,50,0.25)' },
    danger: { bg: '#FFEBEE', text: '#C62828', border: 'rgba(198,40,40,0.25)' },
    warning: { bg: '#FFF8E1', text: '#7B5800', border: 'rgba(249,168,37,0.3)' },
    info: { bg: '#E3F2FD', text: '#1565C0', border: 'rgba(21,101,192,0.25)' },
  };
  const c = colors[type] || colors.info;
  const toast = document.createElement('div');
  toast.style.cssText = `background:${c.bg};color:${c.text};border:1px solid ${c.border};padding:10px 16px;border-radius:6px;font-size:13px;font-weight:500;box-shadow:0 2px 8px rgba(0,0,0,0.1);max-width:320px;animation:slideInToast 0.2s ease;font-family:'Roboto',sans-serif;`;
  toast.textContent = message;
  if (!document.getElementById('toast-style')) {
    const style = document.createElement('style');
    style.id = 'toast-style';
    style.textContent = '@keyframes slideInToast{from{opacity:0;transform:translateX(20px)}to{opacity:1;transform:translateX(0)}}';
    document.head.appendChild(style);
  }
  toastContainer.appendChild(toast);
  setTimeout(function () { toast.remove(); }, duration);
}

// ---- User Session (legacy + unified) ----
function getUser() {
  return getAuthUser();
}
function setUser(user) {
  sessionStorage.setItem('copsense_user', JSON.stringify(user));
}
function requireAuth() {
  const user = getAuthUser();
  if (!user) { window.location.href = 'index.html'; return null; }
  return user;
}
function logout() {
  if (typeof Auth !== 'undefined') Auth.clear();
  sessionStorage.removeItem('copsense_user');
  window.location.href = 'index.html';
}

// ---- Populate User Info in Navbar/Sidebar ----
function populateUserInfo() {
  const user = getAuthUser();
  if (!user) {
    ['navUserName', 'sbUserName'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = 'Guest'; });
    return;
  }

  const displayName = user.full_name || user.name || user.username || 'User';
  const roleMap = { district_head: 'District Head (SSP)', station_officer: 'Station Officer', field_officer: 'Field Officer', citizen: 'Citizen' };
  const displayRole = roleMap[user.role] || user.role || '—';

  const initials = displayName.split(' ').map(p => p[0]).join('').toUpperCase().slice(0, 2);

  ['navUserName', 'sbUserName'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = displayName; });
  ['navUserRole', 'sbUserRole'].forEach(id => { const el = document.getElementById(id); if (el) el.textContent = displayRole; });

  const avatarElements = ['navUserAvatar', 'sbUserAvatar'];
  avatarElements.forEach(id => {
    const el = document.getElementById(id);
    if (el) {
      el.textContent = initials;
      el.style.background = 'var(--secondary)';
      el.style.color = '#fff';
      el.style.display = 'flex';
      el.style.alignItems = 'center';
      el.style.justifyContent = 'center';
      el.style.fontWeight = '700';
    }
  });
}

// ---- Format Date ----
function formatDate(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}
function formatDateTime(dateStr) {
  if (!dateStr) return '—';
  return new Date(dateStr).toLocaleString('en-IN', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false });
}
function timeAgo(dateStr) {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return 'Just now';
  if (m < 60) return m + ' min ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + ' hr ago';
  return Math.floor(h / 24) + 'd ago';
}

// ---- Random ID Generator ----
function genId(prefix) { return prefix + Math.floor(1000 + Math.random() * 9000); }

// ---- CSV Export ----
function exportTableToCSV(tableId, filename) {
  const table = document.getElementById(tableId);
  if (!table) return;
  const rows = Array.from(table.querySelectorAll('tr'));
  const csv = rows.map(row =>
    Array.from(row.querySelectorAll('th,td')).map(cell => '"' + cell.textContent.replace(/"/g, '""').trim() + '"').join(',')
  ).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  a.click();
}

// ---- Chart.js default config ----
function applyChartDefaults() {
  if (typeof Chart === 'undefined') return;
  Chart.defaults.font.family = "'Roboto', Arial, sans-serif";
  Chart.defaults.font.size = 12;
  Chart.defaults.color = '#616161';
  Chart.defaults.plugins.legend.labels.boxWidth = 10;
  Chart.defaults.plugins.legend.labels.padding = 12;
  Chart.defaults.plugins.tooltip.backgroundColor = '#1F3A5F';
  Chart.defaults.plugins.tooltip.padding = 10;
  Chart.defaults.plugins.tooltip.cornerRadius = 6;
}

// ---- Form Validation Helpers ----
function showFieldError(fieldId, message) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.add('is-invalid');
  let errEl = field.parentElement.querySelector('.field-error');
  if (!errEl) {
    errEl = document.createElement('div');
    errEl.className = 'field-error';
    errEl.style.cssText = 'color:#C62828;font-size:11px;margin-top:3px;';
    field.parentElement.appendChild(errEl);
  }
  errEl.textContent = message;
}
function clearFieldError(fieldId) {
  const field = document.getElementById(fieldId);
  if (!field) return;
  field.classList.remove('is-invalid');
  const errEl = field.parentElement.querySelector('.field-error');
  if (errEl) errEl.textContent = '';
}
function clearAllErrors(formEl) {
  if (!formEl) return;
  formEl.querySelectorAll('.is-invalid').forEach(f => f.classList.remove('is-invalid'));
  formEl.querySelectorAll('.field-error').forEach(f => f.textContent = '');
}
function validatePhone(phone) {
  return /^[6-9]\d{9}$/.test(phone.replace(/\s/g, ''));
}

// ---- Init All ----
document.addEventListener('DOMContentLoaded', function () {
  enforceRBAC();
  initSidebar();
  setActiveNavItem();
  initDateTime();
  initNotifications();
  initModals();
  populateUserInfo();
  applyChartDefaults();

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) logoutBtn.addEventListener('click', logout);
});
