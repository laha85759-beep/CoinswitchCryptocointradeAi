// ══════════════════════════════════════════════════════════════════════════
// THESMARTMAG QUANT TERMINAL • CORE APPLICATION & ADMIN PORTAL ENGINE
// ══════════════════════════════════════════════════════════════════════════

let currentTvSymbol = "BINANCE:BTCUSDT";
let currentView = "terminal";
let adminToken = sessionStorage.getItem("tsm_admin_token") || "";
let isBotPaused = false;
let currentTheme = localStorage.getItem("tsm_theme") || "dark";

// ── 1. Initialization ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initUtcClock();
  initTradingViewWidget("tradingview_widget_container", currentTvSymbol);
  initAgent3dCore();
  initWorkflowCycle();
  fetchRealData();
  setInterval(fetchRealData, 4000);
  checkAdminAuth();
});

// ── 1.1 Theme Switcher (Dark / Light) ──────────────────────────────────────
function initTheme() {
  applyTheme(currentTheme);
}

function toggleTheme() {
  currentTheme = currentTheme === "dark" ? "light" : "dark";
  localStorage.setItem("tsm_theme", currentTheme);
  applyTheme(currentTheme);
}

function applyTheme(theme) {
  const icon = document.getElementById("themeToggleIcon");
  const text = document.getElementById("themeToggleText");
  if (theme === "light") {
    document.body.classList.add("light-mode");
    if (icon) icon.textContent = "☀️";
    if (text) text.textContent = "LIGHT";
  } else {
    document.body.classList.remove("light-mode");
    if (icon) icon.textContent = "🌙";
    if (text) text.textContent = "DARK";
  }
}

// ── 2. Real-Time UTC Clock ─────────────────────────────────────────────────
function initUtcClock() {
  const clockEl = document.getElementById("live-utc-clock");
  setInterval(() => {
    const now = new Date();
    const utcStr = now.toUTCString().split(" ")[4] + " UTC";
    if (clockEl) clockEl.textContent = utcStr;
  }, 1000);
}

// ── 3. Tab & View Navigation ──────────────────────────────────────────────
function switchView(viewName) {
  currentView = viewName;
  
  // Update Tab Buttons
  document.querySelectorAll(".tsm-tab").forEach(tab => {
    if (tab.getAttribute("data-view") === viewName) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  // Update View Sections
  document.querySelectorAll(".tsm-view-section").forEach(sec => {
    sec.classList.remove("active");
  });
  
  const targetSec = document.getElementById(`view-${viewName}`);
  if (targetSec) {
    targetSec.classList.add("active");
  }

  // Handle Fullscreen Chart view
  if (viewName === "chart") {
    initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol);
  }
}

function toggleAdminView() {
  switchView("admin");
}

// ── 4. TradingView Pro Chart Integration ──────────────────────────────────
function initTradingViewWidget(containerId, symbol) {
  const container = document.getElementById(containerId);
  if (!container || typeof TradingView === "undefined") return;

  container.innerHTML = "";
  new TradingView.widget({
    "autosize": true,
    "symbol": symbol,
    "interval": "5",
    "timezone": "Etc/UTC",
    "theme": "dark",
    "style": "1",
    "locale": "en",
    "toolbar_bg": "#0b111a",
    "enable_publishing": false,
    "allow_symbol_change": true,
    "container_id": containerId,
    "hide_side_toolbar": false,
    "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies", "VWAP@tv-basicstudies"]
  });
}

function loadTvSymbol(symbol) {
  currentTvSymbol = symbol;
  
  document.querySelectorAll(".chart-coin-btn").forEach(btn => {
    if (btn.textContent.trim() === symbol.split(":")[1].replace("USDT", "")) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  initTradingViewWidget("tradingview_widget_container", currentTvSymbol);
}

// ── 5. Real-Time Telemetry & Data Polling ──────────────────────────────────
async function fetchRealData() {
  try {
    const res = await fetch("/api/terminal-data");
    if (!res.ok) return;
    const data = await res.json();

    // 1. Balances & Capital
    if (data.balances) {
      const totalUsdt = Number(data.balances.total_capital_usdt || 6.57).toFixed(2);
      const csUsdt = Number(data.balances.cs_usdt || 2.34).toFixed(2);
      const csInr = Number(data.balances.cs_inr || 11.41).toFixed(2);
      const deltaUsdt = Number(data.balances.delta_usdt || 4.17).toFixed(2);
      const deltaInr = (deltaUsdt * 88.0).toFixed(2);

      const capEl = document.getElementById("total-capital");
      if (capEl) capEl.innerHTML = `$${totalUsdt} <span class="kpi-unit">USDT</span>`;

      const csBalEl = document.getElementById("cs-bal-txt");
      if (csBalEl) csBalEl.textContent = `$${csUsdt} USDT (₹${csInr})`;

      const deltaBalEl = document.getElementById("delta-bal-txt");
      if (deltaBalEl) deltaBalEl.textContent = `$${deltaUsdt} USDT (₹${deltaInr})`;
    }

    // 2. Performance & PnL
    if (data.performance) {
      const pnlUsdt = Number(data.performance.total_realized_pnl_usdt || 0.0);
      const pnlEl = document.getElementById("total-pnl-value");
      if (pnlEl) {
        pnlEl.textContent = (pnlUsdt >= 0 ? "+$" : "-$") + Math.abs(pnlUsdt).toFixed(2) + " USDT";
        pnlEl.className = `kpi-value-large ${pnlUsdt >= 0 ? "green-text" : "red-text"}`;
      }
      const tradesEl = document.getElementById("closed-trades-count");
      if (tradesEl) tradesEl.textContent = data.performance.closed_trades_count || 0;
    }

    // 3. Tickers
    if (data.tickers) {
      updateTicker("header-btc", data.tickers.btc);
      updateTicker("header-eth", data.tickers.eth);
      updateTicker("header-sol", data.tickers.sol);
      updateTicker("header-ondo", data.tickers.ondo || 0.72);
      updateTicker("header-pepe", data.tickers.pepe || 0.0000078);
    }

    // 4. Open Positions
    if (data.open_positions) {
      const csCount = data.open_positions.cs_count || 0;
      const deltaCount = data.open_positions.delta_count || 0;
      const totalCount = data.open_positions.total_count || 0;

      const posTag = document.getElementById("positions-tag");
      if (posTag) posTag.textContent = `${totalCount} OPEN`;

      const openCountEl = document.getElementById("total-open-count");
      if (openCountEl) openCountEl.innerHTML = `${totalCount} <span class="kpi-unit">POSITIONS</span>`;

      const csCountEl = document.getElementById("cs-open-count");
      if (csCountEl) csCountEl.textContent = csCount;

      const deltaCountEl = document.getElementById("delta-open-count");
      if (deltaCountEl) deltaCountEl.textContent = deltaCount;

      renderPositionsTable(data.open_positions);
    }

    // 5. Signals / Committee
    if (data.advanced && data.advanced.signals_feed) {
      renderSignalsFeed(data.advanced.signals_feed);
    }

  } catch (err) {
    console.debug("Telemetry fetch error:", err);
  }
}

function updateTicker(elementId, val) {
  const el = document.getElementById(elementId);
  if (!el || val === undefined) return;
  const num = Number(val);
  el.textContent = num > 10 ? `$${num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}` : `$${num.toFixed(4)}`;
}

function renderPositionsTable(posData) {
  const tbody = document.getElementById("open-trades-tbody");
  if (!tbody) return;

  const allPositions = [
    ...(posData.coinswitch || []).map(p => ({...p, exchange: "CoinSwitch (Spot)"})),
    ...(posData.delta || []).map(p => ({...p, exchange: "Delta (Futures)"}))
  ];

  if (allPositions.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center empty-state">No open positions. Autonomous scanner primed for high-conviction breakout setups.</td></tr>`;
    return;
  }

  tbody.innerHTML = allPositions.map(pos => `
    <tr>
      <td><span class="live-tag">${pos.exchange}</span></td>
      <td><strong>${pos.symbol}</strong></td>
      <td><span class="${pos.direction === 'buy' || pos.direction === 'long' ? 'green-text' : 'red-text'}">${pos.direction.toUpperCase()}</span></td>
      <td>$${Number(pos.entry_price).toFixed(4)}</td>
      <td class="red-text">$${Number(pos.hard_sl || 0).toFixed(4)}</td>
      <td class="green-text">$${Number(pos.take_profit || 0).toFixed(4)}</td>
      <td><span class="green-text">${pos.trail_active ? '🟢 ACTIVE (+0.2%)' : 'ARMED'}</span></td>
      <td><span class="live-pill">LIVE</span></td>
    </tr>
  `).join("");
}

function renderSignalsFeed(signals) {
  const container = document.getElementById("signals-container");
  if (!container || !signals || signals.length === 0) return;

  container.innerHTML = signals.slice(0, 6).map(s => `
    <div class="signal-item">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <strong>${s.symbol}</strong>
        <span class="${s.signal === 'pump' || s.signal === 'buy' ? 'green-text' : 'red-text'} font-mono">${s.signal.toUpperCase()}</span>
      </div>
      <div style="font-size: 11px; color: var(--text-secondary); display: flex; justify-content: space-between;">
        <span>AI Consensus: <strong class="green-text">${(s.confidence * 100).toFixed(0)}%</strong></span>
        <span style="color: var(--text-muted);">${s.suspected_cause || 'SMC Liquidity Gap'}</span>
      </div>
    </div>
  `).join("");
}

// ── 6. Protected Admin Portal Authentication & Actions ─────────────────────
function checkAdminAuth() {
  const loginBox = document.getElementById("admin-login-box");
  const dashPanel = document.getElementById("admin-dashboard-panel");
  const adminNavBtnText = document.getElementById("adminNavBtnText");

  if (adminToken) {
    if (loginBox) loginBox.style.display = "none";
    if (dashPanel) dashPanel.style.display = "block";
    if (adminNavBtnText) adminNavBtnText.textContent = "ADMIN (LOGGED IN)";
    fetchAdminStatus();
  } else {
    if (loginBox) loginBox.style.display = "block";
    if (dashPanel) dashPanel.style.display = "none";
    if (adminNavBtnText) adminNavBtnText.textContent = "ADMIN PORTAL";
  }
}

async function handleAdminLogin(e) {
  e.preventDefault();
  const user = document.getElementById("adminUserInput").value.trim();
  const pass = document.getElementById("adminPassInput").value.trim();
  const errBox = document.getElementById("loginErrorMsg");
  const submitBtn = document.getElementById("loginSubmitBtn");

  submitBtn.textContent = "AUTHENTICATING...";
  submitBtn.disabled = true;
  if (errBox) errBox.style.display = "none";

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({username: user, password: pass})
    });
    const data = await res.json();

    if (res.ok && data.status === "success" && data.token) {
      adminToken = data.token;
      sessionStorage.setItem("tsm_admin_token", adminToken);
      checkAdminAuth();
    } else {
      if (errBox) {
        errBox.textContent = data.message || "Invalid administrative credentials.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    if (errBox) {
      errBox.textContent = "Connection error. Please try again.";
      errBox.style.display = "block";
    }
  } finally {
    submitBtn.textContent = "AUTHENTICATE ADMIN";
    submitBtn.disabled = false;
  }
}

function handleAdminLogout() {
  adminToken = "";
  sessionStorage.removeItem("tsm_admin_token");
  checkAdminAuth();
  switchView("terminal");
}

async function fetchAdminStatus() {
  if (!adminToken) return;
  try {
    const res = await fetch("/api/admin/status", {
      headers: {"Authorization": `Bearer ${adminToken}`}
    });
    if (!res.ok) {
      if (res.status === 401) handleAdminLogout();
      return;
    }
    const data = await res.json();

    if (data.bot_state) {
      isBotPaused = data.bot_state.is_paused;
      const toggleBtn = document.getElementById("botToggleBtn");
      const statusTxt = document.getElementById("botStatusText");
      if (toggleBtn && statusTxt) {
        if (isBotPaused) {
          toggleBtn.textContent = "RESUME BOT";
          toggleBtn.style.background = "var(--accent-green)";
          statusTxt.textContent = "Status: PAUSED ⏸️";
        } else {
          toggleBtn.textContent = "PAUSE BOT";
          toggleBtn.style.background = "rgba(255,255,255,0.08)";
          statusTxt.textContent = "Status: RUNNING LIVE ▶️";
        }
      }
    }

    if (data.risk_parameters) {
      const rp = data.risk_parameters;
      if (document.getElementById("cfg_hard_sl_pct")) document.getElementById("cfg_hard_sl_pct").value = rp.hard_sl_pct;
      if (document.getElementById("cfg_take_profit_pct")) document.getElementById("cfg_take_profit_pct").value = rp.take_profit_pct;
      if (document.getElementById("cfg_trail_pct")) document.getElementById("cfg_trail_pct").value = rp.trail_pct;
      if (document.getElementById("cfg_max_capital_pct")) document.getElementById("cfg_max_capital_pct").value = rp.max_capital_pct;
    }

  } catch (err) {
    console.debug("Admin status fetch error:", err);
  }
}

async function toggleBotExecution() {
  if (!adminToken) return;
  const action = isBotPaused ? "resume" : "pause";
  try {
    const res = await fetch("/api/admin/bot-toggle", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({action})
    });
    const data = await res.json();
    if (res.ok) {
      alert(data.message);
      fetchAdminStatus();
    }
  } catch (err) {
    alert("Error toggling bot status: " + err);
  }
}

async function saveAdminSettings(e) {
  e.preventDefault();
  if (!adminToken) return;

  const payload = {
    hard_sl_pct: parseFloat(document.getElementById("cfg_hard_sl_pct").value),
    take_profit_pct: parseFloat(document.getElementById("cfg_take_profit_pct").value),
    trail_pct: parseFloat(document.getElementById("cfg_trail_pct").value),
    max_capital_pct: parseFloat(document.getElementById("cfg_max_capital_pct").value)
  };

  try {
    const res = await fetch("/api/admin/update-settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      alert("✅ Risk Parameters Saved & Applied Live!");
    } else {
      alert("Failed to save: " + data.message);
    }
  } catch (err) {
    alert("Error updating settings: " + err);
  }
}

async function panicFlattenAll() {
  if (!confirm("🚨 ARE YOU SURE YOU WANT TO FLATTEN ALL OPEN POSITIONS ON COINSWITCH & DELTA?")) return;
  if (!adminToken) return;

  try {
    const res = await fetch("/api/admin/panic-close-all", {
      method: "POST",
      headers: {"Authorization": `Bearer ${adminToken}`}
    });
    const data = await res.json();
    alert(data.message || "Emergency Panic Flatten Command Dispatched.");
    fetchRealData();
  } catch (err) {
    alert("Panic error: " + err);
  }
}

async function executeManualTrade(e) {
  e.preventDefault();
  if (!adminToken) return;

  const sym = document.getElementById("manual_symbol").value.trim().toUpperCase();
  const ex = document.getElementById("manual_exchange").value;
  const act = document.getElementById("manual_action").value;
  const amt = parseFloat(document.getElementById("manual_amount").value);

  try {
    const res = await fetch("/api/admin/manual-trade", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({symbol: sym, exchange: ex, action: act, amount_usd: amt})
    });
    const data = await res.json();
    if (res.ok) {
      alert("✅ " + (data.message || "Manual trade executed!"));
      fetchRealData();
    } else {
      alert("Execution error: " + data.message);
    }
  } catch (err) {
    alert("Trade request error: " + err);
  }
}

// ── 7. Real-Time 24/7 Background Agents Log Polling ───────────────────────
async function fetchAgentLogs() {
  const consoleEl = document.getElementById("agent-logs-console");
  if (!consoleEl) return;

  try {
    const res = await fetch("/api/agent-logs");
    if (!res.ok) return;
    const data = await res.json();
    if (data.logs && data.logs.length > 0) {
      consoleEl.innerHTML = data.logs.map(logLine => {
        let badgeType = "daemon";
        let badgeText = "DAEMON";

        if (logLine.includes("NVIDIA") || logLine.includes("Nemotron") || logLine.includes("Kumo")) {
          badgeType = "nvidia"; badgeText = "NVIDIA_AI";
        } else if (logLine.includes("Scanner") || logLine.includes("Collector") || logLine.includes("SMC")) {
          badgeType = "scanner"; badgeText = "SCANNER";
        } else if (logLine.includes("Risk") || logLine.includes("Trailing") || logLine.includes("Stop")) {
          badgeType = "risk"; badgeText = "RISK_GUARD";
        } else if (logLine.includes("Filled") || logLine.includes("Executed") || logLine.includes("order")) {
          badgeType = "trade"; badgeText = "EXECUTION";
        }

        return `<div class="log-entry"><span class="log-badge badge-${badgeType}">${badgeText}</span> <span>${escapeHtml(logLine)}</span></div>`;
      }).join("");
      consoleEl.scrollTop = consoleEl.scrollHeight;
    }
  } catch (e) {
    console.debug("Log fetch notice:", e);
  }
}

function escapeHtml(str) {
  return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

setInterval(fetchAgentLogs, 3000);

// ── 8. 3D WebGL Multi-Agent Holographic Neural Sphere Core ────────────────
let scene3d, camera3d, renderer3d, sphereMesh, ringMesh1, ringMesh2, particles3d;



// ── 11. Circuit Board PCB Traces & Electric Pulses Background ──────────────
function initCircuitBgCanvas() {
  const canvas = document.getElementById("circuitBgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  // Generate PCB circuit lines radiating outward
  const lines = [];
  const cx = window.innerWidth / 2;
  const cy = window.innerHeight / 2 - 40;

  for (let a = 0; a < Math.PI * 2; a += Math.PI / 16) {
    const r1 = 180 + Math.random() * 40;
    const r2 = 380 + Math.random() * 120;
    const x1 = cx + Math.cos(a) * r1;
    const y1 = cy + Math.sin(a) * r1;
    const x2 = cx + Math.cos(a) * r2;
    const y2 = cy + Math.sin(a) * r2;
    lines.push({ x1, y1, x2, y2, angle: a, pulsePos: Math.random() });
  }

  function drawCircuits() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    const time = Date.now() * 0.001;

    for (let l of lines) {
      // Draw PCB trace line
      ctx.beginPath();
      ctx.moveTo(l.x1, l.y1);
      // Create stepped 45/90-degree circuit traces
      const midX = (l.x1 + l.x2) / 2;
      ctx.lineTo(midX, l.y1);
      ctx.lineTo(l.x2, l.y2);
      ctx.strokeStyle = "rgba(0, 240, 144, 0.12)";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      // Draw end junction nodes
      ctx.beginPath();
      ctx.arc(l.x2, l.y2, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 212, 255, 0.3)";
      ctx.fill();

      // Draw active traveling light pulse
      l.pulsePos = (l.pulsePos + 0.006) % 1.0;
      const px = l.x1 + (l.x2 - l.x1) * l.pulsePos;
      const py = l.y1 + (l.y2 - l.y1) * l.pulsePos;

      ctx.beginPath();
      ctx.arc(px, py, 2, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 240, 144, 0.85)";
      ctx.shadowColor = "#00f090";
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;
    }
    requestAnimationFrame(drawCircuits);
  }
  drawCircuits();
}


// ── 7. Procedural 3D Wireframe Brain & Neural Synapse Core ──────────────────
function initAgent3dCore() {
  const canvas = document.getElementById("agent3dCanvas");
  const container = document.getElementById("agent3dContainer");
  if (!canvas || !container || typeof THREE === "undefined") return;

  const scene = new THREE.Scene();
  const width = container.clientWidth || 450;
  const height = container.clientHeight || 400;

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 0, 18);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // Brain Group
  const brainGroup = new THREE.Group();
  scene.add(brainGroup);

  // 1. Procedural Cerebral Cortex (Point Cloud & Synapse Network)
  const particleCount = 420;
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  const colorGreen = new THREE.Color(0x00f090);
  const colorCyan = new THREE.Color(0x00d4ff);
  const colorPurple = new THREE.Color(0xa855f7);

  for (let i = 0; i < particleCount; i++) {
    // Generate two brain hemispheres (left & right lobes)
    const hemisphere = i % 2 === 0 ? 1 : -1;
    const u = Math.random() * Math.PI;
    const v = Math.random() * Math.PI * 2;

    // Organic brain lobe deformation equations
    const rx = 3.6 * Math.sin(u) * Math.cos(v) + hemisphere * 0.9;
    const ry = 3.0 * Math.sin(u) * Math.sin(v) + (Math.cos(u * 2) * 0.4);
    const rz = 4.2 * Math.cos(u) + (Math.sin(v * 3) * 0.3);

    positions[i * 3] = rx;
    positions[i * 3 + 1] = ry;
    positions[i * 3 + 2] = rz;

    const lerpC = (i % 3 === 0) ? colorGreen : (i % 3 === 1 ? colorCyan : colorPurple);
    colors[i * 3] = lerpC.r;
    colors[i * 3 + 1] = lerpC.g;
    colors[i * 3 + 2] = lerpC.b;
  }

  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const pMat = new THREE.PointsMaterial({
    size: 0.28,
    vertexColors: true,
    transparent: true,
    opacity: 0.9,
    blending: THREE.AdditiveBlending
  });

  const brainPoints = new THREE.Points(pGeo, pMat);
  brainGroup.add(brainPoints);

  // 2. Synaptic Neural Connections (Lines between nearby vertices)
  const lineMat = new THREE.LineBasicMaterial({
    color: 0x00f090,
    transparent: true,
    opacity: 0.22,
    blending: THREE.AdditiveBlending
  });

  const linePositions = [];
  for (let i = 0; i < particleCount; i += 2) {
    for (let j = i + 1; j < Math.min(i + 12, particleCount); j++) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist < 2.2) {
        linePositions.push(
          positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
          positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
        );
      }
    }
  }

  const lGeo = new THREE.BufferGeometry();
  lGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
  const brainLines = new THREE.LineSegments(lGeo, lineMat);
  brainGroup.add(brainLines);

  // 3. Gyroscopic Holographic Halo Rings
  const ringGeo1 = new THREE.TorusGeometry(6.2, 0.04, 16, 100);
  const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x00f090, wireframe: true, transparent: true, opacity: 0.35 });
  const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
  ring1.rotation.x = Math.PI / 3;
  brainGroup.add(ring1);

  const ringGeo2 = new THREE.TorusGeometry(6.8, 0.04, 16, 100);
  const ringMat2 = new THREE.MeshBasicMaterial({ color: 0xa855f7, wireframe: true, transparent: true, opacity: 0.25 });
  const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
  ring2.rotation.y = Math.PI / 4;
  brainGroup.add(ring2);

  // Mouse interaction
  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 0.4;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 0.4;
  });

  // Animation Loop
  let clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    brainGroup.rotation.y = time * 0.35 + mouseX;
    brainGroup.rotation.x = Math.sin(time * 0.2) * 0.15 + mouseY;

    ring1.rotation.z = time * 0.25;
    ring2.rotation.z = -time * 0.3;

    // Brain pulsating glow effect
    const scale = 1.0 + Math.sin(time * 2.0) * 0.03;
    brainPoints.scale.set(scale, scale, scale);

    renderer.render(scene, camera);
  }
  animate();

  window.addEventListener('resize', () => {
    if (!container) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
    renderer.setSize(w, h);
  });
}


function initNeuralBgCanvas() {
  const canvas = document.getElementById("neuralBgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  resize();
  window.addEventListener("resize", resize);
  const pts = [];
  for (let i = 0; i < 40; i++) {
    pts.push({ x: Math.random() * canvas.width, y: Math.random() * canvas.height, vx: (Math.random()-0.5)*0.3, vy: (Math.random()-0.5)*0.3 });
  }
  function loop() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let p of pts) {
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 1.5, 0, Math.PI*2);
      ctx.fillStyle = "rgba(0, 240, 144, 0.4)";
      ctx.fill();
    }
    requestAnimationFrame(loop);
  }
  loop();
}
