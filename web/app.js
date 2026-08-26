/**
 * Claude.ai Limits Tracker - Frontend Logic & Live Real-time Engine
 */

const CIRCUMFERENCE = 2 * Math.PI * 82; // ~515.22px for r=82

let currentData = null;
let refreshIntervalSec = 60;
let refreshTimer = null;
let countdownRemaining = 60;
let secondTicker = null;

// DOM Elements
const claudeStatusPill = document.getElementById('claudeStatusPill');
const claudeStatusText = document.getElementById('claudeStatusText');
const refreshBtn = document.getElementById('refreshBtn');
const orgName = document.getElementById('orgName');
const planTier = document.getElementById('planTier');
const lastUpdated = document.getElementById('lastUpdated');
const refreshIntervalSelect = document.getElementById('refreshIntervalSelect');
const nextRefreshCountdown = document.getElementById('nextRefreshCountdown');

// Session 5-Hour Elements
const sessionCard = document.getElementById('sessionCard');
const sessionGaugeProgress = document.getElementById('sessionGaugeProgress');
const sessionPercentLeft = document.getElementById('sessionPercentLeft');
const sessionPercentUsed = document.getElementById('sessionPercentUsed');
const sessionStatusBadge = document.getElementById('sessionStatusBadge');
const sessionResetHuman = document.getElementById('sessionResetHuman');
const sessionResetDetail = document.getElementById('sessionResetDetail');
const sessionLinearFill = document.getElementById('sessionLinearFill');

// Weekly Elements
const weeklyCard = document.getElementById('weeklyCard');
const weeklyGaugeProgress = document.getElementById('weeklyGaugeProgress');
const weeklyPercentLeft = document.getElementById('weeklyPercentLeft');
const weeklyPercentUsed = document.getElementById('weeklyPercentUsed');
const weeklyStatusBadge = document.getElementById('weeklyStatusBadge');
const weeklyResetHuman = document.getElementById('weeklyResetHuman');
const weeklyResetDetail = document.getElementById('weeklyResetDetail');
const weeklyLinearFill = document.getElementById('weeklyLinearFill');

// Models & History
const modelsSection = document.getElementById('modelsSection');
const modelsGrid = document.getElementById('modelsGrid');
const historyCanvas = document.getElementById('historyChart');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
  setupEventListeners();
  fetchStatus();
  startSecondTicker();
});

function setupEventListeners() {
  refreshBtn.addEventListener('click', () => {
    fetchStatus();
  });

  refreshIntervalSelect.addEventListener('change', (e) => {
    refreshIntervalSec = parseInt(e.target.value, 10);
    countdownRemaining = refreshIntervalSec;
    resetAutoRefresh();
  });

  window.addEventListener('resize', () => {
    if (currentData && currentData.history) {
      renderHistoryChart(currentData.history);
    }
  });
}

function getColorForPercent(pctLeft) {
  if (pctLeft > 40) return { stroke: '#10b981', glow: 'rgba(16, 185, 129, 0.25)', class: 'healthy' };
  if (pctLeft > 15) return { stroke: '#f59e0b', glow: 'rgba(245, 158, 11, 0.25)', class: 'warning' };
  return { stroke: '#ef4444', glow: 'rgba(239, 68, 68, 0.25)', class: 'danger' };
}

function setGauge(circleEl, pctLeft) {
  const clamped = Math.max(0, Math.min(100, pctLeft));
  const offset = CIRCUMFERENCE - (clamped / 100) * CIRCUMFERENCE;
  const col = getColorForPercent(clamped);

  circleEl.style.strokeDasharray = CIRCUMFERENCE;
  circleEl.style.strokeDashoffset = offset;
  circleEl.style.stroke = col.stroke;
}

async function fetchStatus() {
  const spinIcon = refreshBtn.querySelector('.spin-icon');
  if (spinIcon) spinIcon.classList.add('spinning');
  refreshBtn.disabled = true;

  try {
    const res = await fetch('/api/status', { cache: 'no-store' });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    currentData = data;
    updateUI(data);
  } catch (err) {
    console.error('Failed to fetch status:', err);
    claudeStatusPill.className = 'status-pill';
    claudeStatusText.textContent = 'Server Disconnected';
  } finally {
    if (spinIcon) spinIcon.classList.remove('spinning');
    refreshBtn.disabled = false;
    countdownRemaining = refreshIntervalSec;
  }
}

function updateUI(data) {
  if (!data.success) {
    claudeStatusPill.className = 'status-pill';
    claudeStatusText.textContent = 'Claude Closed / No Session';
    orgName.textContent = data.error || 'Failed to connect';
    return;
  }

  // Header & Status
  if (data.claude_running) {
    claudeStatusPill.className = 'status-pill running';
    claudeStatusText.textContent = 'Claude Desktop Active';
  } else {
    claudeStatusPill.className = 'status-pill';
    claudeStatusText.textContent = 'Claude Idle (Cached Session)';
  }

  const account = data.account || {};
  orgName.textContent = account.org_name || 'Personal Account';
  planTier.textContent = account.plan_tier || 'Free';

  const d = new Date(data.last_updated || Date.now());
  lastUpdated.textContent = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

  // 1. Session (5-Hour) Limit Update
  const s5h = data.session_5h || {};
  const sLeft = s5h.percent_left ?? 100.0;
  const sUsed = s5h.percent_used ?? 0.0;
  const sColor = getColorForPercent(sLeft);

  setGauge(sessionGaugeProgress, sLeft);
  sessionPercentLeft.textContent = `${Math.round(sLeft)}%`;
  sessionPercentUsed.textContent = `${sUsed.toFixed(1)}% used`;

  sessionStatusBadge.className = `status-indicator ${sColor.class}`;
  sessionStatusBadge.textContent = sLeft > 40 ? 'Healthy' : (sLeft > 15 ? 'Moderate' : 'Low Buffer');

  sessionLinearFill.style.width = `${sLeft}%`;
  sessionLinearFill.style.background = sLeft > 40
    ? 'linear-gradient(90deg, #10b981, #34d399)'
    : (sLeft > 15 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #ef4444, #f87171)');

  updateCountdownDisplay();

  // 2. Weekly Limit Update
  const weekly = data.weekly || {};
  const wLeft = weekly.percent_left ?? 100.0;
  const wUsed = weekly.percent_used ?? 0.0;
  const wColor = getColorForPercent(wLeft);

  setGauge(weeklyGaugeProgress, wLeft);
  weeklyPercentLeft.textContent = `${Math.round(wLeft)}%`;
  weeklyPercentUsed.textContent = `${wUsed.toFixed(1)}% used`;

  weeklyStatusBadge.className = `status-indicator ${wColor.class}`;
  weeklyStatusBadge.textContent = wLeft > 40 ? 'Healthy' : (wLeft > 15 ? 'Moderate' : 'Low Buffer');

  weeklyLinearFill.style.width = `${wLeft}%`;
  weeklyLinearFill.style.background = wLeft > 40
    ? 'linear-gradient(90deg, #06b6d4, #38bdf8)'
    : (wLeft > 15 ? 'linear-gradient(90deg, #f59e0b, #fbbf24)' : 'linear-gradient(90deg, #ef4444, #f87171)');

  if (weekly.resets_at) {
    const wDate = new Date(weekly.resets_at);
    weeklyResetDetail.textContent = `Resets on ${wDate.toLocaleDateString([], { weekday: 'short', month: 'short', day: 'numeric' })} at ${wDate.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
  } else {
    weeklyResetDetail.textContent = 'All models 7-day rolling window';
  }

  // 3. Scoped Models (if any)
  const models = data.models || [];
  if (models.length > 0) {
    modelsSection.style.display = 'block';
    modelsGrid.innerHTML = models.map(m => `
      <div class="model-item">
        <div class="model-name"><strong>${m.name}</strong></div>
        <div class="model-reset" style="color: var(--text-muted); font-size: 0.8rem;">${m.resets_in_human || ''}</div>
        <div class="model-pct" style="color: #34d399; font-weight: 700;">${m.percent_left}% left</div>
      </div>
    `).join('');
  } else {
    modelsSection.style.display = 'none';
  }

  // 4. Render History Chart
  if (data.history && data.history.length > 0) {
    renderHistoryChart(data.history);
  }
}

function updateCountdownDisplay() {
  if (!currentData) return;
  const s5h = currentData.session_5h;
  const weekly = currentData.weekly;

  // Session reset live countdown
  if (s5h && s5h.resets_at) {
    const target = new Date(s5h.resets_at).getTime();
    const diff = Math.max(0, target - Date.now());
    if (diff === 0) {
      sessionResetHuman.textContent = 'Resets now (Cooldown over)';
      sessionResetDetail.textContent = 'Limit refreshed';
    } else {
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      sessionResetHuman.textContent = `Resets in ${h}h ${m}m ${s}s`;
      const t = new Date(s5h.resets_at);
      sessionResetDetail.textContent = `Reset target: ${t.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    }
  } else {
    sessionResetHuman.textContent = 'Full limit available';
    sessionResetDetail.textContent = 'No active cooldown';
  }

  // Weekly reset live countdown
  if (weekly && weekly.resets_at) {
    const target = new Date(weekly.resets_at).getTime();
    const diff = Math.max(0, target - Date.now());
    if (diff === 0) {
      weeklyResetHuman.textContent = 'Resets now';
    } else {
      const d = Math.floor(diff / 86400000);
      const h = Math.floor((diff % 86400000) / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      weeklyResetHuman.textContent = d > 0 ? `Resets in ${d}d ${h}h` : `Resets in ${h}h ${m}m`;
    }
  } else {
    weeklyResetHuman.textContent = 'Full limit available';
  }
}

function startSecondTicker() {
  if (secondTicker) clearInterval(secondTicker);
  secondTicker = setInterval(() => {
    // Tick cooldowns
    updateCountdownDisplay();

    // Auto-refresh countdown
    if (countdownRemaining > 1) {
      countdownRemaining--;
      nextRefreshCountdown.textContent = `Auto-refresh in ${countdownRemaining}s`;
    } else {
      fetchStatus();
    }
  }, 1000);
}

function resetAutoRefresh() {
  countdownRemaining = refreshIntervalSec;
}

function renderHistoryChart(samples) {
  if (!historyCanvas) return;
  const ctx = historyCanvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = historyCanvas.getBoundingClientRect();
  
  historyCanvas.width = rect.width * dpr;
  historyCanvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  ctx.clearRect(0, 0, w, h);

  const recent = samples.slice(-25);
  if (recent.length === 0) return;

  const padLeft = 20;
  const padRight = 20;
  const padBottom = 20;
  const padTop = 15;
  const chartW = w - padLeft - padRight;
  const chartH = h - padBottom - padTop;

  // Grid line
  ctx.strokeStyle = 'rgba(255, 255, 255, 0.06)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(padLeft, padTop + chartH);
  ctx.lineTo(padLeft + chartW, padTop + chartH);
  ctx.stroke();

  // Session usage line
  ctx.beginPath();
  ctx.strokeStyle = '#da7756';
  ctx.lineWidth = 2.5;
  ctx.lineJoin = 'round';

  const stepX = chartW / Math.max(1, recent.length - 1);

  recent.forEach((s, idx) => {
    const x = padLeft + idx * stepX;
    const used = Math.min(100, Math.max(0, s.session_5h_used || 0));
    const y = padTop + chartH - (used / 100) * chartH;
    if (idx === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  });
  ctx.stroke();

  // Gradient fill under session line
  ctx.lineTo(padLeft + (recent.length - 1) * stepX, padTop + chartH);
  ctx.lineTo(padLeft, padTop + chartH);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, padTop, 0, padTop + chartH);
  grad.addColorStop(0, 'rgba(218, 119, 86, 0.25)');
  grad.addColorStop(1, 'rgba(218, 119, 86, 0.0)');
  ctx.fillStyle = grad;
  ctx.fill();

  // Dots
  recent.forEach((s, idx) => {
    const x = padLeft + idx * stepX;
    const used = Math.min(100, Math.max(0, s.session_5h_used || 0));
    const y = padTop + chartH - (used / 100) * chartH;
    ctx.beginPath();
    ctx.arc(x, y, 3, 0, Math.PI * 2);
    ctx.fillStyle = '#da7756';
    ctx.fill();
  });
}
