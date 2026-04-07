/**
 * CopSense — Frontend API Client v2.1
 * All calls to the FastAPI backend go through this module.
 * Auth stored in localStorage only (unified — no sessionStorage split).
 */

const API_BASE = 'http://localhost:8000';

// ── Token Storage ─────────────────────────────────────────────────────────────
const Auth = {
  getToken  : ()         => localStorage.getItem('copsense_token'),
  setToken  : (t)        => localStorage.setItem('copsense_token', t),
  getUser   : ()         => JSON.parse(localStorage.getItem('copsense_user') || 'null'),
  setUser   : (u)        => localStorage.setItem('copsense_user', JSON.stringify(u)),
  clear     : ()         => { localStorage.removeItem('copsense_token'); localStorage.removeItem('copsense_user'); sessionStorage.removeItem('copsense_user'); },
  isLoggedIn: ()         => !!Auth.getToken() && !!Auth.getUser(),
  hasRole   : (...roles) => { const u = Auth.getUser(); return u && roles.includes(u.role); },
  isCitizen : ()         => Auth.hasRole('citizen'),
  isOfficer : ()         => Auth.hasRole('field_officer', 'station_officer', 'district_head'),
  isHead    : ()         => Auth.hasRole('district_head'),
};

// ── Core fetch wrapper ─────────────────────────────────────────────────────────
async function apiCall(endpoint, options = {}) {
  const token = Auth.getToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
    ...(options.headers || {}),
  };
  if (options.body instanceof FormData) {
    delete headers['Content-Type'];
  }
  const response = await fetch(`${API_BASE}${endpoint}`, { ...options, headers });

  if (response.status === 401) {
    Auth.clear();
    if (!window.location.pathname.includes('index.html') && !window.location.pathname.includes('register.html')) {
      window.location.href = 'index.html';
    }
    throw new Error('Session expired. Please log in again.');
  }
  if (response.status === 204) return null;

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const msg = data.detail || data.message || `API Error ${response.status}`;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

// ── Auth API ──────────────────────────────────────────────────────────────────
function _roleLabel(role) {
  const map = { district_head:'District Head (SSP)', station_officer:'Station Officer', field_officer:'Field Officer', citizen:'Citizen' };
  return map[role] || role;
}

const AuthAPI = {
  async login(username, password) {
    const data = await apiCall('/api/auth/login', { method:'POST', body: JSON.stringify({ username, password }) });
    Auth.setToken(data.access_token);
    Auth.setUser(data.user);
    sessionStorage.setItem('copsense_user', JSON.stringify({
      name: data.user.full_name, role: _roleLabel(data.user.role),
      id: data.user.id, username: data.user.username,
      badge_id: data.user.badge_id, station_id: data.user.station_id,
      station_name: data.user.station_name,
    }));
    return data.user;
  },
  async me() { return apiCall('/api/auth/me'); },
  async register(payload) { return apiCall('/api/auth/register', { method:'POST', body: JSON.stringify(payload) }); },
  async changePassword(oldPwd, newPwd) {
    return apiCall('/api/auth/change-password', { method:'PUT', body: JSON.stringify({ old_password:oldPwd, new_password:newPwd }) });
  },
  logout() { Auth.clear(); sessionStorage.clear(); window.location.href = 'index.html'; },
};

// ── Dashboard API ─────────────────────────────────────────────────────────────
const DashboardAPI = {
  stats:      ()      => apiCall('/api/dashboard/stats'),
  recentFIRs: (limit) => apiCall(`/api/dashboard/recent-firs?limit=${limit||8}`),
};

// ── FIR API ───────────────────────────────────────────────────────────────────
const FIRAPI = {
  list:   (params={}) => apiCall('/api/fir?' + new URLSearchParams(params)),
  get:    (id)        => apiCall(`/api/fir/${id}`),
  create: (payload)   => apiCall('/api/fir', { method:'POST', body: JSON.stringify(payload) }),
  update: (id,payload)=> apiCall(`/api/fir/${id}`, { method:'PUT', body: JSON.stringify(payload) }),
  delete: (id)        => apiCall(`/api/fir/${id}`, { method:'DELETE' }),
  stats:  ()          => apiCall('/api/fir/stats'),
};

// ── Complaints API ────────────────────────────────────────────────────────────
const ComplaintsAPI = {
  list:         (params={}) => apiCall('/api/complaints?' + new URLSearchParams(params)),
  create:       (payload)   => apiCall('/api/complaints', { method:'POST', body: JSON.stringify(payload) }),
  updateStatus: (id,payload)=> apiCall(`/api/complaints/${id}/status`, { method:'PUT', body: JSON.stringify(payload) }),
  stats:        ()          => apiCall('/api/complaints/stats'),
};

// ── Custody API ───────────────────────────────────────────────────────────────
const CustodyAPI = {
  list:         ()           => apiCall('/api/custody'),
  create:       (payload)    => apiCall('/api/custody', { method:'POST', body: JSON.stringify(payload) }),
  healthUpdate: (id,payload) => apiCall(`/api/custody/${id}/update`, { method:'PUT', body: JSON.stringify(payload) }),
  uploadVideo:  (id,fd)      => apiCall(`/api/custody/${id}/video`, { method:'POST', body: fd }),
  alerts:       ()           => apiCall('/api/custody/alerts'),
};

// ── Feedback API ──────────────────────────────────────────────────────────────
const FeedbackAPI = {
  submit: (payload)    => apiCall('/api/feedback', { method:'POST', body: JSON.stringify(payload) }),
  list:   (params={})  => apiCall('/api/feedback?' + new URLSearchParams(params)),
  stats:  ()           => apiCall('/api/feedback/stats'),
};

// ── Alerts API ────────────────────────────────────────────────────────────────
const AlertsAPI = {
  list:    (params={}) => apiCall('/api/alerts?' + new URLSearchParams(params)),
  resolve: (id)        => apiCall(`/api/alerts/${id}/resolve`, { method:'POST' }),
  scan:    ()          => apiCall('/api/alerts/scan', { method:'POST' }),
  stats:   ()          => apiCall('/api/alerts/stats'),
};

// ── Duty API ──────────────────────────────────────────────────────────────────
const DutyAPI = {
  list:          ()           => apiCall('/api/duty'),
  myAssignments: ()           => apiCall('/api/duty/my-assignments'),
  assign:        (payload)    => apiCall('/api/duty', { method:'POST', body: JSON.stringify(payload) }),
  submitGPS:     (id,payload) => apiCall(`/api/duty/${id}/gps`, { method:'POST', body: JSON.stringify(payload) }),
  violations:    ()           => apiCall('/api/duty/violations'),
};

// ── Heatmap API ───────────────────────────────────────────────────────────────
const HeatmapAPI = {
  points:      (days=30) => apiCall(`/api/heatmap?days=${days}`),
  zones:       (days=30) => apiCall(`/api/heatmap/zones?days=${days}`),
  alertColors: (days=30) => apiCall(`/api/heatmap/alert-colors?days=${days}`),
};

// ── Emergency API ─────────────────────────────────────────────────────────────
const EmergencyAPI = {
  nearest:  (payload) => apiCall('/api/emergency/nearest', { method:'POST', body: JSON.stringify(payload) }),
  dispatch: (payload) => apiCall('/api/emergency/dispatch', { method:'POST', body: JSON.stringify(payload) }),
};

// ── Crowd Planning API ─────────────────────────────────────────────────────────
const CrowdAPI = {
  analyze: (payload) => apiCall('/api/crowd-planning/analyze', { method:'POST', body: JSON.stringify(payload) }),
  list:    ()        => apiCall('/api/crowd-planning'),
  deploy:  (id)      => apiCall(`/api/crowd-planning/${id}/deploy`, { method:'POST' }),
};

// ── Stations API (public listings — no auth header needed for GET) ───────────
const StationsAPI = {
  list:     ()   => fetch(`${API_BASE}/api/stations`).then(r => r.json()),
  get:      (id) => fetch(`${API_BASE}/api/stations/${id}`).then(r => r.json()),
  officers: (id) => fetch(`${API_BASE}/api/stations/${id}/officers`).then(r => r.json()),
};

// ── Export to global scope ────────────────────────────────────────────────────
window.Auth          = Auth;
window.apiCall       = apiCall;
window.AuthAPI       = AuthAPI;
window.DashboardAPI  = DashboardAPI;
window.FIRAPI        = FIRAPI;
window.ComplaintsAPI = ComplaintsAPI;
window.CustodyAPI    = CustodyAPI;
window.FeedbackAPI   = FeedbackAPI;
window.AlertsAPI     = AlertsAPI;
window.DutyAPI       = DutyAPI;
window.HeatmapAPI    = HeatmapAPI;
window.EmergencyAPI  = EmergencyAPI;
window.CrowdAPI      = CrowdAPI;
window.StationsAPI   = StationsAPI;
