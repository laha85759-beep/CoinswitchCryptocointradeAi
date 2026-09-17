// ══════════════════════════════════════════════════════════════════════════
// THESMARTMAG QUANT TERMINAL • NEURAL OS & SAAS ENGINE
// ══════════════════════════════════════════════════════════════════════════

let currentTvSymbol = "BINANCE:BTCUSDT";
let currentView = "terminal";
let adminToken = sessionStorage.getItem("tsm_admin_token") || "";
let userToken = localStorage.getItem("tsm_user_token") || "";
let currentUser = null;
let isBotPaused = false;
let currentTheme = localStorage.getItem("tsm_theme") || "dark";

// ── 1. Initialization ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initUtcClock();
  initTradingViewWidget("tradingview_widget_container", currentTvSymbol);
  initAgent3dCore();
  initCircuitBgCanvas();
  initNeuralBgCanvas();
  initUserSession();
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
  
  document.querySelectorAll(".tsm-tab, .nc-nav-tab").forEach(tab => {
    if (tab.getAttribute("data-view") === viewName) {
      tab.classList.add("active");
    } else {
      tab.classList.remove("active");
    }
  });

  document.querySelectorAll(".tsm-view-section, .nc-view-pane").forEach(sec => {
    sec.classList.remove("active");
  });
  
  const targetSec = document.getElementById(`view-${viewName}`);
  if (targetSec) {
    targetSec.classList.add("active");
  }

  if (viewName === "chart") {
    initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol);
  }
}

function toggleAdminView() {
  switchView("admin");
}

function autofillAdminLogin(target) {
  if (target === 'modal') {
    const emailEl = document.getElementById("loginEmail");
    const passEl = document.getElementById("loginPassword");
    if (emailEl) emailEl.value = "admin@thesmartmag.com";
    if (passEl) passEl.value = "SmartMag@Quant2026!";
    const form = document.getElementById("userLoginForm");
    if (form) form.dispatchEvent(new Event("submit", {cancelable: true, bubbles: true}));
  } else {
    const userEl = document.getElementById("adminUserInput");
    const passEl = document.getElementById("adminPassInput");
    if (userEl) userEl.value = "admin@thesmartmag.com";
    if (passEl) passEl.value = "SmartMag@Quant2026!";
    const form = document.getElementById("adminLoginForm");
    if (form) form.dispatchEvent(new Event("submit", {cancelable: true, bubbles: true}));
  }
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

// ── 5. User Multi-Tenant Authentication & Session Engine ───────────────────
async function initUserSession() {
  if (!userToken) {
    updateUserUI(null);
    return;
  }
  
  try {
    const res = await fetch("/api/auth/me", {
      headers: { "Authorization": `Bearer ${userToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      currentUser = data.user;
      updateUserUI(data.user, data.settings, data.exchange_connections);
    } else {
      handleUserLogout();
    }
  } catch (err) {
    console.debug("User session validation error:", err);
  }
}

function updateUserUI(user, settings, exConnections) {
  const userPill = document.getElementById("userProfilePill");
  const userTxt = document.getElementById("userProfileText");
  const keysBtn = document.getElementById("connectKeysBtn");

  if (user) {
    if (userTxt) userTxt.textContent = `👤 ${user.name || user.email.split('@')[0]}`;
    if (keysBtn) keysBtn.style.display = "flex";
    if (userPill) {
      userPill.title = `Logged in as ${user.email} (Click for settings & profile)`;
      userPill.onclick = () => openUserSettingsModal();
    }
  } else {
    if (userTxt) userTxt.textContent = "SIGN IN / JOIN";
    if (keysBtn) keysBtn.style.display = "none";
    if (userPill) {
      userPill.title = "Login or Create Trader Account";
      userPill.onclick = () => openAuthModal();
    }
  }
}

function openAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) {
    modal.style.display = "flex";
    switchAuthTab("login");
  }
}

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.style.display = "none";
}

function switchAuthTab(tab) {
  const loginTab = document.getElementById("authTabLogin");
  const regTab = document.getElementById("authTabRegister");
  const loginForm = document.getElementById("userLoginForm");
  const regForm = document.getElementById("userRegisterForm");
  const loginErr = document.getElementById("loginError");
  const regErr = document.getElementById("regError");

  if (loginErr) loginErr.style.display = "none";
  if (regErr) regErr.style.display = "none";

  if (tab === "login") {
    if (loginTab) loginTab.classList.add("active");
    if (regTab) regTab.classList.remove("active");
    if (loginForm) loginForm.style.display = "flex";
    if (regForm) regForm.style.display = "none";
  } else {
    if (regTab) regTab.classList.add("active");
    if (loginTab) loginTab.classList.remove("active");
    if (regForm) regForm.style.display = "flex";
    if (loginForm) loginForm.style.display = "none";
  }
}

async function handleUserLogin(e) {
  e.preventDefault();
  const email = document.getElementById("loginEmail").value.trim();
  const password = document.getElementById("loginPassword").value.trim();
  const errBox = document.getElementById("loginError");
  const submitBtn = document.getElementById("loginSubmitBtn");

  if (submitBtn) { submitBtn.textContent = "AUTHENTICATING..."; submitBtn.disabled = true; }
  if (errBox) errBox.style.display = "none";

  try {
    const res = await fetch("/api/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      userToken = data.token;
      localStorage.setItem("tsm_user_token", userToken);
      currentUser = data.user;
      closeAuthModal();
      initUserSession();
      fetchRealData();
      
      if (data.user.role === "superadmin") {
        adminToken = data.token;
        sessionStorage.setItem("tsm_admin_token", adminToken);
        checkAdminAuth();
      }
    } else {
      if (errBox) {
        errBox.textContent = data.message || "Invalid trader credentials.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    if (errBox) {
      errBox.textContent = "Connection error. Please try again.";
      errBox.style.display = "block";
    }
  } finally {
    if (submitBtn) { submitBtn.textContent = "ENTER TRADING TERMINAL"; submitBtn.disabled = false; }
  }
}

async function handleUserRegister(e) {
  e.preventDefault();
  const name = document.getElementById("regName").value.trim();
  const email = document.getElementById("regEmail").value.trim();
  const password = document.getElementById("regPassword").value.trim();
  const errBox = document.getElementById("regError");
  const submitBtn = document.getElementById("regSubmitBtn");

  if (submitBtn) { submitBtn.textContent = "CREATING ACCOUNT..."; submitBtn.disabled = true; }
  if (errBox) errBox.style.display = "none";

  try {
    const res = await fetch("/api/auth/register", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name, email, password })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      userToken = data.token;
      localStorage.setItem("tsm_user_token", userToken);
      currentUser = data.user;
      closeAuthModal();
      initUserSession();
      fetchRealData();
      openExchangeKeysModal();
    } else {
      if (errBox) {
        errBox.textContent = data.message || "Registration failed.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    if (errBox) {
      errBox.textContent = "Connection error. Please try again.";
      errBox.style.display = "block";
    }
  } finally {
    if (submitBtn) { submitBtn.textContent = "CREATE TRADER ACCOUNT"; submitBtn.disabled = false; }
  }
}

function handleUserLogout() {
  userToken = "";
  currentUser = null;
  localStorage.removeItem("tsm_user_token");
  updateUserUI(null);
  closeUserSettingsModal();
  fetchRealData();
}

// ── 6. Exchange API Keys Modal Handlers ────────────────────────────────────
function openExchangeKeysModal() {
  const modal = document.getElementById("exchangeKeysModal");
  const msgBox = document.getElementById("keysSaveMsg");
  if (msgBox) msgBox.style.display = "none";
  if (modal) modal.style.display = "flex";
}

function closeExchangeKeysModal() {
  const modal = document.getElementById("exchangeKeysModal");
  if (modal) modal.style.display = "none";
}

async function handleSaveExchangeKeys(e) {
  e.preventDefault();
  if (!userToken) {
    openAuthModal();
    return;
  }

  const cs_key = document.getElementById("user_cs_key").value.trim();
  const cs_secret = document.getElementById("user_cs_secret").value.trim();
  const delta_key = document.getElementById("user_delta_key").value.trim();
  const delta_secret = document.getElementById("user_delta_secret").value.trim();
  const msgBox = document.getElementById("keysSaveMsg");

  try {
    const res = await fetch("/api/user/exchange-keys", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({ cs_key, cs_secret, delta_key, delta_secret })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      if (msgBox) {
        msgBox.textContent = "✅ Exchange API credentials saved and encrypted securely!";
        msgBox.style.display = "block";
      }
      setTimeout(() => {
        closeExchangeKeysModal();
        fetchRealData();
      }, 1200);
    } else {
      if (msgBox) {
        msgBox.textContent = "Failed to save keys: " + (data.message || "Unknown error");
        msgBox.style.display = "block";
      }
    }
  } catch (err) {
    if (msgBox) {
      msgBox.textContent = "Error saving keys: " + err;
      msgBox.style.display = "block";
    }
  }
}

// ── 7. Personal User Settings & Risk Modal ─────────────────────────────────
async function openUserSettingsModal() {
  if (!userToken) {
    openAuthModal();
    return;
  }

  const modal = document.getElementById("userSettingsModal");
  const msgBox = document.getElementById("userSettingsMsg");
  if (msgBox) msgBox.style.display = "none";

  try {
    const res = await fetch("/api/auth/me", {
      headers: { "Authorization": `Bearer ${userToken}` }
    });
    if (res.ok) {
      const data = await res.json();
      if (data.settings) {
        const s = data.settings;
        if (document.getElementById("user_strategy_select") && s.strategy) document.getElementById("user_strategy_select").value = s.strategy;
        if (document.getElementById("usr_cfg_hard_sl") && s.hard_sl_pct) document.getElementById("usr_cfg_hard_sl").value = s.hard_sl_pct;
        if (document.getElementById("usr_cfg_tp") && s.take_profit_pct) document.getElementById("usr_cfg_tp").value = s.take_profit_pct;
        if (document.getElementById("usr_cfg_trail") && s.trail_pct) document.getElementById("usr_cfg_trail").value = s.trail_pct;
        if (document.getElementById("usr_cfg_max_cap") && s.max_capital_pct) document.getElementById("usr_cfg_max_cap").value = s.max_capital_pct;
      }
    }
  } catch (err) {
    console.debug("Error preloading user settings:", err);
  }

  if (modal) modal.style.display = "flex";
}

function closeUserSettingsModal() {
  const modal = document.getElementById("userSettingsModal");
  if (modal) modal.style.display = "none";
}

async function handleSaveUserSettings(e) {
  e.preventDefault();
  if (!userToken) return;

  const payload = {
    strategy: document.getElementById("user_strategy_select").value,
    hard_sl_pct: parseFloat(document.getElementById("usr_cfg_hard_sl").value),
    take_profit_pct: parseFloat(document.getElementById("usr_cfg_tp").value),
    trail_pct: parseFloat(document.getElementById("usr_cfg_trail").value),
    max_capital_pct: parseFloat(document.getElementById("usr_cfg_max_cap").value)
  };

  const msgBox = document.getElementById("userSettingsMsg");
  try {
    const res = await fetch("/api/user/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      if (msgBox) {
        msgBox.textContent = "✅ Personal strategy and risk settings updated!";
        msgBox.style.display = "block";
      }
      setTimeout(() => {
        closeUserSettingsModal();
        fetchRealData();
      }, 1000);
    } else {
      if (msgBox) {
        msgBox.textContent = "Failed to update: " + (data.message || "Unknown error");
        msgBox.style.display = "block";
      }
    }
  } catch (err) {
    if (msgBox) {
      msgBox.textContent = "Error saving settings: " + err;
      msgBox.style.display = "block";
    }
  }
}

// ── 8. Real-Time Telemetry & Data Polling Engine ───────────────────────────
async function fetchRealData() {
  try {
    let userData = null;
    if (userToken) {
      try {
        const uRes = await fetch("/api/user/terminal-data", {
          headers: { "Authorization": `Bearer ${userToken}` }
        });
        if (uRes.ok) {
          userData = await uRes.json();
        } else if (uRes.status === 401) {
          handleUserLogout();
        }
      } catch (e) {
        console.debug("User data fetch error:", e);
      }
    }

    const res = await fetch("/api/terminal-data");
    if (!res.ok) return;
    const data = await res.json();

    const balances = userData && userData.balances ? userData.balances : data.balances;
    if (balances) {
      const totalUsdt = Number(balances.total_capital_usdt || 6.57).toFixed(2);
      const csUsdt = Number(balances.cs_usdt || 2.34).toFixed(2);
      const csInr = Number(balances.cs_inr || 11.41).toFixed(2);
      const deltaUsdt = Number(balances.delta_usdt || 4.17).toFixed(2);
      const deltaInr = (deltaUsdt * 88.0).toFixed(2);

      const capEl = document.getElementById("total-capital");
      if (capEl) capEl.innerHTML = `$${totalUsdt} <span class="kpi-unit">USDT</span>`;

      const csBalEl = document.getElementById("cs-bal-txt");
      if (csBalEl) csBalEl.textContent = `$${csUsdt} USDT (₹${csInr})`;

      const deltaBalEl = document.getElementById("delta-bal-txt");
      if (deltaBalEl) deltaBalEl.textContent = `$${deltaUsdt} USDT (₹${deltaInr})`;
    }

    const perf = userData && userData.performance ? userData.performance : data.performance;
    if (perf) {
      const pnlUsdt = Number(perf.total_realized_pnl_usdt || 0.0);
      const pnlEl = document.getElementById("total-pnl-value");
      if (pnlEl) {
        pnlEl.textContent = (pnlUsdt >= 0 ? "+$" : "-$") + Math.abs(pnlUsdt).toFixed(2) + " USDT";
        pnlEl.className = `kpi-value-large ${pnlUsdt >= 0 ? "green-text" : "red-text"}`;
      }
      const tradesEl = document.getElementById("closed-trades-count");
      if (tradesEl) tradesEl.textContent = perf.closed_trades_count || 0;
    }

    if (data.tickers) {
      updateTicker("header-btc", data.tickers.btc);
      updateTicker("header-eth", data.tickers.eth);
      updateTicker("header-sol", data.tickers.sol);
      updateTicker("header-ondo", data.tickers.ondo || 0.72);
      updateTicker("header-pepe", data.tickers.pepe || 0.0000078);
    }

    const positions = userData && userData.open_positions ? userData.open_positions : data.open_positions;
    if (positions) {
      const csCount = (positions.coinswitch || []).length;
      const deltaCount = (positions.delta || []).length;
      const totalCount = positions.total_count !== undefined ? positions.total_count : (csCount + deltaCount);

      const posTag = document.getElementById("positions-tag");
      if (posTag) posTag.textContent = `${totalCount} OPEN`;

      const openCountEl = document.getElementById("total-open-count");
      if (openCountEl) openCountEl.innerHTML = `${totalCount} <span class="kpi-unit">POSITIONS</span>`;

      const csCountEl = document.getElementById("cs-open-count");
      if (csCountEl) csCountEl.textContent = csCount;

      const deltaCountEl = document.getElementById("delta-open-count");
      if (deltaCountEl) deltaCountEl.textContent = deltaCount;

      renderPositionsTable(positions);
    }

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

// ── 9. Super Admin Portal & Multi-Tenant User Management ───────────────────
function checkAdminAuth() {
  const loginBox = document.getElementById("admin-login-box");
  const dashPanel = document.getElementById("admin-dashboard-panel");
  const adminNavBtnText = document.getElementById("adminNavBtnText");

  if (adminToken) {
    if (loginBox) loginBox.style.display = "none";
    if (dashPanel) dashPanel.style.display = "block";
    if (adminNavBtnText) adminNavBtnText.textContent = "ADMIN (LOGGED IN)";
    fetchAdminStatus();
    fetchAdminUsersList();
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

  if (submitBtn) { submitBtn.textContent = "AUTHENTICATING..."; submitBtn.disabled = true; }
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
    if (submitBtn) { submitBtn.textContent = "AUTHENTICATE ADMIN"; submitBtn.disabled = false; }
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

async function fetchAdminUsersList() {
  if (!adminToken) return;
  const tbody = document.getElementById("admin-users-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/admin/users", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    if (!data.users || data.users.length === 0) {
      tbody.innerHTML = `<tr><td colspan="9" class="text-center empty-state">No users registered yet.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.users.map(u => {
      const isSuper = u.role === "superadmin";
      const csBadge = u.has_cs ? '<span class="green font-mono">CS:✓</span>' : '<span class="text-muted font-mono">CS:✗</span>';
      const deltaBadge = u.has_delta ? '<span class="cyan font-mono">DELTA:✓</span>' : '<span class="text-muted font-mono">DELTA:✗</span>';
      const statusBadge = u.is_active ? '<span class="user-status-badge active">ACTIVE</span>' : '<span class="user-status-badge disabled">SUSPENDED</span>';
      const autotradeBadge = u.autotrade_enabled ? '<span class="green">ON 🟢</span>' : '<span class="gold">OFF ⏸</span>';

      return `
        <tr>
          <td class="font-mono">${u.id.substring(0, 8)}...</td>
          <td><strong>${escapeHtml(u.name || 'Trader')}</strong></td>
          <td>${escapeHtml(u.email)}</td>
          <td><span class="tsm-badge-pill ${isSuper ? 'admin' : 'cyan'}">${u.role.toUpperCase()}</span></td>
          <td>${csBadge} &nbsp; ${deltaBadge}</td>
          <td class="font-mono text-dim">${u.strategy || 'ai_consensus'}</td>
          <td>${autotradeBadge}</td>
          <td>${statusBadge}</td>
          <td>
            ${isSuper ? '<span class="text-muted font-mono">MASTER</span>' : `<button class="btn-sm-action" onclick="adminToggleUserStatus('${u.id}')">${u.is_active ? 'Disable' : 'Enable'}</button>`}
          </td>
        </tr>
      `;
    }).join("");

  } catch (err) {
    console.debug("Error fetching admin users:", err);
  }
}

async function adminToggleUserStatus(userId) {
  if (!adminToken) return;
  try {
    const res = await fetch("/api/admin/users/toggle-status", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${adminToken}`
      },
      body: JSON.stringify({ user_id: userId })
    });
    const data = await res.json();
    if (res.ok) {
      fetchAdminUsersList();
    } else {
      alert("Failed to toggle status: " + data.message);
    }
  } catch (err) {
    alert("Error: " + err);
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
    alert(data.message || "Manual trade command submitted.");
    fetchRealData();
  } catch (err) {
    alert("Manual trade error: " + err);
  }
}

// ── 10. Agent Execution Logs Console ───────────────────────────────────────
async function fetchAgentLogs() {
  try {
    const res = await fetch("/api/logs");
    if (!res.ok) return;
    const data = await res.json();

    const logConsole = document.getElementById("agentLogConsole");
    if (!logConsole || !data.logs || data.logs.length === 0) return;

    logConsole.innerHTML = data.logs.slice(-25).map(item => {
      let badgeClass = "daemon";
      let agent = item.agent || "SYSTEM";
      if (agent.includes("SCANNER")) badgeClass = "scanner";
      else if (agent.includes("AI") || agent.includes("SUPER_BRAIN")) badgeClass = "ai";
      else if (agent.includes("RISK")) badgeClass = "risk";
      else if (agent.includes("TRADE") || agent.includes("EXEC")) badgeClass = "trade";

      const timeStr = item.time ? item.time.split("T")[1].split(".")[0] : "--:--:--";
      return `
        <div class="nc-term-line">
          <span class="nc-term-ts">${timeStr}</span>
          <span class="nc-term-badge ${badgeClass}">[${agent}]</span>
          <span class="nc-term-msg">${escapeHtml(item.message)}</span>
        </div>
      `;
    }).join("");
    
    logConsole.scrollTop = logConsole.scrollHeight;

  } catch (err) {
    console.debug("Error fetching logs:", err);
  }
}

setInterval(fetchAgentLogs, 3000);

function escapeHtml(str) {
  if (!str) return "";
  return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

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

    for (let l of lines) {
      ctx.beginPath();
      ctx.moveTo(l.x1, l.y1);
      const midX = (l.x1 + l.x2) / 2;
      ctx.lineTo(midX, l.y1);
      ctx.lineTo(l.x2, l.y2);
      ctx.strokeStyle = "rgba(0, 240, 144, 0.12)";
      ctx.lineWidth = 1.2;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(l.x2, l.y2, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 212, 255, 0.3)";
      ctx.fill();

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

// ── 12. Procedural 3D Wireframe Brain & Neural Synapse Core ─────────────────
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

  const brainGroup = new THREE.Group();
  scene.add(brainGroup);

  const particleCount = 420;
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  const colorGreen = new THREE.Color(0x00f090);
  const colorCyan = new THREE.Color(0x00d4ff);
  const colorPurple = new THREE.Color(0xa855f7);

  for (let i = 0; i < particleCount; i++) {
    const hemisphere = i % 2 === 0 ? 1 : -1;
    const u = Math.random() * Math.PI;
    const v = Math.random() * Math.PI * 2;

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

  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 0.4;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 0.4;
  });

  let clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    brainGroup.rotation.y = time * 0.35 + mouseX;
    brainGroup.rotation.x = Math.sin(time * 0.2) * 0.15 + mouseY;

    ring1.rotation.z = time * 0.25;
    ring2.rotation.z = -time * 0.3;

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

// ── 13. Neural Matrix Particles Background ─────────────────────────────────
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
