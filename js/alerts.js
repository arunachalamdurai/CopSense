/* ====================================================
   CopSense — alerts.js v2.0
   Smart AI Alert System — real station scores from heatmap
   ==================================================== */
'use strict';
// Auth enforced by common.js enforceRBAC()

// -------------------------------------------------------
// ALERT DATA — Fetched from backend
// -------------------------------------------------------
const ALERT_ICONS = {
  murder:    '<svg viewBox="0 0 24 24"><path d="M12 9v4"/><path d="M12 17h.01"/><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>',
  missing:   '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="17" y1="11" x2="22" y2="11"/></svg>',
  custody:   '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>',
  delay:     '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>',
  absentee:  '<svg viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><line x1="23" y1="18" x2="17" y2="18"/></svg>',
  complaint: '<svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>',
  violence:  '<svg viewBox="0 0 24 24"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/></svg>',
  resolved:  '<svg viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>',
  geofence:  '<svg viewBox="0 0 24 24"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>'
};

// Fallback station scores
const STATION_SCORES = [
  { name: 'Boring Road',   score: 72, color: '#C62828' },
  { name: 'Kankarbagh',   score: 55, color: '#F9A825' },
  { name: 'Gardanibagh',  score: 42, color: '#F9A825' },
  { name: 'Patna City',   score: 38, color: '#2E7D32' },
  { name: 'Phulwari',     score: 35, color: '#2E7D32' },
  { name: 'Sachivalaya',  score: 28, color: '#2E7D32' },
];

let activeFilter = 'all';
let alertData    = [];
let myChart      = null;

function priorityMeta(p) {
  const m = {
    critical: { label:'CRITICAL', cls:'pb-critical', iconCls:'sac-icon-critical', cardCls:'sac-critical' },
    high:     { label:'HIGH',     cls:'pb-high',     iconCls:'sac-icon-high',     cardCls:'sac-high' },
    warning:  { label:'WARNING',  cls:'pb-warning',  iconCls:'sac-icon-warning',  cardCls:'sac-warning' },
    info:     { label:'RESOLVED', cls:'pb-info',     iconCls:'sac-icon-info',     cardCls:'sac-info' },
  };
  return m[p] || m.info;
}

function timeAgoDate(dateString) {
  if (!dateString) return 'Just now';
  const min = Math.round((new Date() - new Date(dateString)) / 60000);
  if (min < 60)  return min + ' min ago';
  if (min < 1440) return Math.round(min/60) + ' hrs ago';
  return Math.round(min/1440) + ' days ago';
}

function getIconType(module_name, title) {
    title = title.toLowerCase();
    if (module_name === 'custody') return 'custody';
    if (module_name === 'duty' && title.includes('geofence')) return 'geofence';
    if (title.includes('murder') || title.includes('critical')) return 'murder';
    if (title.includes('missing')) return 'missing';
    if (title.includes('delay')) return 'delay';
    if (title.includes('complaint')) return 'complaint';
    if (title.includes('absent')) return 'absentee';
    return 'delay'; // default
}

function renderAlertCard(a) {
  const isResolved = a.status === 'resolved';
  const priority = isResolved ? 'info' : a.priority;
  const pm = priorityMeta(priority);
  const iconType = isResolved ? 'resolved' : getIconType(a.source_module, a.title);

  return `
  <div class="smart-alert-card ${pm.cardCls}" id="card-${a.id}" style="${isResolved?'opacity:.75;':''}">
    <div class="sac-icon-wrap ${pm.iconCls}">${ALERT_ICONS[iconType]||ALERT_ICONS.delay}</div>
    <div class="sac-body">
      <div class="sac-header">
        <span class="priority-badge ${pm.cls}">${pm.label}</span>
        <span class="sac-title">${a.title}</span>
      </div>
      <div class="sac-meta">
        <svg width="11" height="11" viewBox="0 0 24 24" style="stroke:#9E9E9E;fill:none;stroke-width:2;stroke-linecap:round;vertical-align:middle;"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
        ${a.source_module} &nbsp;·&nbsp;
        <svg width="11" height="11" viewBox="0 0 24 24" style="stroke:#9E9E9E;fill:none;stroke-width:2;stroke-linecap:round;vertical-align:middle;"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/></svg>
        Auto-Generated
      </div>
      <div class="sac-desc">${a.description}</div>
      <div class="sac-actions">
        ${!isResolved ? `<button class="btn btn-sm btn-${priority==='critical'?'danger':'secondary'}" onclick="resolveAlert('${a.id}')">Mark Resolved</button>` : '<span class="badge badge-success">Resolved</span>'}
        <a href="${a.source_module + '.html'}" class="btn btn-sm btn-secondary">View Details</a>
      </div>
    </div>
    <div class="sac-time">${timeAgoDate(a.created_at)}</div>
  </div>`;
}

function renderFeed() {
  const feed = document.getElementById('alertFeed');
  let data = alertData;
  if (activeFilter !== 'all') {
    if (activeFilter === 'critical' || activeFilter === 'high' || activeFilter === 'warning') {
        data = alertData.filter(a => a.priority === activeFilter && a.status !== 'resolved');
    } else {
        data = alertData.filter(a => a.source_module === activeFilter || a.source_module === activeFilter.toUpperCase());
    }
  }
  if (!data.length) {
    feed.innerHTML = '<div class="table-empty" style="padding:48px;"><svg viewBox="0 0 24 24" style="width:48px;height:48px;stroke:var(--border);fill:none;stroke-width:1;"><polyline points="20 6 9 17 4 12"/></svg><br/>No alerts match this filter.</div>';
    return;
  }
  feed.innerHTML = data.map(renderAlertCard).join('');
  document.getElementById('feedCount').textContent = `${data.length} alert${data.length!==1?'s':''} — ${data.filter(a=>a.status!=='resolved').length} unresolved`;
  document.getElementById('nbAlertCount').textContent = alertData.filter(a=>a.status!=='resolved').length;
}

function updateStats() {
  document.getElementById('sc-critical').textContent = alertData.filter(a=>a.priority==='critical'&&a.status!=='resolved').length;
  document.getElementById('sc-high').textContent     = alertData.filter(a=>a.priority==='high'&&a.status!=='resolved').length;
  document.getElementById('sc-warnings').textContent = alertData.filter(a=>a.priority==='warning'&&a.status!=='resolved').length;
  document.getElementById('sc-resolved').textContent = alertData.filter(a=>a.status==='resolved').length;
}

async function renderStationScores() {
  const wrap = document.getElementById('stationScores');
  if (!wrap) return;
  try {
    const res = await HeatmapAPI.alertColors(30);
    const zones = res.data || STATION_SCORES;
    wrap.innerHTML = zones.map(s => {
      const score = s.score || s.total_incidents || 0;
      const color = s.color || (score >= 60 ? 'var(--danger)' : score >= 40 ? '#F9A825' : 'var(--success)');
      const maxScore = Math.max(...zones.map(z => z.score || z.total_incidents || 1));
      const pct = Math.min(100, Math.round((score / maxScore) * 100));
      return `<div class="score-bar-row">
        <div class="score-station">${s.name || s.station_name}</div>
        <div class="score-bar-wrap"><div class="score-bar-fill" style="width:${pct}%;background:${color};"></div></div>
        <div class="score-num" style="color:${color};">${score}</div>
      </div>`;
    }).join('');
  } catch(err) {
    // Fallback to hardcoded
    wrap.innerHTML = STATION_SCORES.map(s => {
      const cls = s.score >= 60 ? 'var(--danger)' : s.score >= 45 ? '#F9A825' : 'var(--success)';
      return `<div class="score-bar-row">
        <div class="score-station">${s.name}</div>
        <div class="score-bar-wrap"><div class="score-bar-fill" style="width:${s.score}%;background:${cls};"></div></div>
        <div class="score-num" style="color:${cls};">${s.score}</div>
      </div>`;
    }).join('');
  }
}

async function resolveAlert(id) {
  try {
      await AlertsAPI.resolve(id);
      const a = alertData.find(x=>String(x.id)===String(id));
      if (a) a.status = 'resolved';
      renderFeed();
      updateStats();
      updateDonut();
      showToast('Alert marked as resolved.', 'success');
  } catch(err) {
      showToast('Failed to resolve alert: ' + err.message, 'danger');
  }
}

function updateDonut() {
    if (!myChart) return;
    myChart.data.datasets[0].data = [
        alertData.filter(a=>a.priority==='critical' && a.status!=='resolved').length,
        alertData.filter(a=>a.priority==='high' && a.status!=='resolved').length,
        alertData.filter(a=>a.priority==='warning' && a.status!=='resolved').length,
        alertData.filter(a=>a.status==='resolved').length,
    ];
    myChart.update();
}

function initDonut() {
  const ctx = document.getElementById('alertDonut');
  if(!ctx) return;
  myChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Critical','High Priority','Warnings','Resolved'],
      datasets: [{
        data: [0,0,0,0],
        backgroundColor: ['#C62828','#F9A825','#1565C0','#2E7D32'],
        borderWidth: 2, borderColor: '#fff',
      }],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      cutout: '60%',
      plugins: { legend: { position: 'bottom', labels: { font: { size: 11 } } } },
    },
  });
}

// -------------------------------------------------------
// BACKEND SYNC & AUTO-REFRESH
// -------------------------------------------------------
async function loadAlerts() {
    try {
        const res = await AlertsAPI.list();
        alertData = res.data || [];
        // Sort: unresolved first, then by priority, then date
        alertData.sort((a,b) => {
            if (a.status !== b.status) return a.status === 'resolved' ? 1 : -1;
            const pMap = { critical:0, high:1, warning:2, info:3 };
            if (pMap[a.priority] !== pMap[b.priority]) return pMap[a.priority] - pMap[b.priority];
            return new Date(b.created_at) - new Date(a.created_at);
        });
        
        renderFeed();
        updateStats();
        updateDonut();
    } catch(err) {
        showToast('Error loading alerts: ' + err.message, 'danger');
    }
}

let countdown = 30;
function startCountdown() {
  const fill = document.getElementById('refreshFill');
  const label = document.getElementById('refreshCountdown');
  
  if(!fill || !label) return;
  
  const iv = setInterval(async function() {
    countdown--;
    const pct = (countdown / 30) * 100;
    fill.style.width = pct + '%';
    label.textContent = 'Next refresh in ' + countdown + 's';
    if (countdown <= 0) {
      countdown = 30;
      // Trigger AI scan
      try {
          await AlertsAPI.scan();
          await loadAlerts();
      } catch(ignore) {}
    }
  }, 1000);
  return iv;
}

// -------------------------------------------------------
// INIT
// -------------------------------------------------------
document.addEventListener('DOMContentLoaded', async function() {
    if (Auth.isLoggedIn()) {
        initDonut();
        renderStationScores();
        await loadAlerts();
        startCountdown();
    }

  // Filter tabs
  document.querySelectorAll('.filter-tab').forEach(function(tab) {
    tab.addEventListener('click', function() {
      document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      activeFilter = this.dataset.filter;
      renderFeed();
    });
  });

  // Refresh button
  const refreshBtn = document.getElementById('refreshBtn');
  if(refreshBtn) {
      refreshBtn.addEventListener('click', async function() {
        this.disabled = true;
        countdown = 30;
        const fill = document.getElementById('refreshFill');
        if(fill) fill.style.width = '100%';
        try {
            await AlertsAPI.scan();
            await loadAlerts();
            showToast('Alerts refreshed and scanned by AI engine.', 'success');
        } catch(err) {
            showToast('Scan failed: ' + err.message, 'danger');
        } finally {
            this.disabled = false;
        }
      });
  }

  // Mark all read button (client-sided resolution shortcut)
  const markAllBtn = document.getElementById('markAllBtn');
  if(markAllBtn) {
      markAllBtn.addEventListener('click', async function() {
        this.disabled = true;
        try {
            const unresolved = alertData.filter(a => a.status !== 'resolved');
            for(const a of unresolved) {
                await AlertsAPI.resolve(a.id);
            }
            await loadAlerts();
            showToast('All alerts marked as resolved.', 'success');
        } catch(err) {
            showToast('Failed to resolve all: ' + err.message, 'danger');
        } finally {
            this.disabled = false;
        }
      });
  }
});
