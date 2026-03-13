/* ═══════════════════════════════════════════════════════
   HR MAIL AUTOMATION — dashboard.js
   ═══════════════════════════════════════════════════════ */

// ── State ─────────────────────────────────────────────────
let recPage = 1;
let recTotal = 0;
let recSearch = '';
let lastLogCount = 0;
let searchTimer = null;
const PER_PAGE = 50;


// ═══════════════════════════════════════════════════════════
//                        TABS
// ═══════════════════════════════════════════════════════════

function switchTab(id, el) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  el.classList.add('active');
  document.getElementById('tab-' + id).classList.add('active');
  if (id === 'records') loadRecords();
}


// ═══════════════════════════════════════════════════════════
//                   POLLING — Live Updates
// ═══════════════════════════════════════════════════════════

async function pollStatus() {
  try {
    const res = await fetch('/api/status');
    const data = await res.json();
    document.getElementById('connErr').classList.remove('show');
    updateDashboard(data);
  } catch (e) {
    document.getElementById('connErr').classList.add('show');
    setStatusPill('error', 'Server Offline');
  }
}

function startPolling() {
  pollStatus();
  setInterval(pollStatus, 800);
}


// ═══════════════════════════════════════════════════════════
//                   UPDATE DASHBOARD
// ═══════════════════════════════════════════════════════════

function updateDashboard(d) {
  const total = d.total || 0;
  const sent = d.sent || 0;
  const failed = d.failed || 0;
  const pending = d.pending || 0;
  const pct = total > 0 ? Math.min(100, Math.round((sent / total) * 100)) : 0;
  const limit = d.config?.daily_limit || 50;
  const daysLeft = pending > 0 ? Math.ceil(pending / limit) : 0;

  // ── Stat Cards ──
  setText('stTotal', total.toLocaleString());
  setText('stSent', (d.all_time_sent || sent).toLocaleString());
  setText('stFailed', failed.toLocaleString());
  setText('stDuplicate', (d.duplicates || 0).toLocaleString());
  setText('stPending', pending.toLocaleString());
  setText('stToday', (d.today_sent || 0).toLocaleString());
  setText('stTodayFail', `${d.today_failed || 0} failed today`);
  setText('stDays', `~${daysLeft} days to finish`);

  // ── Progress Bar ──
  setText('progPct', pct + '%');
  document.getElementById('progBar').style.width = pct + '%';
  setText('progLeft', `${pending.toLocaleString()} remaining`);

  const estDate = new Date();
  estDate.setDate(estDate.getDate() + daysLeft);
  setText('progEst', `Est. finish: ${estDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`);

  // ── Status Pill ──
  const statusMap = { running: 'running', paused: 'paused', done: 'done', error: 'error', idle: 'idle' };
  const statusTxt = { running: '● Sending...', paused: '⏸ Paused', done: '✓ Done', error: '⚠ Error', idle: 'Ready' };
  setStatusPill(statusMap[d.status] || 'idle', statusTxt[d.status] || 'Ready');

  // ── Timer ──
  const timer = d.timer || d.timer_remaining || 0;
  if (timer > 0) {
    const m = Math.floor(timer / 60);
    const s = timer % 60;
    setText('timerVal', `${pad(m)}:${pad(s)}`);
    setText('timerSub', 'until next email');
  } else {
    setText('timerVal', '--:--');
    setText('timerSub', d.status === 'running' ? 'Sending now...' : 'Not running');
  }

  const ce = d.current || d.current_email || '';
  setText('curEmail', ce.length > 28 ? ce.substring(0, 25) + '…' : ce);

  // ── Config Display ──
  if (d.config) {
    const c = d.config;
    setText('cfgEmail', c.email_address ? truncate(c.email_address, 20) : 'not set');
    setText('cfgName', c.your_name || 'not set');
    setText('cfgLimit', (c.daily_limit || 50) + ' / day');
    setText('cfgDelay', `${c.delay_min || 60}–${c.delay_max || 120} sec`);
    setText('cfgExcel', c.excel_file || 'hr_emails.xlsx');
    setText('cfgResume', c.resume_file || 'resume.pdf');
  }
  setText('cfgLast', d.last_run || 'Never');

  // ── Buttons ──
  const running = d.status === 'running';
  const paused = d.status === 'paused';
  const done = d.status === 'done';
  const active = running || paused;

  const btnStart = document.getElementById('btnStart');
  const btnPause = document.getElementById('btnPause');
  const btnStop = document.getElementById('btnStop');

  // Start button
  btnStart.disabled = active;
  if (running) {
    btnStart.textContent = '⏳ Sending...';
    btnStart.style.opacity = '0.5';
    btnStart.style.cursor = 'not-allowed';
  } else if (paused) {
    btnStart.textContent = '⏸ Paused';   // ← Resume nahi, Paused
    btnStart.style.opacity = '0.5';
    btnStart.style.cursor = 'not-allowed';
    btnStart.disabled = true;           // ← disabled

    btnPause.textContent = '▶ Resume';    // ← Pause button pe Resume
    btnPause.disabled = false;
    btnPause.style.opacity = '1';
  } else if (done) {
    btnStart.textContent = '✓ Done — Start Again';
    btnStart.style.opacity = '1';
    btnStart.style.cursor = 'pointer';
  } else {
    btnStart.textContent = '▶ Start Campaign';
    btnStart.style.opacity = '1';
    btnStart.style.cursor = 'pointer';
  }

  // Pause button
  btnPause.disabled = !active;
  btnPause.style.opacity = active ? '1' : '0.4';
  btnPause.textContent = paused ? '▶ Resume' : '⏸ Pause';
  if (paused) {
    btnPause.style.borderColor = 'var(--green)';
    btnPause.style.color = 'var(--green)';
  } else {
    btnPause.style.borderColor = '';
    btnPause.style.color = '';
  }

  // Stop button
  btnStop.disabled = !active;
  btnStop.style.opacity = active ? '1' : '0.4';

  // ── Logs ──
  renderLogs(d.logs || []);

  // ── Batch ──
  renderBatch(d.batch || [], limit, d.today_sent || 0);
}


// ═══════════════════════════════════════════════════════════
//                    RENDER: LOG FEED
// ═══════════════════════════════════════════════════════════

function renderLogs(logs) {
  if (logs.length === lastLogCount) return;
  lastLogCount = logs.length;

  const icons = { success: '✅', fail: '❌', info: 'ℹ️', wait: '⏳' };
  const feed = document.getElementById('logFeed');

  feed.innerHTML = logs.map(l => `
    <div class="log-entry ${l.type}">
      <span class="le-icon">${icons[l.type] || '•'}</span>
      <div class="le-body">
        <div class="le-title">${esc(l.title)}</div>
        <div class="le-msg">${esc(l.msg)}</div>
      </div>
      <span class="le-time">${l.time}</span>
    </div>
  `).join('');

  setText('logBadge', `${logs.length} events`);
}


// ═══════════════════════════════════════════════════════════
//                   RENDER: BATCH LIST
// ═══════════════════════════════════════════════════════════

function renderBatch(batch, limit, todaySent) {
  setText('batchBadge', `${todaySent} / ${limit}`);

  if (!batch.length) {
    document.getElementById('batchList').innerHTML =
      '<div style="padding:20px;text-align:center;color:var(--muted);font-size:12px;">No batch running yet</div>';
    return;
  }

  document.getElementById('batchList').innerHTML = batch.map((b, i) => `
    <div class="bi" id="bi-${i}">
      <span class="bi-num">${i + 1}</span>
      <span class="bi-email">${esc(b.email)}</span>
      <span class="bi-co">${esc(b.company || '')}</span>
      <div class="bi-s ${b.status}">
        ${b.status === 'sent' ? '✓' : b.status === 'failed' ? '✗' : b.status === 'active' ? '●' : b.status === 'duplicate' ? '⊘' : ''}
      </div>
    </div>
  `).join('');

  // Auto-scroll to active row
  const activeEl = document.querySelector('.bi-s.active');
  if (activeEl) {
    activeEl.closest('.bi').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  }
}


// ═══════════════════════════════════════════════════════════
//                   RECORDS TABLE
// ═══════════════════════════════════════════════════════════

async function loadRecords() {

  const body = document.getElementById("recBody");

  // Skeleton loading rows
  body.innerHTML = `
    <tr>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
    </tr>
    <tr>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
    </tr>
    <tr>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
      <td class="skeleton"></td>
    </tr>
  `;

  const q = encodeURIComponent(recSearch);

  try {

    const res = await fetch(`/api/records?page=${recPage}&per=${PER_PAGE}&q=${q}`);
    const data = await res.json();

    recTotal = data.total;

    renderRecords(data.records, data.total);

  } catch (e) {

    body.innerHTML =
      '<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--red);">Could not load — is app.py running?</td></tr>';

  }

}

function renderRecords(records, total) {
  const start = (recPage - 1) * PER_PAGE + 1;
  const end = Math.min(recPage * PER_PAGE, total);

  setText('pgInfo', `${start}–${end} of ${total.toLocaleString()} records`);
  setText('pgCur', `Page ${recPage}`);
  setDisabled('pgPrev', recPage <= 1);
  setDisabled('pgNext', end >= total);

  if (!records.length) {
    document.getElementById('recBody').innerHTML =
      '<tr><td colspan="5" style="text-align:center;padding:30px;color:var(--muted);">No records found</td></tr>';
    return;
  }

  document.getElementById('recBody').innerHTML = records.map((r, i) => `
    <tr>
      <td style="color:var(--muted)">${(recPage - 1) * PER_PAGE + i + 1}</td>
      <td>${esc(r.name || '—')}</td>
      <td style="color:var(--accent)">${esc(r.email)}</td>
      <td style="color:var(--muted)">${esc(r.company || '—')}</td>
      <td>
        <span class="st-badge ${r.status}">${r.status}</span>
        ${r.reason ? `<div style="font-size:10px;color:var(--muted);margin-top:3px;">${esc(r.reason)}</div>` : ''}
      </td>
    </tr>
  `).join('');
}

function changePage(dir) {
  recPage = Math.max(1, recPage + dir);
  loadRecords();
}

function searchRecords() {
  clearTimeout(searchTimer);
  recSearch = document.getElementById('recSearch').value;
  recPage = 1;
  searchTimer = setTimeout(loadRecords, 300);
}


// ═══════════════════════════════════════════════════════════
//                      API CALLS
// ═══════════════════════════════════════════════════════════

async function apiStart() {
  const btnStart = document.getElementById('btnStart');

  // Paused hai to Resume karo — Start nahi
  const isPaused = btnStart.textContent.includes('Resume');
  if (isPaused) {
    btnStart.textContent = '⏳ Resuming...';
    btnStart.disabled = true;
    btnStart.style.opacity = '0.5';
    await fetch('/api/pause', { method: 'POST' });
    showToast('▶ Campaign resume ho gayi!');
    return;
  }

  btnStart.textContent = '⏳ Starting...';
  btnStart.disabled = true;
  btnStart.style.opacity = '0.5';

  const res = await fetch('/api/start', { method: 'POST' });
  const data = await res.json();

  if (data.ok) {
    showToast('▶ Campaign shuru ho gayi!');
    btnStart.textContent = '⏳ Sending...';
  } else {
    showToast('❌ ' + data.msg, 'err');
    btnStart.textContent = '▶ Start Campaign';
    btnStart.disabled = false;
    btnStart.style.opacity = '1';
  }
}

async function apiPause() {
  const btnPause = document.getElementById('btnPause');
  const wasPaused = btnPause.textContent.includes('Resume');

  btnPause.textContent = '⏳ ...';
  btnPause.disabled = true;

  const res = await fetch('/api/pause', { method: 'POST' });
  const data = await res.json();

  showToast(data.msg, wasPaused ? '' : 'warn');
  // Poll update karega actual state
}

async function apiStop() {
  document.getElementById('btnStop').textContent = '⏳ Stopping...';
  document.getElementById('btnStop').disabled = true;
  await fetch('/api/stop', { method: 'POST' });
  showToast('⏹ Campaign rok di gayi', 'warn');
  // 2 second baad reset karo — poll update karega
  setTimeout(() => {
    document.getElementById('btnStop').textContent = '⏹ Stop';
    document.getElementById('btnStop').disabled = false;
  }, 2000);
}

async function apiReset() {
  if (!confirm('Sab progress reset karna chahte ho? Yeh undo nahi hoga.')) return;
  await fetch('/api/reset', { method: 'POST' });
  lastLogCount = 0;
  recPage = 1;
  showToast('↺ Progress reset ho gaya!', 'warn');
}


// ═══════════════════════════════════════════════════════════
//                   SETTINGS MODAL
// ═══════════════════════════════════════════════════════════

function openSettings() {
  fetch('/api/status')
    .then(r => r.json())
    .then(d => {
      if (!d.config) return;
      const c = d.config;
      setVal('iEmail', c.email_address || '');
      setVal('iName', c.your_name || '');
      setVal('iLimit', c.daily_limit || 50);
      setVal('iDelayMin', c.delay_min || 60);
      setVal('iDelayMax', c.delay_max || 120);
      setVal('iExcel', c.excel_file || 'hr_emails.xlsx');
      setVal('iResume', c.resume_file || 'resume.pdf');
    })
    .catch(() => { });

  document.getElementById('settingsModal').classList.add('show');
}

function closeSettings() {
  document.getElementById('settingsModal').classList.remove('show');
}

async function saveSettings() {
  const email = getVal('iEmail').trim();
  const password = getVal('iPass').trim();
  const name = getVal('iName').trim();

  if (!email || !name) {
    showToast('⚠️ Email aur naam zaroori hai!', 'warn');
    return;
  }

  const payload = {
    email_address: email,
    email_password: password,
    your_name: name,
    your_phone: getVal('iPhone').trim(),
    your_linkedin: getVal('iLinkedin').trim(),
    excel_file: getVal('iExcel').trim() || 'hr_emails.xlsx',
    resume_file: getVal('iResume').trim() || 'resume.pdf',
    daily_limit: parseInt(getVal('iLimit')) || 50,
    delay_min: parseInt(getVal('iDelayMin')) || 60,
    delay_max: parseInt(getVal('iDelayMax')) || 120,
  };

  try {
    const res = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    closeSettings();
    lastLogCount = 0;
    showToast(data.ok ? '✅ Config saved!' : '⚠️ ' + data.msg, data.ok ? '' : 'warn')
  } catch (e) {
    showToast('❌ Server se connect nahi ho pa raha', 'err');
  }
}

// Close modal on outside click
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('settingsModal').addEventListener('click', function (e) {
    if (e.target === this) closeSettings();
  });
  startPolling();
});


// ═══════════════════════════════════════════════════════════
//                       HELPERS
// ═══════════════════════════════════════════════════════════

function setStatusPill(type, text) {
  document.getElementById('sDot').className = 'dot ' + type;
  setText('sTxt', text);
}

function showToast(msg, type = '') {
  const t = document.getElementById('toast');
  t.textContent = msg;
  t.className = `toast ${type} show`;
  setTimeout(() => t.classList.remove('show'), 3500);
}

function setText(id, val) { const el = document.getElementById(id); if (el) el.textContent = val; }
function setVal(id, val) { const el = document.getElementById(id); if (el) el.value = val; }
function getVal(id) { const el = document.getElementById(id); return el ? el.value : ''; }
function setDisabled(id, val) { const el = document.getElementById(id); if (el) el.disabled = val; }
function pad(n) { return String(n).padStart(2, '0'); }
function truncate(str, n) { return str.length > n ? str.substring(0, n - 1) + '…' : str; }
function esc(str) {
  return String(str || '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}