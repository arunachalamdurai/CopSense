/* =========================================
   CopSense — complaints.js v2.0
   Full form validation + NLP preview
   ========================================= */
'use strict';

const HIGH_KEYWORDS = ['urgent','assault','threat','missing','violence','attack','rape','murder','abduct','kidnap','harass','terror'];
function aiPriority(text) {
  const t = text.toLowerCase();
  return HIGH_KEYWORDS.some(k => t.includes(k)) ? 'High' : 'Normal';
}

const STATION_MAP = {
  'Patna City': 1, 'Kankarbagh': 2, 'Gardanibagh': 3, 'Boring Road': 4, 'Phulwari': 5, 'Sachivalaya': 6
};

let cmpData = [];
let filteredCmp = [];
let cmpPage = 1;
const CMP_PS = 10;

function cmpErr(fieldId, msg) {
  const el = document.getElementById('err-' + fieldId);
  if (el) el.textContent = msg;
  const f = document.getElementById(fieldId);
  if (f) f.classList.add('is-invalid');
}
function cmpClear(fieldId) {
  const el = document.getElementById('err-' + fieldId);
  if (el) el.textContent = '';
  const f = document.getElementById(fieldId);
  if (f) f.classList.remove('is-invalid');
}

function applyCmpFilters() {
  const s  = document.getElementById('cmpSearch')?.value.toLowerCase() || '';
  const st = document.getElementById('cmpStatus')?.value || '';
  const p  = document.getElementById('cmpPriority')?.value || '';
  filteredCmp = cmpData.filter(c => {
    return (!s  || (c.id||'').toString().includes(s)||(c.citizen_name||'').toLowerCase().includes(s)||(c.complaint_type||'').toLowerCase().includes(s))
        && (!st || c.status === st)
        && (!p  || c.priority === p);
  });
  cmpPage = 1;
  renderCmpTable();
}

function getStatusBadge(s) {
  const m = { 'open':'badge-danger','in_progress':'badge-warning','resolved':'badge-success','escalated':'badge-info','closed':'badge-neutral' };
  return `<span class="badge ${m[s]||'badge-neutral'}">${s||'open'}</span>`;
}

function renderCmpTable() {
  const tbody = document.getElementById('cmpTableBody');
  if (!tbody) return;
  const start = (cmpPage-1)*CMP_PS, end = start+CMP_PS;
  const page  = filteredCmp.slice(start, end);
  if (!page.length) {
    tbody.innerHTML = '<tr><td colspan="8"><div class="table-empty">No complaints match your filters.</div></td></tr>';
    return;
  }
  tbody.innerHTML = page.map((c, i) => `
    <tr>
      <td class="td-id">${c.id || '—'}</td>
      <td>${(c.date||c.filed_at||'').split('T')[0]}</td>
      <td class="td-bold">${c.citizen_name || 'Citizen'}</td>
      <td>${c.complaint_type}</td>
      <td>${c.station_name || '—'}</td>
      <td>${['critical','high'].includes(c.priority) ? `<span class="badge badge-danger">${c.priority}</span>` : `<span class="badge badge-neutral">${c.priority||'normal'}</span>`}</td>
      <td>${getStatusBadge(c.status)}</td>
      <td><button class="btn btn-sm btn-secondary" onclick="cycleStatus(${start+i})">Update</button></td>
    </tr>
  `).join('');
  const tot = filteredCmp.length;
  ['cmpPageInfo'].forEach(id => { const el = document.getElementById(id); if(el) el.textContent = `Showing ${start+1}–${Math.min(end,tot)} of ${tot}`; });
  const prevEl = document.getElementById('cmpPrev'); if(prevEl) prevEl.disabled = cmpPage===1;
  const nextEl = document.getElementById('cmpNext'); if(nextEl) nextEl.disabled = end>=tot;
}

async function cycleStatus(idx) {
  const cycle = ['open','in_progress','resolved','escalated'];
  const c = filteredCmp[idx];
  const next = cycle[(cycle.indexOf(c.status)+1)%cycle.length];
  try {
    await ComplaintsAPI.updateStatus(c.id, { status: next });
    c.status = next;
    renderCmpTable();
    showToast('Status updated → ' + next, 'success');
  } catch(e) {
    showToast('Failed: ' + e.message, 'danger');
  }
}

async function fetchComplaints() {
  try {
    const res = await ComplaintsAPI.list({ per_page: 100 });
    cmpData = res.data || [];
    filteredCmp = [...cmpData];
    renderCmpTable();
  } catch(err) {
    showToast('Error loading complaints: ' + err.message, 'danger');
  }
}

document.addEventListener('DOMContentLoaded', async function() {
  if (typeof Auth !== 'undefined' && Auth.isLoggedIn()) {
    await fetchComplaints();
  }

  ['cmpSearch','cmpStatus','cmpPriority'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener(id==='cmpSearch'?'input':'change', applyCmpFilters);
  });

  const prevEl = document.getElementById('cmpPrev');
  const nextEl = document.getElementById('cmpNext');
  if (prevEl) prevEl.addEventListener('click', () => { if(cmpPage>1){cmpPage--;renderCmpTable();} });
  if (nextEl) nextEl.addEventListener('click', () => { if(cmpPage*CMP_PS<filteredCmp.length){cmpPage++;renderCmpTable();} });

  const descEl = document.getElementById('cmpDesc');
  if (descEl) descEl.addEventListener('input', function() {
    const prev = document.getElementById('aiPriorityPreview');
    if (!prev) return;
    const p = aiPriority(this.value);
    prev.style.display = this.value.length > 5 ? 'block' : 'none';
    if (this.value.length > 5) {
      prev.innerHTML = p === 'High'
        ? '<div class="alert alert-danger"><strong>AI: HIGH PRIORITY</strong> — Contains urgent keywords. Will be escalated.</div>'
        : '<div class="alert alert-info">AI Classification: <strong>Normal Priority</strong></div>';
    }
  });

  const saveBtn = document.getElementById('saveComplaintBtn');
  if (saveBtn) saveBtn.addEventListener('click', async function() {
    ['cmpName','cmpPhone','cmpType','cmpStation','cmpDesc'].forEach(cmpClear);

    const name    = (document.getElementById('cmpName')?.value || '').trim();
    const phone   = (document.getElementById('cmpPhone')?.value || '').trim();
    const type    = document.getElementById('cmpType')?.value || '';
    const staName = document.getElementById('cmpStation')?.value || '';
    const desc    = (document.getElementById('cmpDesc')?.value || '').trim();
    const loc     = (document.getElementById('cmpLocation')?.value || '').trim();

    let valid = true;
    if (!name || name.length < 2) { cmpErr('cmpName', 'Name must be at least 2 characters.'); valid = false; }
    if (phone && !/^[6-9]\d{9}$/.test(phone.replace(/\s/g,''))) { cmpErr('cmpPhone', 'Enter a valid 10-digit Indian mobile number.'); valid = false; }
    if (!type) { cmpErr('cmpType', 'Please select complaint type.'); valid = false; }
    if (!staName) { cmpErr('cmpStation', 'Please select a police station.'); valid = false; }
    if (!desc || desc.length < 20) { cmpErr('cmpDesc', 'Description must be at least 20 characters.'); valid = false; }
    if (!valid) return;

    const payload = {
      citizen_name:   name,
      phone:          phone || null,
      complaint_type: type,
      description:    desc,
      location:       loc || 'Patna',
      station_id:     STATION_MAP[staName] || 1,
    };

    this.disabled = true; this.textContent = 'Submitting…';
    try {
      await ComplaintsAPI.create(payload);
      showToast('Complaint submitted successfully.', 'success');
      closeModal('addComplaintModal');
      ['cmpName','cmpPhone','cmpType','cmpStation','cmpDesc','cmpLocation'].forEach(id => { const el = document.getElementById(id); if(el) el.value = ''; });
      const prevEl = document.getElementById('aiPriorityPreview'); if(prevEl) prevEl.style.display = 'none';
      await fetchComplaints();
    } catch(err) {
      showToast(err.message, 'danger');
    } finally {
      this.disabled = false; this.textContent = 'Submit Complaint';
    }
  });
});

window.cycleStatus = cycleStatus;
