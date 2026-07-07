'use strict';

/* =============================================================
   CONFIG
============================================================= */
const API_BASE = 'http://localhost:8000';

/* =============================================================
   APP STATE
============================================================= */
const S = {
  page:         'home',
  rankResults:  null,
  pendingFiles: [],
  charts:       {},   // chart instances to destroy on re-render
};

/* =============================================================
   API CLIENT
============================================================= */
const API = {
  async _req(method, path, opts = {}) {
    const url = new URL(API_BASE + path);
    if (opts.params) {
      Object.entries(opts.params).forEach(([k, v]) => url.searchParams.set(k, v));
    }
    const init = {
      method,
      signal: AbortSignal.timeout(90000),
    };
    if (opts.form)  init.body = opts.form;
    if (opts.json)  { init.body = JSON.stringify(opts.json); init.headers = { 'Content-Type': 'application/json' }; }
    const res = await fetch(url, init);
    if (!res.ok) {
      let msg = `${res.status} ${res.statusText}`;
      try { const j = await res.json(); msg = j.detail || msg; } catch {}
      throw new Error(msg);
    }
    if (res.status === 204) return null;
    return res.json();
  },
  get:    (path, params) => API._req('GET',    path, { params }),
  post:   (path, opts)   => API._req('POST',   path, opts),
  delete: (path)         => API._req('DELETE', path),
};

/* =============================================================
   TOAST
============================================================= */
function toast(msg, type = 'info', ms = 3600) {
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-dot"></span><span>${msg}</span>`;
  document.getElementById('toastContainer').appendChild(el);
  setTimeout(() => {
    el.style.animation = 'slideInRight .2s reverse forwards';
    setTimeout(() => el.remove(), 210);
  }, ms);
}

/* =============================================================
   ROUTER
============================================================= */
function navigate(page) {
  S.page = page;
  document.querySelectorAll('.nav-link').forEach(el =>
    el.classList.toggle('active', el.dataset.page === page)
  );
  // destroy any live charts so canvas can be reused
  Object.values(S.charts).forEach(c => { try { c.destroy(); } catch {} });
  S.charts = {};
  renderPage(page);
  history.replaceState(null, '', `#${page}`);
}

async function renderPage(page) {
  const app = document.getElementById('app');
  app.innerHTML = '<div class="page-loading"><div class="spinner"></div></div>';
  try {
    switch (page) {
      case 'home':      await renderHome(app);      break;
      case 'resumes':   await renderResumes(app);   break;
      case 'jobs':      await renderJobs(app);      break;
      case 'rankings':  await renderRankings(app);  break;
      case 'analytics': await renderAnalytics(app); break;
      case 'history':   await renderHistory(app);   break;
      default:          await renderHome(app);
    }
  } catch (err) {
    app.innerHTML = empty('Something went wrong', err.message);
  }
}

/* =============================================================
   HTML HELPERS
============================================================= */
function ph(title, sub) {
  return `
  <div class="page-hd page-enter">
    <div class="page-title">${title}</div>
    <div class="page-sub">${sub}</div>
    <div class="page-div"></div>
  </div>`;
}

function sc(value, label, sup = '') {
  return `
  <div class="stat-card">
    ${sup ? `<div class="stat-sup">${sup}</div>` : ''}
    <div class="stat-val">${value}</div>
    <div class="stat-lbl">${label}</div>
  </div>`;
}

function secLbl(text) {
  return `<div class="sec-lbl">${text}</div>`;
}

function infoStrip(text, cls = '') {
  return `<div class="info-strip ${cls}">${text}</div>`;
}

function empty(title, sub = '') {
  return `
  <div class="empty">
    <div class="empty-icon">&#9654;</div>
    <div class="empty-title">${title}</div>
    ${sub ? `<div class="empty-sub">${sub}</div>` : ''}
  </div>`;
}

function chips(arr = [], cls = 'chip-gray', max = 40) {
  return arr.slice(0, max).map(s => `<span class="chip ${cls}">${esc(s)}</span>`).join('');
}

function recBadge(rec) {
  const m = {
    'Excellent Candidate': 'b-excellent',
    'Strong Match':        'b-strong',
    'Suitable':            'b-suitable',
    'Average Match':       'b-average',
    'Not Recommended':     'b-not',
  };
  return `<span class="badge ${m[rec] || 'b-not'}">${esc(rec)}</span>`;
}

function rankBadge(n) {
  const c = n <= 3 ? `rank-${n}` : 'rank-n';
  return `<span class="rank-badge ${c}">${n}</span>`;
}

function scoreBar(score) {
  const cls = score >= 80 ? 's-high' : score >= 60 ? 's-good' : score >= 40 ? 's-mid' : score >= 20 ? 's-low' : 's-poor';
  return `
  <div class="score-bar-wrap">
    <div class="score-bar-hd">
      <span class="score-bar-lbl">Match Score</span>
      <span class="score-bar-val">${score.toFixed(1)}%</span>
    </div>
    <div class="score-track">
      <div class="score-fill ${cls}" data-target="${score}"></div>
    </div>
  </div>`;
}

function animateBars() {
  requestAnimationFrame(() => {
    document.querySelectorAll('.score-fill[data-target]').forEach(el => {
      el.style.width = el.dataset.target + '%';
    });
  });
}

function esc(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function fmtBytes(b) {
  if (b < 1024) return `${b} B`;
  if (b < 1048576) return `${(b / 1024).toFixed(1)} KB`;
  return `${(b / 1048576).toFixed(1)} MB`;
}

function fmtDate(str) {
  return str ? String(str).slice(0, 10) : '—';
}

/* =============================================================
   TABS INIT
============================================================= */
function initTabs(barId) {
  const bar = document.getElementById(barId);
  if (!bar) return;
  bar.addEventListener('click', e => {
    const btn = e.target.closest('.tab-btn');
    if (!btn) return;
    bar.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const key = btn.dataset.tab;
    document.querySelectorAll('.tab-pane').forEach(p =>
      p.classList.toggle('active', p.dataset.pane === key)
    );
  });
}

/* =============================================================
   API STATUS
============================================================= */
async function checkStatus() {
  const dot  = document.getElementById('statusDot');
  const txt  = document.getElementById('statusText');
  try {
    await API.get('/health');
    dot.className  = 'status-dot online';
    txt.textContent = 'API Online';
  } catch {
    dot.className  = 'status-dot offline';
    txt.textContent = 'API Offline';
  }
}

/* =============================================================
   HOME PAGE
============================================================= */
async function renderHome(app) {
  const [resumes, jobs, history] = await Promise.all([
    API.get('/resumes').catch(() => []),
    API.get('/jobs').catch(() => []),
    API.get('/history').catch(() => []),
  ]);

  const ranked = history.filter(h => h.total_resumes > 0);
  const avgTop = ranked.length
    ? (ranked.reduce((s, h) => s + (h.top_score || 0), 0) / ranked.length).toFixed(1) + '%'
    : '—';

  app.innerHTML = `
  ${ph('Resume Ranking Dashboard',
    'An AI-powered recruitment tool that reads resumes, extracts skills and experience, and ranks every candidate against your job description — automatically.')}

  <div class="g4 mb32">
    ${sc(resumes.length,  'Resumes Stored',    'TOTAL UPLOADED')}
    ${sc(jobs.length,     'Job Descriptions',  'ON FILE')}
    ${sc(ranked.length,   'Rankings Run',      'SESSIONS')}
    ${sc(avgTop,          'Avg Top Score',      'BEST CANDIDATE')}
  </div>

  <div class="g2">
    <div class="page-enter">
      ${secLbl('HOW IT WORKS')}
      <div class="step-list">
        ${[
          'Upload resume files in PDF, DOCX, or TXT format',
          'Add a job description by typing, pasting, or uploading a file',
          'The AI parses every resume — extracts skills, education, experience',
          'TF-IDF converts resume and JD text into mathematical vectors',
          'Cosine similarity computes a match score for each candidate',
          'Candidates are ranked highest to lowest with full skill gap analysis',
          'Export results as CSV, Excel spreadsheet, or a PDF report',
        ].map((s, i) => `
        <div class="step"><div class="step-n">${i + 1}</div><span>${s}</span></div>`).join('')}
      </div>
    </div>

    <div class="page-enter">
      ${secLbl('SCORE THRESHOLDS')}
      ${[
        ['Excellent Candidate', '95% and above',  '#D1FAE5', '#065F46'],
        ['Strong Match',        '80% – 94%',      '#DCFCE7', '#166534'],
        ['Suitable',            '60% – 79%',      '#FEF3C7', '#92400E'],
        ['Average Match',       '40% – 59%',      '#FFEDD5', '#9A3412'],
        ['Not Recommended',     'Below 40%',      '#FEE2E2', '#991B1B'],
      ].map(([lbl, rng, bg, fg]) => `
      <div class="thresh-row" style="background:${bg};">
        <span style="color:${fg};">${lbl}</span>
        <span style="color:${fg};font-size:0.9rem;">${rng}</span>
      </div>`).join('')}

      ${!resumes.length ? `<div class="mt20">
        ${infoStrip('No resumes yet — go to <b>Upload Resumes</b> and click <b>Generate Sample Data</b> to load 20 demo resumes and 5 job descriptions instantly.')}
      </div>` : ''}
    </div>
  </div>`;
}

/* =============================================================
   RESUMES PAGE
============================================================= */
async function renderResumes(app) {
  const resumes = await API.get('/resumes').catch(() => []);

  app.innerHTML = `
  ${ph('Upload Resumes',
    'Upload candidate resumes as PDF, DOCX, or TXT files. The system automatically extracts name, contact details, skills, education, work experience, projects, and certifications.')}

  <div class="tab-bar" id="resumeTabBar">
    <button class="tab-btn active" data-tab="upload">Upload Files</button>
    <button class="tab-btn" data-tab="demo">Sample Data</button>
    <button class="tab-btn" data-tab="list">Stored Resumes (${resumes.length})</button>
  </div>

  <div class="tab-pane active" data-pane="upload">
    ${infoStrip('Select one or multiple files at once. Duplicate files are detected by hash and skipped automatically.')}
    <div class="upload-zone" id="upZone">
      <input type="file" id="upInput" multiple accept=".pdf,.docx,.txt" />
      <div class="upload-icon">&#8593;</div>
      <div class="upload-title">Drop files here or <strong>click to browse</strong></div>
      <div class="upload-sub">PDF, DOCX, or TXT &nbsp;·&nbsp; Multiple files supported</div>
    </div>
    <div id="upFileList" class="file-list"></div>
    <div id="upActions" style="display:none;" class="mt16">
      <button class="btn btn-primary btn-lg" id="upBtn">Upload and Parse All</button>
    </div>
    <div id="upResults"></div>
  </div>

  <div class="tab-pane" data-pane="demo">
    <div style="max-width:520px;margin:0 auto;">
      <div class="card" style="padding:40px 36px;text-align:center;">
        <div style="font-size:1.15rem;font-weight:800;margin-bottom:12px;">Generate Demo Data</div>
        <div style="font-size:0.9rem;color:var(--text-muted);line-height:1.7;margin-bottom:28px;">
          Creates 20 realistic synthetic resumes across five profiles — Data Scientist, Software Engineer,
          DevOps Engineer, ML Engineer, and Frontend Developer — along with 5 matching job descriptions.
          Ready to rank immediately.
        </div>
        <button class="btn btn-primary btn-lg w100" id="demoBtn">Generate Sample Data</button>
      </div>
    </div>
  </div>

  <div class="tab-pane" data-pane="list">
    <div class="filter-bar mb20">
      <input type="text" class="input" id="resumeSearch" placeholder="Search by name or skill..." />
    </div>
    <div id="resumeList">${buildResumeList(resumes)}</div>
  </div>`;

  initTabs('resumeTabBar');
  initUploadZone(resumes);
}

function buildResumeList(list) {
  if (!list.length) return empty('No resumes yet', 'Upload files or generate sample data');
  return list.map(r => {
    const name = esc(r.candidate_name || r.filename);
    return `
    <div class="card mb8" style="padding:16px 20px;">
      <div class="flex-cb">
        <div style="flex:1;min-width:0;">
          <div class="bold" style="font-size:.95rem;">${name}</div>
          <div class="txt-xs txt-faint mt8">
            ${r.experience_years || 0} yrs experience &nbsp;·&nbsp;
            ${(r.skills || []).length} skills extracted &nbsp;·&nbsp;
            Quality ${(r.completeness_score || 0).toFixed(0)}%
          </div>
          ${r.skills?.length ? `<div class="chip-group mt8">${chips(r.skills.slice(0,14), 'chip-green')}</div>` : ''}
        </div>
        <button class="btn btn-danger btn-sm" style="margin-left:16px;flex-shrink:0;"
                onclick="delResume(${r.id}, this)">Delete</button>
      </div>
    </div>`;
  }).join('');
}

function initUploadZone(allResumes) {
  const zone  = document.getElementById('upZone');
  const input = document.getElementById('upInput');
  const btn   = document.getElementById('upBtn');
  const srch  = document.getElementById('resumeSearch');
  S.pendingFiles = [];

  const prevent = e => e.preventDefault();
  zone.addEventListener('dragenter', prevent);
  zone.addEventListener('dragover',  e => { prevent(e); zone.classList.add('drag-on'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-on'));
  zone.addEventListener('drop', e => {
    prevent(e); zone.classList.remove('drag-on');
    addFiles(e.dataTransfer.files);
  });
  input.addEventListener('change', () => addFiles(input.files));
  btn.addEventListener('click', doUpload);

  srch.addEventListener('input', () => {
    const q = srch.value.toLowerCase();
    const filtered = q
      ? allResumes.filter(r =>
          (r.candidate_name || '').toLowerCase().includes(q) ||
          (r.skills || []).some(s => s.toLowerCase().includes(q)))
      : allResumes;
    document.getElementById('resumeList').innerHTML = buildResumeList(filtered);
  });
}

function addFiles(files) {
  Array.from(files).forEach(f => {
    if (!S.pendingFiles.find(p => p.name === f.name && p.size === f.size)) {
      S.pendingFiles.push(f);
    }
  });
  syncFileList();
}

function syncFileList() {
  const list    = document.getElementById('upFileList');
  const actions = document.getElementById('upActions');
  const btn     = document.getElementById('upBtn');
  if (!list) return;
  if (!S.pendingFiles.length) {
    list.innerHTML = '';
    if (actions) actions.style.display = 'none';
    return;
  }
  if (actions) actions.style.display = 'block';
  list.innerHTML = S.pendingFiles.map((f, i) => {
    const ext = f.name.split('.').pop().toUpperCase();
    return `
    <div class="file-item" id="fi${i}">
      <div class="file-ext">${ext}</div>
      <div class="file-info">
        <div class="file-name">${esc(f.name)}</div>
        <div class="file-size">${fmtBytes(f.size)}</div>
      </div>
      <button class="file-rm" onclick="rmFile(${i})">&#x2715;</button>
    </div>`;
  }).join('');
  if (btn) btn.textContent = `Upload and Parse ${S.pendingFiles.length} File${S.pendingFiles.length > 1 ? 's' : ''}`;
}

window.rmFile = i => { S.pendingFiles.splice(i, 1); syncFileList(); };

async function doUpload() {
  if (!S.pendingFiles.length) return;
  const btn = document.getElementById('upBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spin"></span> Uploading…';

  const form = new FormData();
  S.pendingFiles.forEach(f => form.append('files', f, f.name));

  try {
    const results = await API.post('/upload-resume', { form });
    S.pendingFiles = [];
    syncFileList();
    toast(`${results.length} resume(s) processed`, 'success');

    document.getElementById('upResults').innerHTML = `
    <div class="mt24">
      ${secLbl(`${results.length} RESUMES PARSED`)}
      ${results.map(r => `
      <div class="card mb8" style="padding:14px 18px;">
        <div class="flex-cb mb8">
          <span class="bold">${esc(r.candidate_name || r.filename)}</span>
          <span class="badge b-suitable">${(r.completeness_score || 0).toFixed(0)}% quality</span>
        </div>
        <div class="chip-group">${chips(r.skills || [], 'chip-green', 20)}</div>
      </div>`).join('')}
    </div>`;
  } catch (err) {
    toast('Upload failed: ' + err.message, 'error');
    btn.disabled = false;
    btn.textContent = `Upload and Parse ${S.pendingFiles.length} Files`;
  }
}

window.delResume = async (id, btn) => {
  btn.disabled = true; btn.textContent = '…';
  try {
    await API.delete(`/delete/${id}`);
    btn.closest('.card').remove();
    toast('Resume deleted', 'success', 2000);
  } catch {
    toast('Delete failed', 'error');
    btn.disabled = false; btn.textContent = 'Delete';
  }
};

document.addEventListener('click', e => {
  if (e.target.id === 'demoBtn') generateSample();
});

async function generateSample() {
  const btn = document.getElementById('demoBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spin"></span> Generating…';
  try {
    const r = await API.post('/generate-sample');
    toast(`Created ${r.resumes} resumes and ${r.jobs} job descriptions`, 'success');
    btn.textContent = 'Done — Sample Data Created';
  } catch (err) {
    toast('Failed: ' + err.message, 'error');
    btn.disabled = false;
    btn.textContent = 'Generate Sample Data';
  }
}

/* =============================================================
   JOBS PAGE
============================================================= */
async function renderJobs(app) {
  const jobs = await API.get('/jobs').catch(() => []);

  app.innerHTML = `
  ${ph('Job Description',
    'Define the role you are hiring for. Paste the job description as text or upload a file. The AI extracts required skills and qualifications automatically.')}

  <div class="tab-bar" id="jobTabBar">
    <button class="tab-btn active" data-tab="paste">Paste Text</button>
    <button class="tab-btn" data-tab="file">Upload File</button>
    <button class="tab-btn" data-tab="saved">Saved Jobs (${jobs.length})</button>
  </div>

  <div class="tab-pane active" data-pane="paste">
    ${infoStrip('The more detailed the job description, the more accurate the ranking. Include required skills, tools, responsibilities, and qualifications.')}
    <div style="max-width:640px;">
      <div class="form-g">
        <label class="form-lbl">Job Title</label>
        <input type="text" class="input" id="jdTitle" placeholder="e.g. Senior Data Scientist" />
      </div>
      <div class="form-g">
        <label class="form-lbl">Job Description</label>
        <textarea class="textarea" id="jdText" style="min-height:220px;"
                  placeholder="Paste the full job posting here…"></textarea>
      </div>
      <button class="btn btn-primary btn-lg" id="saveJdBtn">Save Job Description</button>
      <div id="jdResult" class="mt20"></div>
    </div>
  </div>

  <div class="tab-pane" data-pane="file">
    <div style="max-width:640px;">
      <div class="form-g">
        <label class="form-lbl">Job Title</label>
        <input type="text" class="input" id="jdTitleFile" placeholder="e.g. DevOps Engineer" />
      </div>
      <div class="upload-zone" id="jdUpZone">
        <input type="file" id="jdFileInput" accept=".pdf,.docx,.txt" />
        <div class="upload-icon">&#8593;</div>
        <div class="upload-title">Drop file here or <strong>click to browse</strong></div>
        <div class="upload-sub">PDF, DOCX, or TXT</div>
      </div>
      <div id="jdFilePv" class="file-list"></div>
      <div id="jdFileAct" style="display:none;" class="mt16">
        <button class="btn btn-primary" id="jdUpBtn">Upload and Save</button>
      </div>
    </div>
  </div>

  <div class="tab-pane" data-pane="saved">
    <div id="jobList">${buildJobList(jobs)}</div>
  </div>`;

  initTabs('jobTabBar');
  initJobPaste();
  initJobFileZone();
}

function buildJobList(jobs) {
  if (!jobs.length) return empty('No job descriptions yet', 'Use the tabs above to add one');
  return jobs.map(j => `
  <div class="card mb8" style="padding:18px 22px;">
    <div class="flex-cb mb8">
      <span class="bold" style="font-size:.95rem;">${esc(j.title)}</span>
      <button class="btn btn-danger btn-sm" onclick="delJob(${j.id}, this)">Delete</button>
    </div>
    <div class="txt-xs txt-faint mb8">${(j.required_skills || []).length} skills extracted</div>
    <div class="chip-group">${chips(j.required_skills || [], 'chip-green', 30)}</div>
  </div>`).join('');
}

function initJobPaste() {
  document.getElementById('saveJdBtn').addEventListener('click', async () => {
    const title = document.getElementById('jdTitle').value.trim();
    const text  = document.getElementById('jdText').value.trim();
    const btn   = document.getElementById('saveJdBtn');
    if (!title) { toast('Enter a job title', 'warning'); return; }
    if (!text)  { toast('Paste the job description', 'warning'); return; }
    btn.disabled = true; btn.innerHTML = '<span class="btn-spin"></span> Saving…';
    try {
      const form = new FormData(); form.append('title', title); form.append('text', text);
      const r = await API.post('/upload-job', { form });
      toast(`Saved "${r.title}"`, 'success');
      document.getElementById('jdTitle').value = '';
      document.getElementById('jdText').value = '';
      document.getElementById('jdResult').innerHTML = `
        ${secLbl('SKILLS EXTRACTED')}
        <div class="chip-group">${chips(r.required_skills || [], 'chip-green')}</div>`;
    } catch (err) { toast('Save failed: ' + err.message, 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Save Job Description'; }
  });
}

function initJobFileZone() {
  const zone  = document.getElementById('jdUpZone');
  const input = document.getElementById('jdFileInput');
  const pv    = document.getElementById('jdFilePv');
  const act   = document.getElementById('jdFileAct');
  let file    = null;

  function setFile(f) {
    file = f;
    const ext = f.name.split('.').pop().toUpperCase();
    pv.innerHTML = `
    <div class="file-item">
      <div class="file-ext">${ext}</div>
      <div class="file-info">
        <div class="file-name">${esc(f.name)}</div>
        <div class="file-size">${fmtBytes(f.size)}</div>
      </div>
    </div>`;
    act.style.display = 'block';
  }

  const p = e => e.preventDefault();
  zone.addEventListener('dragenter', p);
  zone.addEventListener('dragover',  e => { p(e); zone.classList.add('drag-on'); });
  zone.addEventListener('dragleave', () => zone.classList.remove('drag-on'));
  zone.addEventListener('drop', e => { p(e); zone.classList.remove('drag-on'); if (e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
  input.addEventListener('change', () => { if (input.files[0]) setFile(input.files[0]); });

  document.getElementById('jdUpBtn').addEventListener('click', async () => {
    const title = document.getElementById('jdTitleFile').value.trim();
    if (!title) { toast('Enter a job title', 'warning'); return; }
    if (!file)  { toast('Select a file', 'warning'); return; }
    const btn = document.getElementById('jdUpBtn');
    btn.disabled = true; btn.innerHTML = '<span class="btn-spin"></span> Uploading…';
    try {
      const form = new FormData(); form.append('title', title); form.append('file', file, file.name);
      const r = await API.post('/upload-job', { form });
      toast(`Saved "${r.title}"`, 'success');
    } catch (err) { toast('Upload failed: ' + err.message, 'error'); }
    finally { btn.disabled = false; btn.textContent = 'Upload and Save'; }
  });
}

window.delJob = async (id, btn) => {
  btn.disabled = true; btn.textContent = '…';
  try {
    await API.delete(`/jobs/${id}`);
    btn.closest('.card').remove();
    toast('Job description deleted', 'success', 2000);
  } catch {
    toast('Delete failed', 'error');
    btn.disabled = false; btn.textContent = 'Delete';
  }
};

/* =============================================================
   RANKINGS PAGE
============================================================= */
async function renderRankings(app) {
  const jobs = await API.get('/jobs').catch(() => []);
  if (!jobs.length) {
    app.innerHTML = ph('Ranking Results', 'Rank candidates against a job description.') +
      infoStrip('No job descriptions found. Go to <b>Job Description</b> to add one first.');
    return;
  }

  const opts = jobs.map(j => `<option value="${j.id}">${esc(j.title)}</option>`).join('');

  app.innerHTML = `
  ${ph('Ranking Results',
    'Select a job description, choose a similarity engine, and run the ranking. Every resume gets a score, a recommendation, and a full skill gap breakdown.')}

  <div class="rank-panel">
    <div class="rank-controls">
      <div class="rank-ctrl">
        <label class="form-lbl">Job Description</label>
        <select class="select" id="rkJob">${opts}</select>
      </div>
      <div class="rank-ctrl-sm">
        <label class="form-lbl">Engine</label>
        <select class="select" id="rkEngine">
          <option value="tfidf">TF-IDF (Fast)</option>
          <option value="sbert">SBERT (Semantic)</option>
        </select>
      </div>
      <div class="rank-ctrl-sm">
        <label class="form-lbl">Min Score &nbsp;<span id="minScoreLbl" style="color:var(--text-faint);font-weight:400;">(0%)</span></label>
        <input type="range" id="rkMin" min="0" max="100" value="0"
               oninput="document.getElementById('minScoreLbl').textContent='('+this.value+'%)';" />
      </div>
      <div class="rank-ctrl-btns">
        <button class="btn btn-primary btn-lg" id="rkRunBtn">Run Ranking</button>
        <button class="btn btn-secondary" id="rkLoadBtn">Load Saved</button>
      </div>
    </div>
  </div>

  <div id="rkResults">
    ${S.rankResults
      ? buildRankResults(S.rankResults.results, S.rankResults.job_title)
      : infoStrip('Click <b>Run Ranking</b> to start. Results are saved automatically and can be loaded next time.')}
  </div>`;

  document.getElementById('rkRunBtn').addEventListener('click', runRanking);
  document.getElementById('rkLoadBtn').addEventListener('click', loadRanking);
  document.getElementById('rkMin').addEventListener('input', filterByScore);

  if (S.rankResults) setTimeout(animateBars, 80);
}

function buildRankResults(results, jobTitle) {
  if (!results?.length) return empty('No results', 'Run the ranking first');

  const scores = results.map(r => r.similarity_score);
  const top    = Math.max(...scores).toFixed(1);
  const avg    = (scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(1);
  const exc    = results.filter(r => r.recommendation === 'Excellent Candidate').length;

  return `
  <div class="g4 mb32">
    ${sc(top + '%',        'Top Score',    'BEST MATCH')}
    ${sc(avg + '%',        'Average Score','ALL CANDIDATES')}
    ${sc(results.length,   'Candidates',   'IN RESULTS')}
    ${sc(exc,              'Excellent',    'HIGH MATCHES')}
  </div>

  <div class="flex-cb mb20" style="flex-wrap:wrap;gap:12px;">
    <div class="filter-bar" style="flex:1;margin:0;">
      <input type="text" class="input" id="rkSearch" placeholder="Search candidate name…" oninput="filterCandidates()" />
      <select class="select" id="rkRec" style="max-width:220px;" onchange="filterCandidates()">
        <option value="">All Recommendations</option>
        <option>Excellent Candidate</option><option>Strong Match</option>
        <option>Suitable</option><option>Average Match</option><option>Not Recommended</option>
      </select>
    </div>
    <div class="btn-row">
      <button class="btn btn-secondary btn-sm" onclick="exportCSV()">Download CSV</button>
      <button class="btn btn-secondary btn-sm" onclick="exportXLS()">Download Excel</button>
    </div>
  </div>

  ${secLbl(`CANDIDATES — ${esc(jobTitle)}`)}
  <div id="candList">${buildCandidates(results)}</div>`;
}

function buildCandidates(results, nameFilter = '', recFilter = '', minScore = 0) {
  let list = results;
  if (nameFilter) list = list.filter(r => (r.candidate_name || '').toLowerCase().includes(nameFilter));
  if (recFilter)  list = list.filter(r => r.recommendation === recFilter);
  if (minScore)   list = list.filter(r => r.similarity_score >= minScore);
  if (!list.length) return empty('No candidates match the filter');

  return list.map(r => {
    const name    = esc(r.candidate_name || r.filename);
    const matched = r.matched_skills || [];
    const missing = r.missing_skills || [];
    const extra   = r.extra_skills   || [];

    return `
    <div class="cand-card" onclick="this.classList.toggle('open')">
      <div class="cand-hd">
        ${rankBadge(r.rank)}
        <div class="cand-info">
          <div class="cand-name">${name}</div>
          <div class="cand-meta">
            ${r.experience_years || 0} yrs experience &nbsp;·&nbsp;
            Quality ${(r.quality_score || 0).toFixed(0)}% &nbsp;·&nbsp;
            KW density ${(r.keyword_density || 0).toFixed(2)}%
          </div>
        </div>
        ${recBadge(r.recommendation)}
        <div class="expand-icon">&#9654;</div>
      </div>

      ${scoreBar(r.similarity_score)}

      <div class="cand-details">
        <div class="g2" style="gap:20px;">
          <div>
            ${matched.length ? `${secLbl('MATCHED SKILLS')}<div class="chip-group">${chips(matched, 'chip-green')}</div>` : ''}
            ${extra.length   ? `<div class="mt12">${secLbl('ADDITIONAL SKILLS')}<div class="chip-group">${chips(extra.slice(0,12), 'chip-blue')}</div></div>` : ''}
          </div>
          <div>
            ${missing.length
              ? `${secLbl('MISSING SKILLS')}<div class="chip-group">${chips(missing, 'chip-red')}</div>`
              : `<div style="background:var(--success-lt);border:1px solid var(--success-bd);border-radius:var(--r);padding:18px;text-align:center;">
                   <div style="font-weight:700;color:var(--success);">All required skills matched</div>
                 </div>`}
          </div>
        </div>
      </div>
    </div>`;
  }).join('');
}

window.filterCandidates = function() {
  if (!S.rankResults) return;
  const nm  = (document.getElementById('rkSearch')?.value || '').toLowerCase();
  const rec = document.getElementById('rkRec')?.value || '';
  const min = parseFloat(document.getElementById('rkMin')?.value || 0);
  const el  = document.getElementById('candList');
  if (el) { el.innerHTML = buildCandidates(S.rankResults.results, nm, rec, min); setTimeout(animateBars, 50); }
};

window.filterByScore = function() {
  filterCandidates();
};

async function runRanking() {
  const jobId  = document.getElementById('rkJob').value;
  const engine = document.getElementById('rkEngine').value;
  const btn    = document.getElementById('rkRunBtn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spin"></span> Computing…';
  try {
    const rr = await API.get('/rank', { job_id: jobId, engine });
    S.rankResults = rr;
    document.getElementById('rkResults').innerHTML = buildRankResults(rr.results, rr.job_title);
    setTimeout(animateBars, 80);
    toast(`Ranked ${rr.results.length} candidates`, 'success');
  } catch (err) {
    toast('Ranking failed: ' + err.message, 'error');
  } finally {
    btn.disabled = false; btn.textContent = 'Run Ranking';
  }
}

async function loadRanking() {
  const jobId = document.getElementById('rkJob').value;
  const btn   = document.getElementById('rkLoadBtn');
  btn.disabled = true; btn.innerHTML = '<span class="btn-spin btn-spin-dk"></span>';
  try {
    const rr = await API.get('/results', { job_id: jobId });
    S.rankResults = rr;
    document.getElementById('rkResults').innerHTML = buildRankResults(rr.results, rr.job_title);
    setTimeout(animateBars, 80);
    toast('Results loaded', 'info');
  } catch {
    toast('No saved results for this job — run the ranking first', 'warning');
  } finally {
    btn.disabled = false; btn.textContent = 'Load Saved';
  }
}

window.exportCSV = function() {
  if (!S.rankResults) return;
  const rows = [
    ['Rank','Name','Score','Recommendation','Experience (yrs)','Quality','Matched Skills','Missing Skills'],
    ...S.rankResults.results.map(r => [
      r.rank, r.candidate_name || r.filename, r.similarity_score.toFixed(1),
      r.recommendation, r.experience_years || 0, (r.quality_score || 0).toFixed(0),
      (r.matched_skills || []).join('; '), (r.missing_skills || []).join('; '),
    ]),
  ];
  download('ranking.csv', 'text/csv', rows.map(row => row.map(c => `"${c}"`).join(',')).join('\n'));
};

window.exportXLS = function() {
  if (!S.rankResults) return;
  const rows = [
    ['Rank','Name','Score','Recommendation','Experience (yrs)','Quality','Matched Skills','Missing Skills'],
    ...S.rankResults.results.map(r => [
      r.rank, r.candidate_name || r.filename, r.similarity_score.toFixed(1),
      r.recommendation, r.experience_years || 0, (r.quality_score || 0).toFixed(0),
      (r.matched_skills || []).join(', '), (r.missing_skills || []).join(', '),
    ]),
  ];
  download('ranking.xls', 'application/vnd.ms-excel', rows.map(r => r.join('\t')).join('\n'));
};

function download(name, mime, content) {
  const a = document.createElement('a');
  a.href     = URL.createObjectURL(new Blob([content], { type: mime }));
  a.download = name;
  a.click();
  URL.revokeObjectURL(a.href);
}

/* =============================================================
   ANALYTICS PAGE
============================================================= */
async function renderAnalytics(app) {
  if (!S.rankResults) {
    const jobs = await API.get('/jobs').catch(() => []);
    const opts = jobs.map(j => `<option value="${j.id}">${esc(j.title)}</option>`).join('');
    app.innerHTML = `
    ${ph('Analytics', 'Visual breakdown of ranking results.')}
    ${infoStrip('No results loaded yet. Load results for a job to see charts.')}
    ${jobs.length ? `
    <div class="card" style="max-width:420px;padding:24px;">
      <div class="form-g">
        <label class="form-lbl">Load Results For</label>
        <select class="select" id="anJobSel">${opts}</select>
      </div>
      <button class="btn btn-primary mt16" id="anLoadBtn">Load Results</button>
    </div>` : ''}`;

    document.getElementById('anLoadBtn')?.addEventListener('click', async () => {
      const id = document.getElementById('anJobSel').value;
      try {
        S.rankResults = await API.get('/results', { job_id: id });
        navigate('analytics');
      } catch { toast('No results found for this job', 'warning'); }
    });
    return;
  }

  const results = S.rankResults.results;
  app.innerHTML = `
  ${ph('Analytics', `Visual breakdown for: ${esc(S.rankResults.job_title)} — ${results.length} candidates`)}

  <div class="g2 mb24">
    <div class="chart-card"><div class="chart-title">Score Distribution</div><canvas id="chDist"></canvas></div>
    <div class="chart-card"><div class="chart-title">Recommendation Split</div><canvas id="chRec"></canvas></div>
  </div>

  <div class="g2 mb24">
    <div class="chart-card"><div class="chart-title">Skill Coverage — Top 15</div><canvas id="chSkill"></canvas></div>
    <div class="chart-card"><div class="chart-title">Experience vs Score</div><canvas id="chExp"></canvas></div>
  </div>

  <div class="card">
    <div class="flex-cb mb20">
      <div class="card-title" style="font-weight:700;">All Candidates</div>
      <button class="btn btn-secondary btn-sm" onclick="exportCSV()">Download CSV</button>
    </div>
    <div class="tbl-wrap">
      <table>
        <thead><tr>
          <th>Rank</th><th>Candidate</th><th>Score</th>
          <th>Recommendation</th><th>Experience</th><th>Quality</th>
          <th>Matched</th><th>Missing</th>
        </tr></thead>
        <tbody>
          ${results.map(r => `
          <tr>
            <td>${rankBadge(r.rank)}</td>
            <td class="bold">${esc(r.candidate_name || r.filename)}</td>
            <td><b>${r.similarity_score.toFixed(1)}%</b></td>
            <td>${recBadge(r.recommendation)}</td>
            <td>${r.experience_years || 0} yrs</td>
            <td>${(r.quality_score || 0).toFixed(0)}%</td>
            <td>${(r.matched_skills || []).length}</td>
            <td>${(r.missing_skills || []).length}</td>
          </tr>`).join('')}
        </tbody>
      </table>
    </div>
  </div>`;

  drawCharts(results);
}

function drawCharts(results) {
  const scores = results.map(r => r.similarity_score);

  // Score histogram
  const bins  = ['0–20', '20–40', '40–60', '60–80', '80–100'];
  const bdata = [0, 0, 0, 0, 0];
  scores.forEach(s => { bdata[Math.min(4, Math.floor(s / 20))]++; });
  S.charts.dist = new Chart(document.getElementById('chDist'), {
    type: 'bar',
    data: {
      labels: bins,
      datasets: [{ data: bdata, label: 'Candidates',
        backgroundColor: ['#EF4444','#F97316','#EAB308','#3B82F6','#10B981'],
        borderRadius: 6, borderWidth: 0 }],
    },
    options: { plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } } },
  });

  // Recommendation donut
  const recMap   = {};
  results.forEach(r => { recMap[r.recommendation] = (recMap[r.recommendation] || 0) + 1; });
  const rcColors = {
    'Excellent Candidate': '#10B981', 'Strong Match': '#3B82F6',
    'Suitable': '#EAB308', 'Average Match': '#F97316', 'Not Recommended': '#EF4444',
  };
  S.charts.rec = new Chart(document.getElementById('chRec'), {
    type: 'doughnut',
    data: {
      labels: Object.keys(recMap),
      datasets: [{ data: Object.values(recMap),
        backgroundColor: Object.keys(recMap).map(k => rcColors[k] || '#94A3B8'),
        borderWidth: 0, hoverOffset: 5 }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { font: { size: 11 }, boxWidth: 12 } } } },
  });

  // Skill coverage bar (top 15)
  const top15 = results.slice(0, 15);
  S.charts.skill = new Chart(document.getElementById('chSkill'), {
    type: 'bar',
    data: {
      labels: top15.map(r => (r.candidate_name || r.filename).split(' ')[0]),
      datasets: [
        { label: 'Matched', data: top15.map(r => (r.matched_skills || []).length), backgroundColor: '#A7F3D0', borderRadius: 4, borderWidth: 0 },
        { label: 'Missing', data: top15.map(r => (r.missing_skills || []).length), backgroundColor: '#FECDD3', borderRadius: 4, borderWidth: 0 },
      ],
    },
    options: { indexAxis: 'y', plugins: { legend: { position: 'top' } }, scales: { x: { beginAtZero: true } } },
  });

  // Experience scatter
  const ptColors = results.map(r => {
    const s = r.similarity_score;
    return s >= 80 ? '#10B981' : s >= 60 ? '#3B82F6' : s >= 40 ? '#EAB308' : '#EF4444';
  });
  S.charts.exp = new Chart(document.getElementById('chExp'), {
    type: 'scatter',
    data: {
      datasets: [{
        label: 'Candidates',
        data: results.map(r => ({ x: r.experience_years || 0, y: r.similarity_score })),
        backgroundColor: ptColors,
        pointRadius: 7, pointHoverRadius: 9,
      }],
    },
    options: {
      scales: {
        x: { title: { display: true, text: 'Years of Experience' } },
        y: { title: { display: true, text: 'Score (%)' }, min: 0, max: 100 },
      },
    },
  });
}

/* =============================================================
   HISTORY PAGE
============================================================= */
async function renderHistory(app) {
  const history = await API.get('/history').catch(() => []);

  app.innerHTML = `
  ${ph('Ranking History',
    'Every ranking session is saved automatically. Load any previous result to view the full rankings or analytics without re-running the AI engine.')}

  ${!history.length ? empty('No history yet', 'Run your first ranking from the Rankings page') : `
  ${secLbl(`${history.length} JOB${history.length > 1 ? 'S' : ''} ON RECORD`)}
  ${history.map(h => `
  <div class="card mb12">
    <div class="flex-cb mb16">
      <div>
        <div class="bold" style="font-size:1rem;">${esc(h.job_title)}</div>
        <div class="txt-xs txt-faint mt8">
          ${fmtDate(h.ranked_at)} &nbsp;·&nbsp; ${h.total_resumes || 0} candidates ranked
        </div>
      </div>
      ${h.total_resumes > 0
        ? `<button class="btn btn-primary" onclick="loadHistRr(${h.job_id}, this)">Load Results</button>`
        : `<span class="badge b-not">No data</span>`}
    </div>
    ${h.total_resumes > 0 ? `
    <div class="g4">
      ${sc(esc(h.top_candidate || '—'), 'Top Candidate', 'BEST MATCH')}
      ${sc(h.top_score ? h.top_score.toFixed(1) + '%' : '—', 'Top Score', 'HIGHEST')}
      ${sc(h.total_resumes, 'Candidates', 'RANKED')}
      ${sc(fmtDate(h.ranked_at), 'Date', 'RUN ON')}
    </div>` : ''}
  </div>`).join('')}
  `}`;
}

window.loadHistRr = async function(jobId, btn) {
  btn.disabled = true; btn.innerHTML = '<span class="btn-spin"></span>';
  try {
    S.rankResults = await API.get('/results', { job_id: jobId });
    toast('Results loaded — viewing Rankings', 'success');
    navigate('rankings');
  } catch {
    toast('Could not load results', 'error');
    btn.disabled = false; btn.textContent = 'Load Results';
  }
};

/* =============================================================
   BOOT
============================================================= */
function boot() {
  document.querySelectorAll('.nav-link').forEach(el => {
    el.addEventListener('click', () => navigate(el.dataset.page));
  });
  const page = (location.hash.replace('#', '') || 'home');
  checkStatus();
  setInterval(checkStatus, 30000);
  navigate(page);
}

document.addEventListener('DOMContentLoaded', boot);
