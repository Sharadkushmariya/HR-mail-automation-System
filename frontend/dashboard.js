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
  // ✅ FIX LOGIC 2: Research auto-load — yahan se handle karo, duplicate listener nahi
  if (id === 'research' && Object.keys(_researchResultsMap).length === 0) loadResearchDone();
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
  // ✅ FIX Minor: 200ms/800ms bahut aggressive tha — 2000ms server-friendly
  setInterval(pollStatus, 2000);
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
  // ✅ FIX UI 6: "~0 days to finish" confusing tha — proper message
  setText('stDays', pending > 0 ? `~${daysLeft} days to finish` : (sent > 0 ? '🎉 Campaign complete!' : 'Start karo campaign'));

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
  // ✅ FIX LOGIC 4: Max page check add kiya — overflow prevent
  const maxPage = Math.ceil(recTotal / PER_PAGE) || 1;
  recPage = Math.min(maxPage, Math.max(1, recPage + dir));
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

  // ✅ FIX BUG 1: Text check galat tha — server se actual status check karo
  let currentStatus = 'idle';
  try {
    const statusRes = await fetch('/api/status');
    const statusData = await statusRes.json();
    currentStatus = statusData.status || 'idle';
  } catch (e) { /* ignore — niche handle hoga */ }

  if (currentStatus === 'paused') {
    btnStart.textContent = '⏳ Resuming...';
    btnStart.disabled = true;
    btnStart.style.opacity = '0.5';
    try {
      await fetch('/api/pause', { method: 'POST' });
      showToast('▶ Campaign resume ho gayi!');
    } catch (e) {
      showToast('❌ Server se connect nahi ho pa raha', 'err');
      btnStart.textContent = '⏸ Paused';
      btnStart.disabled = false;
      btnStart.style.opacity = '0.5';
    }
    return;
  }

  btnStart.textContent = '⏳ Starting...';
  btnStart.disabled = true;
  btnStart.style.opacity = '0.5';

  // ✅ FIX BUG 2: try/catch add kiya — server offline hone pe button stuck nahi rahega
  try {
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
  } catch (e) {
    showToast('❌ Server se connect nahi ho pa raha', 'err');
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
    // ✅ FIX BUG 3: Session check sirf warn karo — block mat karo
    // User config-only changes (naam, limit) bhi save kar sake bina re-upload ke
    if (!_fileSessionValid && !_pendingFiles.excel && !_pendingFiles.resume) {
      showToast('⚠️ File session expired — files pehle upload karo campaign start se pehle', 'warn');
      // Return mat karo — config save hone do
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
  // ✅ FIX BUG 5: parseInt('NaN events') = NaN — fallback 0 add kiya
  const currentCount = parseInt(document.getElementById('logBadge').textContent) || 0;
  setText('logBadge', (currentCount + 1) + ' events');
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

// ═══════════════════════════════════════════════════════════
// RESEARCH TAB — dashboard.js ke bottom mein add karo
// ═══════════════════════════════════════════════════════════

let _researchPollTimer = null;
let _researchResultsMap = {};   // company → result (dedupe)

// ── Category badge color ────────────────────────────────────
function getCategoryColor(category) {
  if (!category) return { bg: "var(--bg2)", color: "var(--muted)" };
  const c = category.toLowerCase();
  if (c.includes("networking") || c.includes("telecom"))
    return { bg: "#1a3a2a", color: "#4ade80" };
  if (c.includes("software") || c.includes("saas"))
    return { bg: "#1a2a3a", color: "#60a5fa" };
  if (c.includes("cloud") || c.includes("security"))
    return { bg: "#1a1a3a", color: "#a78bfa" };
  if (c.includes("data") || c.includes("ai"))
    return { bg: "#2a1a3a", color: "#e879f9" };
  if (c.includes("it services"))
    return { bg: "#1a2a20", color: "#34d399" };
  if (c.includes("bpo") || c.includes("kpo"))
    return { bg: "#2a2a1a", color: "#fbbf24" };
  if (c.includes("finance") || c.includes("bfsi"))
    return { bg: "#2a1a1a", color: "#f87171" };
  return { bg: "var(--bg2)", color: "var(--muted)" };
}

function getMatchColor(score) {
  if (score >= 85) return "#4ade80";
  if (score >= 70) return "#fbbf24";
  return "#f87171";
}

// ── Render one research result card (Improved UI) ──────────
function renderResearchCard(res) {
  const catColor = getCategoryColor(res.category);
  const score = res.match_score || 0;
  const matchClr = getMatchColor(score);
  const tsArray = Array.isArray(res.tech_stack) ? res.tech_stack
    : (typeof res.tech_stack === 'string' ? [res.tech_stack] : []);
  const techStack = tsArray.slice(0, 5)
    .map(t => `<span style="font-size:11px;padding:2px 9px;border-radius:4px;
      background:var(--surface3);border:1px solid var(--border);
      color:var(--muted);font-family:var(--fm);">${esc(t)}</span>`)
    .join(" ");

  const rewriteNote = res.match_attempts > 1
    ? `<span style="font-size:10px;color:var(--amber);margin-left:4px;">↻ rewritten ${res.match_attempts - 1}×</span>`
    : "";

  const statusBadge = res.ok
    ? `<span style="font-size:11px;color:var(--green);background:var(--green-dim);
         padding:2px 8px;border-radius:100px;border:1px solid rgba(74,222,128,.3);">✓ Ready</span>`
    : `<span style="font-size:11px;color:var(--red);background:var(--red-dim);
         padding:2px 8px;border-radius:100px;">⚠ Error</span>`;

  const matchBarWidth = score + "%";
  const matchBarColor = score >= 85 ? "var(--green)" : score >= 70 ? "var(--amber)" : "var(--red)";

  return `
<div class="research-card" style="border-left:3px solid ${catColor.color};">
  <!-- Header row -->
  <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px;gap:10px;">
    <div style="flex:1;min-width:0;">
      <div style="font-size:15px;font-weight:700;color:var(--text-bright);margin-bottom:4px;">${esc(res.company)}</div>
      <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;">
        <span class="cat-chip" style="background:${catColor.bg};color:${catColor.color};">${esc(res.category || 'Unknown')}</span>
        ${statusBadge}
        ${rewriteNote}
      </div>
    </div>
    <button class="btn btn-secondary btn-sm" style="flex-shrink:0;"
      onclick="previewEmail('${encodeURIComponent(res.company)}','${encodeURIComponent(res.email_subject || '')}','${encodeURIComponent(res.email_body || '')}')">
      👁 Email
    </button>
  </div>

  <!-- Description -->
  <p style="font-size:13px;color:var(--muted);margin:0 0 12px;line-height:1.55;
    display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">
    ${esc(res.description || '—')}
  </p>

  <!-- Tech stack -->
  ${techStack ? `<div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:12px;">${techStack}</div>` : ""}

  <!-- Match score -->
  <div class="match-bar-wrap">
    <span style="font-size:11px;color:var(--muted);white-space:nowrap;">Match</span>
    <div class="match-bar-bg">
      <div class="match-bar-fill" style="width:${matchBarWidth};background:${matchBarColor};"></div>
    </div>
    <span style="font-size:12px;font-weight:700;color:${matchClr};font-family:var(--fm);white-space:nowrap;">${score}/100</span>
  </div>

  <!-- Footer meta -->
  <div style="margin-top:8px;font-size:10px;color:var(--muted2);display:flex;gap:12px;">
    ${res.researched_at ? `<span>🕐 ${esc(res.researched_at)}</span>` : ""}
    <span>Attempts: ${res.match_attempts || 1}</span>
  </div>
</div>`;
}

// ── Inject cards into results div ──────────────────────────
function renderAllResearchCards() {
  const container = document.getElementById("researchResults");
  const empty = document.getElementById("researchEmpty");
  const cards = Object.values(_researchResultsMap);

  if (cards.length === 0) {
    if (empty) empty.style.display = "block";
    return;
  }
  if (empty) empty.style.display = "none";

  // Re-render all cards
  container.innerHTML = cards.map(renderResearchCard).join("");
}

// ── START BATCH RESEARCH ────────────────────────────────────
function startBatchResearch() {
  const limit = parseInt(document.getElementById("researchLimit").value) || 10;
  const btn = document.getElementById("btnResearchStart");

  btn.disabled = true;
  btn.textContent = "🔄 Researching...";

  document.getElementById("researchProgressCard").style.display = "block";
  document.getElementById("researchBadge").textContent = "Running...";

  fetch("/api/research/start", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ limit })
  })
    .then(r => r.json())
    .then(d => {
      if (!d.ok) {
        showToast(d.msg, "error");
        btn.disabled = false;
        btn.textContent = "🔬 Start Research";
        return;
      }
      showToast(d.msg, "success");
      _startResearchPoll();
    })
    .catch(() => {
      showToast("Research start nahi ho payi", "error");
      btn.disabled = false;
      btn.textContent = "🔬 Start Research";
    });
}

// ── POLL research status ────────────────────────────────────
function _startResearchPoll() {
  if (_researchPollTimer) clearInterval(_researchPollTimer);
  _researchPollTimer = setInterval(_pollResearchStatus, 2000);
}

function _pollResearchStatus() {
  fetch("/api/research/status")
    .then(r => r.json())
    .then(data => {
      const pct = data.total > 0 ? Math.round((data.progress / data.total) * 100) : 0;
      const badge = document.getElementById("researchBadge");
      const pgBadge = document.getElementById("researchProgressBadge");
      const pgBar = document.getElementById("researchProgBar");
      const pgPct = document.getElementById("researchProgPct");
      const pgCo = document.getElementById("researchCurrentCo");

      if (pgBadge) pgBadge.textContent = `${data.progress} / ${data.total}`;
      if (pgBar) pgBar.style.width = pct + "%";
      if (pgPct) pgPct.textContent = pct + "%";
      if (pgCo) pgCo.textContent = data.current || "—";

      // New results merge karo
      (data.results || []).forEach(res => {
        _researchResultsMap[res.company] = res;
      });
      renderAllResearchCards();

      // ✅ Update status dot
      const dot = document.getElementById("researchStatusDot");

      if (!data.running) {
        clearInterval(_researchPollTimer);
        _researchPollTimer = null;

        const btn = document.getElementById("btnResearchStart");
        if (btn) { btn.disabled = false; btn.textContent = "🔬 Start Batch Research"; }
        if (badge) badge.textContent = data.done ? `✓ ${data.progress} companies researched` : "Ready";
        if (pgCo) pgCo.textContent = "Completed!";
        if (dot) { dot.className = data.error ? "research-status-dot error" : "research-status-dot done"; }
        document.getElementById("researchProgressCard").style.display = "none";

        if (data.error) showToast("Research error: " + data.error, "error");
        else if (data.done) showToast(`✅ ${data.progress} companies research ho gayi!`, "success");
      } else {
        if (badge) badge.textContent = `Researching ${data.progress}/${data.total}...`;
        if (dot) dot.className = "research-status-dot running";
      }
    })
    .catch(() => { });
}

// ── LOAD EXISTING DONE RESULTS ──────────────────────────────
function loadResearchDone() {
  document.getElementById("researchBadge").textContent = "Loading...";
  fetch("/api/research/done")
    .then(r => r.json())
    .then(data => {
      (data.records || []).forEach(rec => {
        // Map to card format
        _researchResultsMap[rec.company] = {
          company: rec.company,
          category: rec.category,
          description: rec.description,
          tech_stack: [],
          match_score: parseInt(rec.match_score) || 0,
          match_attempts: 1,
          email_subject: `Application for IT Role – ${rec.company}`,
          email_body: rec.email_body,
          ok: true,
          error: "",
          researched_at: "",
          is_tech: rec.category.toLowerCase().includes("tech"),
        };
      });
      renderAllResearchCards();
      document.getElementById("researchBadge").textContent =
        `${data.total} loaded`;
      showToast(`${data.total} existing results loaded`, "success");
    })
    .catch(() => showToast("Load failed", "error"));
}

// ── SINGLE COMPANY RESEARCH ─────────────────────────────────
function researchSingle() {
  const input = document.getElementById("singleCompanyInput");
  const company = input.value.trim();
  const btn = document.getElementById("btnSingleResearch");

  if (!company) { showToast("Company name likho pehle", "error"); return; }

  btn.disabled = true;
  btn.textContent = "Researching...";
  document.getElementById("researchBadge").textContent = `Researching ${company}...`;

  fetch("/api/research/single", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ company })
  })
    .then(r => r.json())
    .then(data => {
      btn.disabled = false;
      btn.textContent = "Research ↗";

      if (!data.ok) {
        showToast(data.msg || "Research failed", "error");
        return;
      }
      const res = data.result;
      _researchResultsMap[res.company] = res;
      renderAllResearchCards();
      document.getElementById("researchBadge").textContent = "Done";
      showToast(`✅ ${company} researched!`, "success");
      input.value = "";
    })
    .catch(() => {
      btn.disabled = false;
      btn.textContent = "Research ↗";
      showToast("Research failed", "error");
    });
}

// ── EMAIL PREVIEW MODAL ─────────────────────────────────────
function previewEmail(companyEncoded, subjectEncoded, bodyEncoded) {
  const company = decodeURIComponent(companyEncoded);
  const subject = decodeURIComponent(subjectEncoded);
  const body = decodeURIComponent(bodyEncoded);

  document.getElementById("emailPreviewCompany").textContent = company;
  document.getElementById("emailPreviewSubject").textContent = subject;
  document.getElementById("emailPreviewBody").value = body;
  // ✅ FIX BUG 4: display:flex ki jagah .show class use karo — CSS overlay centering sahi kaam karega
  document.getElementById("emailPreviewModal").classList.add("show");
}

function closeEmailPreview(event) {
  // ✅ FIX BUG 4: .show class remove karo
  if (!event || event.target === document.getElementById("emailPreviewModal")) {
    document.getElementById("emailPreviewModal").classList.remove("show");
  }
}

function copyEmailPreview() {
  const subject = document.getElementById("emailPreviewSubject").textContent;
  const body = document.getElementById("emailPreviewBody").value;
  const full = `Subject: ${subject}\n\n${body}`;
  navigator.clipboard.writeText(full).then(() => showToast("Email copied!", "success"));
}

// ✅ FIX LOGIC 2: Duplicate research tab listener hataya — switchTab() mein already handle hai

// Single company input — Enter key
document.addEventListener("DOMContentLoaded", () => {
  const inp = document.getElementById("singleCompanyInput");
  if (inp) inp.addEventListener("keydown", e => { if (e.key === "Enter") researchSingle(); });
}
);