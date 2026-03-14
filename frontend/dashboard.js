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

// ✅ Upload state — pending files
const _pendingFiles = { excel: null, resume: null };

// ✅ File session state — server se aata hai
let _fileSessionValid = false;


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

  setText('stTotal', total.toLocaleString());
  setText('stSent', (d.all_time_sent || sent).toLocaleString());
  setText('stFailed', failed.toLocaleString());
  setText('stDuplicate', (d.duplicates || 0).toLocaleString());
  setText('stPending', pending.toLocaleString());
  setText('stToday', (d.today_sent || 0).toLocaleString());
  setText('stTodayFail', `${d.today_failed || 0} failed today`);
  setText('stDays', `~${daysLeft} days to finish`);

  setText('progPct', pct + '%');
  document.getElementById('progBar').style.width = pct + '%';
  setText('progLeft', `${pending.toLocaleString()} remaining`);

  const estDate = new Date();
  estDate.setDate(estDate.getDate() + daysLeft);
  setText('progEst', `Est. finish: ${estDate.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}`);

  const statusMap = { running: 'running', paused: 'paused', done: 'done', error: 'error', idle: 'idle' };
  const statusTxt = { running: '● Sending...', paused: '⏸ Paused', done: '✓ Done', error: '⚠ Error', idle: 'Ready' };
  setStatusPill(statusMap[d.status] || 'idle', statusTxt[d.status] || 'Ready');

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

  if (d.config) {
    const c = d.config;
    setText('cfgEmail', c.email_address ? truncate(c.email_address, 20) : 'not set');
    setText('cfgName', c.your_name || 'not set');
    setText('cfgLimit', (c.daily_limit || 50) + ' / day');
    setText('cfgDelay', `${c.delay_min || 60}–${c.delay_max || 120} sec`);
    setText('cfgExcel', c.excel_file ? truncate(c.excel_file.split(/[\\/]/).pop(), 22) : 'not set');
    setText('cfgResume', c.resume_file ? truncate(c.resume_file.split(/[\\/]/).pop(), 22) : 'not set');
  }
  setText('cfgLast', d.last_run || 'Never');

  // ✅ File session check — expire hui to log mein warn karo
  const fs = d.file_session || {};
  const wasValid = _fileSessionValid;
  _fileSessionValid = fs.valid === true;

  if (wasValid && !_fileSessionValid) {
    // Session abhi abhi expire hui — ek baar log mein dikhao
    addExpiredLog();
  }

  const running = d.status === 'running';
  const paused = d.status === 'paused';
  const done = d.status === 'done';
  const active = running || paused;

  const btnStart = document.getElementById('btnStart');
  const btnPause = document.getElementById('btnPause');
  const btnStop = document.getElementById('btnStop');

  btnStart.disabled = active;
  if (running) {
    btnStart.textContent = '⏳ Sending...';
    btnStart.style.opacity = '0.5';
    btnStart.style.cursor = 'not-allowed';
  } else if (paused) {
    btnStart.textContent = '⏸ Paused';
    btnStart.style.opacity = '0.5';
    btnStart.style.cursor = 'not-allowed';
    btnStart.disabled = true;
    btnPause.textContent = '▶ Resume';
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

  btnStop.disabled = !active;
  btnStop.style.opacity = active ? '1' : '0.4';

  renderLogs(d.logs || []);
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
  body.innerHTML = `
    <tr><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td></tr>
    <tr><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td></tr>
    <tr><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td><td class="skeleton"></td></tr>
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
}

async function apiStop() {
  document.getElementById('btnStop').textContent = '⏳ Stopping...';
  document.getElementById('btnStop').disabled = true;
  await fetch('/api/stop', { method: 'POST' });
  showToast('⏹ Campaign rok di gayi', 'warn');
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
      const fs = d.file_session || {};

      setVal('iEmail', c.email_address || '');
      setVal('iName', c.your_name || '');
      setVal('iLimit', c.daily_limit || 50);
      setVal('iDelayMin', c.delay_min || 60);
      setVal('iDelayMax', c.delay_max || 120);

      // ✅ File session valid hai — zone hide karo, preview dikhao (with ✕ to re-upload)
      if (fs.valid) {
        if (fs.excel_name) {
          // Zone hide, preview show — already uploaded file
          document.getElementById('excelZone').style.display = 'none';
          document.getElementById('excelPreview').style.display = 'flex';
          document.getElementById('excelPreviewName').textContent = fs.excel_name;
          document.getElementById('excelPreviewRows').textContent = '✓ valid till midnight';
          document.getElementById('excelPreviewRows').style.color = 'var(--green)';
          // ✕ button pe click karo to zone wapas dikhao (re-upload ke liye)
          document.getElementById('excelPreview')
            .querySelector('.up-remove').onclick = () => clearFileSession('excel');
        }
        if (fs.resume_name) {
          document.getElementById('resumeZone').style.display = 'none';
          document.getElementById('resumePreview').style.display = 'flex';
          document.getElementById('resumePreviewName').textContent = fs.resume_name;
          // ✅ Resume mein bhi "valid till midnight" dikhao
          const resumeRows = document.getElementById('resumePreviewRows');
          if (resumeRows) {
            resumeRows.textContent = '✓ valid till midnight';
            resumeRows.style.color = 'var(--green)';
          }
          document.getElementById('resumePreview')
            .querySelector('.up-remove').onclick = () => clearFileSession('resume');
          document.getElementById('excelPreviewRows').textContent = '✓ valid till midnight';
          document.getElementById('excelPreviewRows').style.color = 'var(--green)';
          document.getElementById('resumePreview')
            .querySelector('.up-remove').onclick = () => clearFileSession('resume');
        }
        // Current line clear karo — zone ki jagah preview hai ab
        document.getElementById('excelCurrent').textContent = '';
        document.getElementById('resumeCurrent').textContent = '';

      } else {
        // Session expire / nahi hai — zone dikhao + warning
        resetUploadZone('excel');
        resetUploadZone('resume');
        const warn = `<span style="color:var(--amber)">⚠️ Please re-upload file</span>`;
        if (c.excel_file) document.getElementById('excelCurrent').innerHTML = warn;
        if (c.resume_file) document.getElementById('resumeCurrent').innerHTML = warn;
      }
    })
    .catch(() => { });

  // Pending files reset karo — session valid files apna ✕ handle karengi
  _pendingFiles.excel = null;
  _pendingFiles.resume = null;
  // Zones ka default state — session check ke baad overwrite hoga
  resetUploadZone('excel');
  resetUploadZone('resume');
  document.getElementById('excelCurrent').textContent = '';
  document.getElementById('resumeCurrent').textContent = '';

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

  const btnSave = document.getElementById('btnSave');
  btnSave.textContent = '⏳ Saving...';
  btnSave.disabled = true;

  try {
    // ✅ File session check — expire hai to files zaroori hain
    if (!_fileSessionValid && !_pendingFiles.excel && !_pendingFiles.resume) {
      showToast('⚠️ File session expired! Excel & Resume dobara upload karo', 'warn');
      btnSave.textContent = '💾 Save Settings';
      btnSave.disabled = false;
      return;
    }

    // ── Step 1: Upload files if pending ───────────────────
    let uploadMsg = '';

    if (_pendingFiles.excel || _pendingFiles.resume) {
      const formData = new FormData();
      if (_pendingFiles.excel) formData.append('excel', _pendingFiles.excel);
      if (_pendingFiles.resume) formData.append('resume', _pendingFiles.resume);

      const upRes = await fetch('/api/upload', { method: 'POST', body: formData });
      const upData = await upRes.json();

      if (!upData.ok) {
        showToast('❌ Upload failed: ' + upData.msg, 'err');
        btnSave.textContent = '💾 Save Settings';
        btnSave.disabled = false;
        return;
      }

      // Build upload summary
      if (upData.saved?.excel) {
        const rows = upData.saved.excel.rows;
        uploadMsg += `📊 Excel: ${rows} contacts loaded. `;
      }
      if (upData.saved?.resume) {
        uploadMsg += `📄 Resume uploaded. `;
      }
    }

    // ── Step 2: Save config ───────────────────────────────
    const payload = {
      email_address: email,
      email_password: password,
      your_name: name,
      your_phone: getVal('iPhone').trim(),
      your_linkedin: getVal('iLinkedin').trim(),
      daily_limit: parseInt(getVal('iLimit')) || 50,
      delay_min: parseInt(getVal('iDelayMin')) || 60,
      delay_max: parseInt(getVal('iDelayMax')) || 120,
    };

    const cfgRes = await fetch('/api/config', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const cfgData = await cfgRes.json();

    closeSettings();
    lastLogCount = 0;

    const finalMsg = (uploadMsg + (cfgData.ok ? '✅ Config saved!' : '⚠️ ' + cfgData.msg)).trim();
    showToast(finalMsg, cfgData.ok ? '' : 'warn');

  } catch (e) {
    showToast('❌ Server se connect nahi ho pa raha', 'err');
  } finally {
    btnSave.textContent = '💾 Save Settings';
    btnSave.disabled = false;
  }
}


// ═══════════════════════════════════════════════════════════
//              ✅ FILE SESSION — LOGIC
// ═══════════════════════════════════════════════════════════

/**
 * Session expire hone pe log mein ek baar warn karo
 */
function addExpiredLog() {
  // Fake log entry inject karo — server se aane wale logs ke upar
  const feed = document.getElementById('logFeed');
  if (!feed) return;

  const entry = document.createElement('div');
  entry.className = 'log-entry wait';
  entry.innerHTML = `
    <span class="le-icon">⚠️</span>
    <div class="le-body">
      <div class="le-title">File Session Expired</div>
      <div class="le-msg">Please re-upload Excel &amp; Resume from ⚙️ Settings → Files</div>
    </div>
    <span class="le-time">now</span>
  `;
  feed.prepend(entry);
  setText('logBadge', parseInt(document.getElementById('logBadge').textContent) + 1 + ' events');
}

/**
 * Jab user file select kare — preview dikhao, pending mein rakh
 * type: 'excel' ya 'resume'
 */
function handleFileSelect(type, inputEl) {
  const file = inputEl.files[0];
  if (!file) return;

  _pendingFiles[type] = file;

  const zone = document.getElementById(type === 'excel' ? 'excelZone' : 'resumeZone');
  const preview = document.getElementById(type === 'excel' ? 'excelPreview' : 'resumePreview');

  // Hide zone, show preview
  zone.style.display = 'none';
  preview.style.display = 'flex';

  if (type === 'excel') {
    document.getElementById('excelPreviewName').textContent = file.name;
    // Size
    const kb = (file.size / 1024).toFixed(1);
    document.getElementById('excelPreviewRows').textContent = `${kb} KB — will upload on Save`;
  } else {
    document.getElementById('resumePreviewName').textContent = file.name;
  }
}

/**
 * Upload zone drag & drop support
 */
function setupDragDrop(zoneId, inputId, type) {
  const zone = document.getElementById(zoneId);
  if (!zone) return;

  zone.addEventListener('dragover', e => {
    e.preventDefault();
    zone.classList.add('drag-over');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-over'));
  zone.addEventListener('drop', e => {
    e.preventDefault();
    zone.classList.remove('drag-over');
    const file = e.dataTransfer.files[0];
    if (!file) return;

    // Validate type
    if (type === 'excel' && !file.name.match(/\.(xlsx|xls)$/i)) {
      showToast('❌ Sirf .xlsx ya .xls file allowed hai', 'err');
      return;
    }
    if (type === 'resume' && !file.name.match(/\.pdf$/i)) {
      showToast('❌ Sirf .pdf file allowed hai', 'err');
      return;
    }

    // Inject into file input and trigger handler
    const dt = new DataTransfer();
    dt.items.add(file);
    const inp = document.getElementById(inputId);
    inp.files = dt.files;
    handleFileSelect(type, inp);
  });
}

/**
 * ✅ Session wali file ka ✕ dabaya — zone wapas dikhao (re-upload ke liye)
 * Pending file bhi clear karo
 */
function clearFileSession(type) {
  _pendingFiles[type] = null;
  // Preview hide, zone show
  resetUploadZone(type);
  // Input clear
  const inputId = type === 'excel' ? 'excelInput' : 'resumeInput';
  document.getElementById(inputId).value = '';
  // ✕ handler wapas original pe
  const previewId = type === 'excel' ? 'excelPreview' : 'resumePreview';
  document.getElementById(previewId)
    .querySelector('.up-remove').onclick = () => clearFile(type);
}

/**
 * Remove selected file — reset to zone view
 */
function clearFile(type) {
  _pendingFiles[type] = null;
  resetUploadZone(type);
  // Clear the input so same file can be reselected
  const inputId = type === 'excel' ? 'excelInput' : 'resumeInput';
  document.getElementById(inputId).value = '';
}

function resetUploadZone(type) {
  const zone = document.getElementById(type === 'excel' ? 'excelZone' : 'resumeZone');
  const preview = document.getElementById(type === 'excel' ? 'excelPreview' : 'resumePreview');
  if (zone) zone.style.display = '';
  if (preview) preview.style.display = 'none';
}


// Close modal on outside click
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('settingsModal').addEventListener('click', function (e) {
    if (e.target === this) closeSettings();
  });

  // Setup drag & drop for both zones
  setupDragDrop('excelZone', 'excelInput', 'excel');
  setupDragDrop('resumeZone', 'resumeInput', 'resume');

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
function changeNum(id, delta) {
  const el = document.getElementById(id);
  const val = parseInt(el.value) || parseInt(el.placeholder) || 0;
  const min = parseInt(el.min) || 1;
  const max = parseInt(el.max) || 9999;
  el.value = Math.min(max, Math.max(min, val + delta));
}