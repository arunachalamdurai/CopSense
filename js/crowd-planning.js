/* =========================================
   CopSense — crowd-planning.js (API Connected)
   AI Crowd Risk Prediction Engine
   ========================================= */
'use strict';
(function(){ const u=JSON.parse(sessionStorage.getItem('copsense_user')||'null'); if(!u) window.location.href='index.html'; })();

let eventHistory = [];

async function fetchHistory() {
  try {
    const res = await CrowdAPI.list();
    eventHistory = res.data || [];
    renderHistory();
  } catch (err) {
    showToast('Failed to load past AI plans: ' + err.message, 'danger');
  }
}

async function runAIAnalysis() {
  const name       = document.getElementById('evtName').value.trim();
  const type       = document.getElementById('evtType').value;
  const date       = document.getElementById('evtDate').value;
  const location   = document.getElementById('evtLocation').value.trim();
  const crowd      = parseInt(document.getElementById('evtCrowd').value) || 0;
  const duration   = parseInt(document.getElementById('evtDuration').value) || 4;
  const incidents  = parseInt(document.getElementById('evtIncidents').value) || 0;
  const vip        = parseInt(document.getElementById('evtVIP').value) || 0;

  if (!name || !type || !date || !location || crowd < 100) {
    showToast('Please fill in all required fields with valid crowd size.', 'danger');
    return;
  }

  // Determine risk level purely for input based on the js heuristic (backend overrides with calculate_risk_score but nice to provide base)
  let baseRisk = 'medium';
  if (crowd > 50000 || incidents >= 3) baseRisk = 'high';
  else if (crowd < 5000 && incidents === 0 && !vip) baseRisk = 'low';

  const payload = {
      name: name,
      location: location,
      lat: 25.603, // Defaulting to Patna
      lng: 85.133,
      event_date: new Date(date).toISOString(),
      crowd_size: crowd,
      duration_hrs: duration,
      risk_level: baseRisk,
      event_type: type,
      vip_presence: vip === 1,
      past_incidents: incidents,
      station_id: 1 // Default to Patna City for now
  };

  const btn = document.getElementById('analyzeBtn');
  btn.disabled = true;
  btn.innerHTML = '<svg viewBox="0 0 24 24" style="width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round" class="spin"><circle cx="12" cy="12" r="10"/><path d="M12 2a10 10 0 0 1 10 10"/></svg> Analyzing...';

  try {
      const res = await CrowdAPI.analyze(payload);
      
      const bp = res.blueprint;
      const riskScore = res.risk_score;
      let riskClass, riskLevel;
      if (riskScore >= 7) { riskClass = 'risk-high'; riskLevel = 'High'; }
      else if (riskScore >= 4) { riskClass = 'risk-medium'; riskLevel='Medium'; }
      else { riskClass = 'risk-low'; riskLevel='Low'; }

      // Show results
      document.getElementById('aiNoResult').style.display  = 'none';
      document.getElementById('aiResultPanel').style.display = 'block';

      document.getElementById('aiEventLabel').textContent  = name + ' · ' + date;
      document.getElementById('aiRiskBadge').textContent   = 'Risk Level: ' + riskLevel;
      document.getElementById('aiRiskBadge').className     = 'risk-meter ' + riskClass;
      
      const p = bp.personnel || {};
      document.getElementById('aiPolice').textContent      = p.total_officers || 0;
      document.getElementById('aiAmbulance').textContent   = p.ambulances || 0;
      document.getElementById('aiBarricades').textContent  = (bp.crowd_control && bp.crowd_control.barricades) || 0;
      document.getElementById('aiVenues').textContent      = (bp.crowd_control && bp.crowd_control.cctv) || 0;

      const venueSuit = Math.max(30, 100 - riskScore*10);
      document.getElementById('venueScore').textContent    = venueSuit + '%';
      document.getElementById('venueFill').style.width     = venueSuit + '%';
      document.getElementById('venueFill').style.background = venueSuit >= 70 ? 'var(--success)' : venueSuit >= 50 ? 'var(--warning)' : 'var(--danger)';
      
      document.getElementById('aiRemarks').innerHTML       = bp.remarks.map(r => `<div style="margin-bottom:4px;">&#8226; ${r}</div>`).join('');

      // Enable deploy button logic
      document.getElementById('saveEventPlanBtn').dataset.eventId = res.event_id;
      document.getElementById('saveEventPlanBtn').textContent = 'Deploy Event Patrols';
      document.getElementById('saveEventPlanBtn').className = 'btn btn-primary';
      document.getElementById('saveEventPlanBtn').disabled = false;
      
      // Update history table so the new save is visible right away
      await fetchHistory();

      showToast('AI Analysis Complete', 'success');

  } catch(err) {
      showToast('AI Error: ' + err.message, 'danger');
  } finally {
      btn.disabled = false;
      btn.innerHTML = '<svg viewBox="0 0 24 24" style="width:18px;height:18px;stroke:currentColor;fill:none;stroke-width:2;stroke-linecap:round"><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/><line x1="2" y1="12" x2="22" y2="12"/></svg> Run AI Analysis';
  }
}

async function saveEventPlan() {
  const btn = document.getElementById('saveEventPlanBtn');
  const eid = btn.dataset.eventId;
  if (!eid) return;

  btn.disabled = true;
  btn.textContent = 'Deploying...';
  
  try {
      const res = await CrowdAPI.deploy(eid);
      showToast(res.message, 'success');
      btn.textContent = '✓ Deployed to Duty Roster';
      btn.className = 'btn btn-success';
      await fetchHistory();
  } catch(err) {
      showToast('Deployment Failed: ' + err.message, 'danger');
      btn.disabled = false;
      btn.textContent = 'Deploy Event Patrols';
  }
}

function renderHistory() {
  const tbody = document.getElementById('eventHistoryBody');
  if (!eventHistory.length) {
    tbody.innerHTML = '<tr><td colspan="7"><div class="table-empty">No plans yet.</div></td></tr>';
    return;
  }
  tbody.innerHTML = eventHistory.map(e => {
    let pol = 0; let r = 'Medium';
    if(e.ai_blueprint) {
      pol = e.ai_blueprint.personnel ? e.ai_blueprint.personnel.total_officers : 0;
    }
    if(e.risk_score >= 7) r = 'High'; else if (e.risk_score < 4) r = 'Low';
    
    return `
    <tr>
      <td class="td-bold">${e.name}</td>
      <td>${e.event_type || 'Unknown'}</td>
      <td>${(e.event_date||'').split('T')[0]}</td>
      <td>${e.location}</td>
      <td>${(e.crowd_size||0).toLocaleString()}</td>
      <td>${pol}</td>
      <td>${r === 'High' ? '<span class="badge badge-danger">High</span>' : r==='Medium'?'<span class="badge badge-warning">Medium</span>':'<span class="badge badge-success">Low</span>'}</td>
    </tr>
    `
  }).join('');
}

document.addEventListener('DOMContentLoaded', async function() {
  if (Auth.isLoggedIn()) {
      await fetchHistory();
  }
  document.getElementById('evtDate').value = new Date().toISOString().slice(0,10);
  document.getElementById('analyzeBtn').addEventListener('click', runAIAnalysis);
  document.getElementById('saveEventPlanBtn').addEventListener('click', saveEventPlan);
  // Add CSS animation for spinning loading icon
  const style = document.createElement('style');
  style.textContent = '@keyframes spin { 100% { transform: rotate(360deg); } } .spin { animation: spin 1s linear infinite; }';
  document.head.appendChild(style);
});
