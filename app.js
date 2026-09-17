// ══════════════════════════════════════════════════════════════════════════
// THESMARTMAG QUANT TERMINAL • NEURAL OS & SAAS ENGINE
// ══════════════════════════════════════════════════════════════════════════

let currentTvSymbol = "BINANCE:BTCUSDT";
let currentView = "terminal";
let adminToken = sessionStorage.getItem("tsm_admin_token") || "";
let userToken = localStorage.getItem("tsm_user_token") || "";
let currentUser = null;
let isBotPaused = false;
let currentTheme = "dark";
localStorage.setItem("tsm_theme", "dark");

// ── 1. Initialization ─────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.body.classList.remove("light-mode");
  localStorage.setItem("tsm_theme", "dark");
  initTheme();
  initUtcClock();
  initTradingViewWidget("tradingview_widget_container", currentTvSymbol);
  initAgent3dCore();
  initCircuitBgCanvas();
  initNeuralBgCanvas();
  initUserSession();
  fetchRealData();
  setInterval(fetchRealData, 4000);
  fetchNewsData();
  setInterval(fetchNewsData, 10000);
  fetchIndianMarketData();
  setInterval(fetchIndianMarketData, 8000);
  checkAdminAuth();
  if (window.location.hash) {
    handleHashRouting();
  }
  window.addEventListener("hashchange", handleHashRouting);
});

// ── 1.1 Theme Switcher (Dark / Light) ──────────────────────────────────────
function initTheme() {
  document.body.classList.remove("light-mode");
  localStorage.setItem("tsm_theme", "dark");
}

function toggleTheme() {
  // Permanently locked to approved 100% Dark Cyberpunk Holographic theme
  document.body.classList.remove("light-mode");
  localStorage.setItem("tsm_theme", "dark");
}

function applyTheme(theme) {
  document.body.classList.remove("light-mode");
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
function handleHashRouting() {
  const hash = window.location.hash.replace("#", "").toLowerCase().trim();
  if (["terminal", "rwa", "partners", "india", "news", "chart", "trades", "admin"].includes(hash)) {
    switchView(hash, false);
  }
}

function switchView(viewName, updateHash = true) {
  currentView = viewName;
  if (updateHash && window.location.hash !== `#${viewName}`) {
    history.replaceState(null, null, `#${viewName}`);
  }
  
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
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  if (viewName === "chart") {
    initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol);
  } else if (viewName === "news") {
    fetchNewsData();
  } else if (viewName === "india") {
    fetchIndianMarketData();
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
  const logoutBtn = document.getElementById("userLogoutBtn");
  const adminNavBtn = document.getElementById("adminNavBtn");
  const superAdminTab = document.getElementById("superAdminNavTab");

  if (user) {
    if (logoutBtn) logoutBtn.style.display = "flex";
  } else {
    if (logoutBtn) logoutBtn.style.display = "none";
  }

  if (user) {
    if (userTxt) userTxt.textContent = `👤 ${user.name || user.email.split('@')[0]}`;
    if (keysBtn) keysBtn.style.display = "flex";
    if (userPill) {
      userPill.title = `Logged in as ${user.email} (Click for settings & profile)`;
      userPill.onclick = () => openUserSettingsModal();
    }

    // STRICT ROLE CHECK: Only reveal Super Admin controls to authenticated superadmin
    if (user.role === "superadmin") {
      if (adminNavBtn) adminNavBtn.style.display = "flex";
      if (superAdminTab) superAdminTab.style.display = "flex";
    } else {
      if (adminNavBtn) adminNavBtn.style.display = "none";
      if (superAdminTab) superAdminTab.style.display = "none";
    }
  } else {
    if (userTxt) userTxt.textContent = "SIGN IN / JOIN";
    if (keysBtn) keysBtn.style.display = "none";
    if (adminNavBtn) adminNavBtn.style.display = "none";
    if (superAdminTab) superAdminTab.style.display = "none";
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
  adminToken = "";
  localStorage.removeItem("tsm_user_token");
  sessionStorage.removeItem("tsm_admin_token");
  updateUserUI(null);
  checkAdminAuth();
  closeUserSettingsModal();
  switchView("terminal");
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
let globalJarvisRenderer = null;
let globalJarvisScene = null;
let globalJarvisCamera = null;
let jarvisAnimationId = null;

function initAgent3dCore() {
  const canvas = document.getElementById("agent3dCanvas");
  const container = document.getElementById("agent3dContainer");
  if (!canvas || !container || typeof THREE === "undefined") return;

  const scene = new THREE.Scene();
  const width = container.clientWidth || 450;
  const height = container.clientHeight || 400;

  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 0, 20);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const mainGroup = new THREE.Group();
  scene.add(mainGroup);

  // 1. Core Synaptic Cloud (540 particles)
  const particleCount = 540;
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);

  const cGreen = new THREE.Color(0x00f090);
  const cCyan = new THREE.Color(0x00d4ff);
  const cGold = new THREE.Color(0xffd700);

  for (let i = 0; i < particleCount; i++) {
    const hemisphere = i % 2 === 0 ? 1 : -1;
    const u = Math.random() * Math.PI;
    const v = Math.random() * Math.PI * 2;

    const rx = 3.8 * Math.sin(u) * Math.cos(v) + hemisphere * 0.9;
    const ry = 3.2 * Math.sin(u) * Math.sin(v) + (Math.cos(u * 2) * 0.45);
    const rz = 4.4 * Math.cos(u) + (Math.sin(v * 3) * 0.35);

    positions[i * 3] = rx;
    positions[i * 3 + 1] = ry;
    positions[i * 3 + 2] = rz;

    const col = (i % 3 === 0) ? cGreen : (i % 3 === 1 ? cCyan : cGold);
    colors[i * 3] = col.r;
    colors[i * 3 + 1] = col.g;
    colors[i * 3 + 2] = col.b;
  }

  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(colors, 3));

  const pMat = new THREE.PointsMaterial({
    size: 0.32,
    vertexColors: true,
    transparent: true,
    opacity: 0.95,
    blending: THREE.AdditiveBlending
  });

  const brainPoints = new THREE.Points(pGeo, pMat);
  mainGroup.add(brainPoints);

  // 2. Synaptic Neural Connector Lines
  const linePositions = [];
  for (let i = 0; i < particleCount; i += 2) {
    for (let j = i + 1; j < Math.min(i + 14, particleCount); j++) {
      const dx = positions[i * 3] - positions[j * 3];
      const dy = positions[i * 3 + 1] - positions[j * 3 + 1];
      const dz = positions[i * 3 + 2] - positions[j * 3 + 2];
      const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
      if (dist < 2.3) {
        linePositions.push(
          positions[i * 3], positions[i * 3 + 1], positions[i * 3 + 2],
          positions[j * 3], positions[j * 3 + 1], positions[j * 3 + 2]
        );
      }
    }
  }

  const lGeo = new THREE.BufferGeometry();
  lGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
  const lMat = new THREE.LineBasicMaterial({
    color: 0x00f090,
    transparent: true,
    opacity: 0.25,
    blending: THREE.AdditiveBlending
  });
  const brainLines = new THREE.LineSegments(lGeo, lMat);
  mainGroup.add(brainLines);

  // 3. Multi-Axis Concentric Gyroscopic Rings
  const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x00f090, wireframe: true, transparent: true, opacity: 0.45 });
  const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.35 });
  const ringMat3 = new THREE.MeshBasicMaterial({ color: 0xffd700, wireframe: true, transparent: true, opacity: 0.3 });

  const ring1 = new THREE.Mesh(new THREE.TorusGeometry(6.4, 0.05, 16, 80), ringMat1);
  ring1.rotation.x = Math.PI / 3;
  mainGroup.add(ring1);

  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(7.2, 0.04, 16, 90), ringMat2);
  ring2.rotation.y = Math.PI / 4;
  mainGroup.add(ring2);

  const ring3 = new THREE.Mesh(new THREE.TorusGeometry(8.0, 0.03, 16, 100), ringMat3);
  ring3.rotation.z = Math.PI / 6;
  mainGroup.add(ring3);

  // 4. Orbiting 3D Trade & Asset Nodes (BTC, Gold, Nifty, ETH, SOL, Sensex)
  const nodeAssets = [
    { label: "BTC", color: 0xf7931a, radius: 9.0, speed: 0.4, angle: 0 },
    { label: "GOLD", color: 0xffd700, radius: 9.5, speed: 0.32, angle: 1.2 },
    { label: "NIFTY", color: 0x00f090, radius: 8.8, speed: 0.45, angle: 2.4 },
    { label: "ETH", color: 0x627eea, radius: 9.2, speed: 0.38, angle: 3.6 },
    { label: "SOL", color: 0x14f195, radius: 9.6, speed: 0.5, angle: 4.8 },
    { label: "SENSEX", color: 0x00d4ff, radius: 8.5, speed: 0.35, angle: 5.8 }
  ];

  const nodeMeshes = [];
  nodeAssets.forEach(asset => {
    const nodeGeo = new THREE.SphereGeometry(0.45, 16, 16);
    const nodeMat = new THREE.MeshBasicMaterial({ color: asset.color, wireframe: true });
    const mesh = new THREE.Mesh(nodeGeo, nodeMat);
    mainGroup.add(mesh);
    nodeMeshes.push({ mesh, asset });
  });

  // 5. Procedural Lightning Arcs
  const sparkGeo = new THREE.BufferGeometry();
  const sparkCount = 24;
  const sparkPositions = new Float32Array(sparkCount * 3);
  sparkGeo.setAttribute('position', new THREE.BufferAttribute(sparkPositions, 3));
  const sparkMat = new THREE.LineBasicMaterial({
    color: 0x00d4ff,
    transparent: true,
    opacity: 0.8,
    blending: THREE.AdditiveBlending
  });
  const sparkLine = new THREE.Line(sparkGeo, sparkMat);
  mainGroup.add(sparkLine);

  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 0.4;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 0.4;
  });

  const clock = new THREE.Clock();
  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    mainGroup.rotation.y = time * 0.25 + mouseX;
    mainGroup.rotation.x = Math.sin(time * 0.15) * 0.15 + mouseY;

    ring1.rotation.z = time * 0.3;
    ring2.rotation.x = -time * 0.25;
    ring3.rotation.y = time * 0.2;

    // Organic double-pulse heartbeat
    const heart = Math.pow(Math.sin(time * 3.4), 8) * 0.08 + Math.pow(Math.sin(time * 3.4 + 0.3), 8) * 0.04;
    const scale = 1.0 + heart;
    brainPoints.scale.set(scale, scale, scale);
    brainLines.scale.set(scale, scale, scale);

    // Update orbiting trade nodes
    nodeMeshes.forEach(n => {
      const a = n.asset;
      const curAngle = a.angle + time * a.speed;
      n.mesh.position.x = Math.cos(curAngle) * a.radius;
      n.mesh.position.z = Math.sin(curAngle) * a.radius;
      n.mesh.position.y = Math.sin(curAngle * 2.0) * 2.0;
      n.mesh.rotation.y = time * 2.0;
    });

    // Lightning discharge spark effect
    if (Math.random() < 0.25) {
      const pArr = sparkLine.geometry.attributes.position.array;
      let startX = (Math.random() - 0.5) * 4.0;
      let startY = (Math.random() - 0.5) * 4.0;
      let startZ = (Math.random() - 0.5) * 4.0;
      for (let k = 0; k < sparkCount; k++) {
        pArr[k * 3] = startX + (Math.random() - 0.5) * 1.2;
        pArr[k * 3 + 1] = startY + (Math.random() - 0.5) * 1.2;
        pArr[k * 3 + 2] = startZ + (Math.random() - 0.5) * 1.2;
        startX = pArr[k * 3];
        startY = pArr[k * 3 + 1];
        startZ = pArr[k * 3 + 2];
      }
      sparkLine.geometry.attributes.position.needsUpdate = true;
      sparkMat.opacity = 0.9;
    } else {
      sparkMat.opacity *= 0.85;
    }

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

// ── 12b. Fullscreen Holographic Jarvis 3D Core Engine ────────────────────────
function openJarvisModal() {
  const modal = document.getElementById("jarvisModal");
  if (!modal) return;
  modal.style.display = "flex";
  initJarvis3dCore();
}

function closeJarvisModal() {
  const modal = document.getElementById("jarvisModal");
  if (modal) modal.style.display = "none";
  if (jarvisAnimationId) cancelAnimationFrame(jarvisAnimationId);
}

function initJarvis3dCore() {
  const canvas = document.getElementById("jarvis3dCanvas");
  if (!canvas || typeof THREE === "undefined") return;

  const width = canvas.parentElement.clientWidth || 700;
  const height = canvas.parentElement.clientHeight || 500;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(0, 0, 24);

  const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const jarvisGroup = new THREE.Group();
  scene.add(jarvisGroup);

  // Dense Jarvis Hologram Sphere (800 points)
  const count = 800;
  const pos = new Float32Array(count * 3);
  const cols = new Float32Array(count * 3);

  for (let i = 0; i < count; i++) {
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos(2 * Math.random() - 1);
    const r = 6.8 + (Math.random() - 0.5) * 1.2;

    pos[i * 3] = r * Math.sin(phi) * Math.cos(theta);
    pos[i * 3 + 1] = r * Math.sin(phi) * Math.sin(theta);
    pos[i * 3 + 2] = r * Math.cos(phi);

    cols[i * 3] = 0.0;
    cols[i * 3 + 1] = 0.85 + Math.random() * 0.15;
    cols[i * 3 + 2] = 0.95 + Math.random() * 0.05;
  }

  const pGeo = new THREE.BufferGeometry();
  pGeo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  pGeo.setAttribute('color', new THREE.BufferAttribute(cols, 3));
  const pMat = new THREE.PointsMaterial({ size: 0.35, vertexColors: true, transparent: true, opacity: 0.9, blending: THREE.AdditiveBlending });
  const points = new THREE.Points(pGeo, pMat);
  jarvisGroup.add(points);

  // Triple Hologram Rings
  const r1 = new THREE.Mesh(new THREE.TorusGeometry(8.5, 0.05, 16, 120), new THREE.MeshBasicMaterial({ color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.4 }));
  r1.rotation.x = Math.PI / 2.5;
  jarvisGroup.add(r1);

  const r2 = new THREE.Mesh(new THREE.TorusGeometry(9.8, 0.05, 16, 120), new THREE.MeshBasicMaterial({ color: 0x00f090, wireframe: true, transparent: true, opacity: 0.35 }));
  r2.rotation.y = Math.PI / 3;
  jarvisGroup.add(r2);

  let mouseX = 0, mouseY = 0;
  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX / window.innerWidth - 0.5) * 0.6;
    mouseY = (e.clientY / window.innerHeight - 0.5) * 0.6;
  });

  const clock = new THREE.Clock();
  function jarvisLoop() {
    jarvisAnimationId = requestAnimationFrame(jarvisLoop);
    const t = clock.getElapsedTime();

    jarvisGroup.rotation.y = t * 0.3 + mouseX;
    jarvisGroup.rotation.x = Math.sin(t * 0.2) * 0.2 + mouseY;
    r1.rotation.z = t * 0.4;
    r2.rotation.z = -t * 0.35;

    const scale = 1.0 + Math.sin(t * 3.0) * 0.04;
    points.scale.set(scale, scale, scale);

    renderer.render(scene, camera);
  }
  jarvisLoop();
}

// ── 12c. Enterprise Admin Sub-Navigation Router ─────────────────────────────
function switchAdminSubTab(sectionId, btn) {
  const bar = btn?.parentElement;
  if (bar) {
    bar.querySelectorAll(".admin-tab-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");

  document.querySelectorAll(".admin-sub-section").forEach(sec => sec.classList.remove("active"));
  const target = document.getElementById(`admin-sec-${sectionId}`);
  if (target) target.classList.add("active");

  if (sectionId === 'analytics') {
    renderAdminAnalyticsCurve();
  }
}

function renderAdminAnalyticsCurve() {
  const canvas = document.getElementById("adminEquityCurveCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.parentElement.clientWidth || 800;
  const h = 260;
  canvas.width = w;
  canvas.height = h;

  ctx.clearRect(0, 0, w, h);
  
  // Background Grid Lines
  ctx.strokeStyle = "rgba(0, 240, 144, 0.08)";
  ctx.lineWidth = 1;
  for (let y = 30; y < h; y += 40) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw Smooth Cumulative Profit Curve
  const points = [
    { x: 0, y: h * 0.8 },
    { x: w * 0.15, y: h * 0.72 },
    { x: w * 0.3, y: h * 0.65 },
    { x: w * 0.45, y: h * 0.52 },
    { x: w * 0.6, y: h * 0.42 },
    { x: w * 0.75, y: h * 0.30 },
    { x: w * 0.9, y: h * 0.22 },
    { x: w, y: h * 0.12 }
  ];

  ctx.beginPath();
  ctx.moveTo(points[0].x, points[0].y);
  for (let i = 1; i < points.length; i++) {
    const xc = (points[i].x + points[i - 1].x) / 2;
    const yc = (points[i].y + points[i - 1].y) / 2;
    ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
  }
  ctx.lineTo(points[points.length - 1].x, points[points.length - 1].y);
  ctx.strokeStyle = "#00f090";
  ctx.lineWidth = 3;
  ctx.stroke();

  // Gradient Fill Under Curve
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(0, 240, 144, 0.35)");
  grad.addColorStop(1, "rgba(0, 240, 144, 0.0)");
  ctx.fillStyle = grad;
  ctx.fill();
}

// ── 12d. Trader CRM Profile Modal Controller ────────────────────────────────
function openUserProfileModal(id, name, email, tier, balance) {
  const modal = document.getElementById("userProfileModal");
  if (!modal) return;
  document.getElementById("crm-trader-name").textContent = name;
  document.getElementById("crm-user-title").textContent = name;
  document.getElementById("crm-user-id").textContent = `ID: ${id}`;
  document.getElementById("crm-user-email").textContent = email;
  document.getElementById("crm-user-tier").textContent = tier;
  document.getElementById("crm-user-balance").textContent = `$${Number(balance).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
  
  const initials = name.split(" ").map(n => n[0]).join("").toUpperCase();
  document.getElementById("crm-avatar-box").textContent = initials || "TR";
  
  modal.style.display = "flex";
}

function closeUserProfileModal() {
  const modal = document.getElementById("userProfileModal");
  if (modal) modal.style.display = "none";
}

function switchCrmTab(tabId, btn) {
  const bar = btn?.parentElement;
  if (bar) bar.querySelectorAll(".crm-tab-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");

  document.querySelectorAll(".crm-pane").forEach(p => p.classList.remove("active"));
  const target = document.getElementById(`crm-pane-${tabId}`);
  if (target) target.classList.add("active");
}

// ── 12e. Global Command Palette (Ctrl+K) ────────────────────────────────────
function openCommandPalette() {
  const modal = document.getElementById("commandPaletteModal");
  if (!modal) return;
  modal.style.display = "flex";
  const inp = document.getElementById("paletteInput");
  if (inp) {
    inp.value = "";
    inp.focus();
  }
}

function closeCommandPalette() {
  const modal = document.getElementById("commandPaletteModal");
  if (modal) modal.style.display = "none";
}

function handlePaletteBackdropClick(e) {
  if (e.target.id === "commandPaletteModal") closeCommandPalette();
}

function handlePaletteSearch(e) {
  if (e.key === "Escape") {
    closeCommandPalette();
    return;
  }
  const query = (e.target.value || "").toLowerCase().trim();
  const items = document.querySelectorAll(".palette-item");
  items.forEach(item => {
    const text = item.textContent.toLowerCase();
    if (!query || text.includes(query)) {
      item.style.display = "flex";
    } else {
      item.style.display = "none";
    }
  });
}

function executePaletteCmd(cmd) {
  closeCommandPalette();
  if (cmd === 'view_dashboard') {
    switchView('terminal');
  } else if (cmd === 'view_admin') {
    switchView('admin');
  } else if (cmd === 'open_jarvis') {
    openJarvisModal();
  } else if (cmd === 'pause_all_bots') {
    toggleBotExecution();
  } else if (cmd === 'refresh_data') {
    fetchIndianMarketData(true);
    triggerNewsScan();
  } else if (cmd === 'panic_flatten') {
    panicFlattenAll();
  }
}

// Global Keyboard Shortcut: Ctrl+K / Cmd+K and Esc
window.addEventListener("keydown", (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
    e.preventDefault();
    const pal = document.getElementById("commandPaletteModal");
    if (pal && pal.style.display === "flex") closeCommandPalette();
    else openCommandPalette();
  } else if (e.key === "Escape") {
    closeCommandPalette();
    closeJarvisModal();
    closeUserProfileModal();
  }
});

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


// ── 14. Live News Agent, Economic Calendar & Macro Signal Engine ───────────
let cachedNewsList = [];
let currentNewsFilter = 'all';

async function fetchNewsData() {
  try {
    // 1. Fetch Live News & Sentiment
    const nRes = await fetch("/api/news/live");
    if (nRes.ok) {
      const nData = await nRes.json();
      if (nData.sentiment) {
        const s = nData.sentiment;
        const sentVal = document.getElementById("news-sentiment-val");
        const sentSub = document.getElementById("news-sentiment-sub");
        if (sentVal) {
          sentVal.textContent = `${s.label} ${s.score}%`;
          sentVal.className = `nc-hex-val ${s.score >= 55 ? 'green' : (s.score <= 45 ? 'purple' : 'cyan')}`;
        }
        if (sentSub) {
          sentSub.textContent = `Bullish: ${s.bull_pct}% • Bearish: ${s.bear_pct}%`;
        }
        const previewSent = document.getElementById("preview-news-sentiment");
        if (previewSent) {
          previewSent.textContent = `SENTIMENT: ${s.label} ${s.score}%`;
          previewSent.className = `tsm-badge-pill ${s.score >= 55 ? 'admin' : (s.score <= 45 ? 'gold' : 'cyan')}`;
        }
      }
      if (nData.indian_indices) {
        const ind = nData.indian_indices;
        const nifty = ind["NIFTY 50"];
        const banknifty = ind["BANK NIFTY"];
        const sensex = ind["SENSEX"];
        const usdinr = ind["USD/INR"];
        
        if (nifty && document.getElementById("idx-nifty")) {
          document.getElementById("idx-nifty").textContent = Number(nifty.price).toLocaleString('en-IN');
          const el = document.getElementById("idx-nifty-chg");
          if (el) {
            el.textContent = `${nifty.change_pct > 0 ? '+' : ''}${nifty.change_pct}% ${nifty.change_pct >= 0 ? '🟢' : '🔴'}`;
            el.className = `indian-idx-chg ${nifty.change_pct >= 0 ? 'green' : 'red-text'}`;
          }
        }
        if (banknifty && document.getElementById("idx-banknifty")) {
          document.getElementById("idx-banknifty").textContent = Number(banknifty.price).toLocaleString('en-IN');
          const el = document.getElementById("idx-banknifty-chg");
          if (el) {
            el.textContent = `${banknifty.change_pct > 0 ? '+' : ''}${banknifty.change_pct}% ${banknifty.change_pct >= 0 ? '🟢' : '🔴'}`;
            el.className = `indian-idx-chg ${banknifty.change_pct >= 0 ? 'green' : 'red-text'}`;
          }
        }
        if (sensex && document.getElementById("idx-sensex")) {
          document.getElementById("idx-sensex").textContent = Number(sensex.price).toLocaleString('en-IN');
          const el = document.getElementById("idx-sensex-chg");
          if (el) {
            el.textContent = `${sensex.change_pct > 0 ? '+' : ''}${sensex.change_pct}% ${sensex.change_pct >= 0 ? '🟢' : '🔴'}`;
            el.className = `indian-idx-chg ${sensex.change_pct >= 0 ? 'green' : 'red-text'}`;
          }
        }
        if (usdinr && document.getElementById("idx-usdinr")) {
          document.getElementById("idx-usdinr").textContent = `₹${usdinr.price}`;
          const el = document.getElementById("idx-usdinr-chg");
          if (el) {
            el.textContent = `${usdinr.change_pct > 0 ? '+' : ''}${usdinr.change_pct}% ⚪`;
          }
        }
      }
      if (nData.news && nData.news.length > 0) {
        cachedNewsList = nData.news;
        const countEl = document.getElementById("news-total-count");
        if (countEl) countEl.textContent = `${nData.news.length} WIRES`;
        const previewHeadline = document.getElementById("preview-news-headline");
        if (previewHeadline && nData.news[0]) {
          previewHeadline.innerHTML = `⚡ <span class="cyan">[${escapeHtml(nData.news[0].source || 'Live Wire')}]</span> <strong>${escapeHtml(nData.news[0].title || '')}</strong>`;
        }
        renderNewsFeed();
      }
    }

    // 2. Fetch Economic Calendar
    const cRes = await fetch("/api/news/calendar");
    if (cRes.ok) {
      const cData = await cRes.json();
      const events = cData.events || cData.calendar || [];
      if (events.length > 0) {
        const calCount = document.getElementById("news-cal-count");
        if (calCount) calCount.textContent = `${events.length} EVENTS`;
        renderEconomicCalendar(events);
      }
    }

    // 3. Fetch Macro & Forex Signals
    const sRes = await fetch("/api/news/signals");
    if (sRes.ok) {
      const sData = await sRes.json();
      const sigs = sData.signals || [];
      if (sigs.length > 0) {
        renderMacroSignals(sigs);
      }
    }

  } catch (err) {
    console.debug("News data fetch notice:", err);
  }
}

function filterNewsCategory(cat, btn) {
  currentNewsFilter = cat;
  document.querySelectorAll(".news-filter-btn").forEach(b => b.classList.remove("active"));
  if (btn) btn.classList.add("active");
  renderNewsFeed();
}

function renderNewsFeed() {
  const container = document.getElementById("news-stream-container");
  if (!container || !cachedNewsList || cachedNewsList.length === 0) return;

  let filtered = cachedNewsList;
  if (currentNewsFilter === 'india') {
    filtered = cachedNewsList.filter(n => n.category === 'INDIA' || n.country === 'INDIA' || ['Moneycontrol', 'Economic Times', 'LiveMint', 'Business Standard'].includes(n.source));
  } else if (currentNewsFilter === 'crypto') {
    filtered = cachedNewsList.filter(n => n.category === 'CRYPTO');
  } else if (currentNewsFilter === 'forex') {
    filtered = cachedNewsList.filter(n => n.category !== 'CRYPTO' || (n.affected_assets && n.affected_assets.some(a => ['EUR', 'GBP', 'USD', 'GOLD', 'INR'].includes(a))));
  } else if (currentNewsFilter === 'bullish') {
    filtered = cachedNewsList.filter(n => (n.sentiment || '').includes('BULL'));
  } else if (currentNewsFilter === 'bearish') {
    filtered = cachedNewsList.filter(n => (n.sentiment || '').includes('BEAR'));
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state text-center" style="padding:20px;">No articles match the '${currentNewsFilter}' filter.</div>`;
    return;
  }

  container.innerHTML = filtered.map(item => {
    const sent = (item.sentiment || 'NEUTRAL').toUpperCase();
    let sentBadge = `<span class="news-sentiment-neutral">⚪ NEUTRAL</span>`;
    if (sent.includes('BULL')) sentBadge = `<span class="news-sentiment-bull">🟢 BULLISH</span>`;
    else if (sent.includes('BEAR')) sentBadge = `<span class="news-sentiment-bear">🔴 BEARISH</span>`;

    const impactScore = item.impact_score || 50;

    return `
      <div class="news-item-card">
        <div class="news-item-head">
          <div style="display:flex; gap:6px; align-items:center;">
            <span class="tsm-partner-badge cyan">${escapeHtml(item.source || 'Wire')}</span>
            <span class="tsm-partner-badge gold">${escapeHtml(item.category || 'MARKET')}</span>
            ${sentBadge}
          </div>
          <span class="font-mono" style="font-size:9.5px; color:var(--text-muted);">Impact: <strong class="green">${impactScore}/100</strong></span>
        </div>
        <a href="${item.url || '#'}" target="_blank" class="news-item-title">${escapeHtml(item.title)}</a>
        <p style="font-size:11px; color:var(--text-dim); line-height:1.4;">${escapeHtml(item.summary || '')}</p>
        ${item.ai_takeaway ? `<div class="news-item-ai">🧠 <strong>AI Catalyst Insight:</strong> ${escapeHtml(item.ai_takeaway)}</div>` : ''}
      </div>
    `;
  }).join("");
}

let cachedCalendarEvents = [];
let currentCalFilter = 'all';

function filterCalendarEvents(filterType, btn) {
  currentCalFilter = filterType;
  const parent = btn?.parentElement;
  if (parent) {
    parent.querySelectorAll(".news-filter-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");

  const labelEl = document.getElementById("cal-filter-label");
  if (labelEl) {
    labelEl.textContent = filterType.toUpperCase() + (filterType === 'all' ? ' RELEASES' : ' FILTER');
  }

  renderEconomicCalendar(cachedCalendarEvents);
}

function renderEconomicCalendar(events) {
  const tbody = document.getElementById("economic-calendar-tbody");
  if (!tbody) return;

  if (events && events.length > 0) {
    cachedCalendarEvents = events;
  }

  let list = cachedCalendarEvents || [];

  if (currentCalFilter === 'high') {
    list = list.filter(e => (e.impact || '').toLowerCase() === 'high');
  } else if (currentCalFilter === 'med') {
    list = list.filter(e => ['medium', 'med'].includes((e.impact || '').toLowerCase()));
  } else if (['USD', 'INR', 'EUR', 'GBP', 'JPY', 'AUD', 'CAD', 'CHF'].includes(currentCalFilter)) {
    list = list.filter(e => {
      const c = (e.country || '').toUpperCase();
      const curr = (e.currency || '').toUpperCase();
      return c.includes(currentCalFilter) || curr.includes(currentCalFilter);
    });
  }

  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center empty-state">No economic events match '${currentCalFilter}' filter.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.slice(0, 30).map(ev => {
    const imp = (ev.impact || 'low').toLowerCase();
    let impBadge = `<span class="cal-impact-low">LOW</span>`;
    if (imp === 'high') impBadge = `<span class="cal-impact-high">HIGH 🔴</span>`;
    else if (imp === 'medium' || imp === 'med') impBadge = `<span class="cal-impact-med">MED 🟠</span>`;

    return `
      <tr>
        <td><span class="tsm-badge-pill admin font-mono">${escapeHtml(ev.country || 'ALL')}</span></td>
        <td><strong>${escapeHtml(ev.title)}</strong></td>
        <td>${impBadge}</td>
        <td class="font-mono green"><strong>${escapeHtml(ev.actual || 'N/A')}</strong></td>
        <td class="font-mono text-dim">${escapeHtml(ev.forecast || 'N/A')}</td>
        <td class="font-mono text-muted">${escapeHtml(ev.previous || 'N/A')}</td>
      </tr>
    `;
  }).join("");
}

function renderMacroSignals(signals) {
  const container = document.getElementById("macro-signals-container");
  if (!container || !signals || signals.length === 0) return;

  container.innerHTML = signals.map(s => {
    const isBuy = (s.direction || 'BUY').toUpperCase() === 'BUY';
    const levels = s.levels || {};

    return `
      <div class="macro-sig-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-family:var(--font-orb); font-size:13px; color:var(--text-main);">${escapeHtml(s.symbol)}</strong>
          <span class="tsm-badge-pill ${isBuy ? 'admin' : 'gold'}">${s.direction.toUpperCase()} • ${(s.confidence * 100).toFixed(0)}% CONF</span>
        </div>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:var(--font-mono); font-size:11px; background:rgba(0,0,0,0.3); padding:8px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05);">
          <div>Entry: <strong class="cyan">${escapeHtml(s.entry)}</strong></div>
          <div>Stop Loss: <strong class="red-text">${escapeHtml(s.sl)}</strong></div>
          <div>Target 1: <strong class="green">${escapeHtml(s.tp1)}</strong></div>
          <div>Target 2: <strong class="green">${escapeHtml(s.tp2)}</strong></div>
        </div>

        <p style="font-size:11px; color:var(--text-dim); line-height:1.4;">⚡ <i>${escapeHtml(s.reason)}</i></p>

        <!-- Multi-Level Explanations -->
        <div style="display:flex; flex-direction:column; gap:6px;">
          ${levels.beginner ? `<div class="macro-level-box"><div class="macro-level-title green">🔰 BEGINNER GUIDE</div>${escapeHtml(levels.beginner)}</div>` : ''}
          ${levels.intermediate ? `<div class="macro-level-box"><div class="macro-level-title cyan">📊 TECHNICAL REASONING</div>${escapeHtml(levels.intermediate)}</div>` : ''}
          ${levels.experienced ? `<div class="macro-level-box"><div class="macro-level-title purple">🏛 INSTITUTIONAL ALPHA</div>${escapeHtml(levels.experienced)}</div>` : ''}
        </div>
      </div>
    `;
  }).join("");
}

// ── 12. INDIAN EQUITIES & F&O OPTIONS INTELLIGENCE ENGINE ──────────────────
let cachedIndianStocks = [];
let currentStockFilter = 'all';

async function fetchIndianMarketData(isManual = false) {
  try {
    if (isManual) {
      await fetch("/api/india/trigger-refresh", { method: "POST" });
    }

    const res = await fetch("/api/india/overview");
    if (!res.ok) return;
    const data = await res.json();

    // 1. Update Benchmark Scorecard
    if (data.indices) {
      const idx = data.indices;
      const nifty = idx["NIFTY 50"];
      const bn = idx["BANK NIFTY"];
      const sensex = idx["SENSEX"];
      const vix = idx["INDIA VIX"];
      const usdinr = idx["USD/INR"];

      if (nifty && document.getElementById("in-idx-nifty")) {
        document.getElementById("in-idx-nifty").textContent = Number(nifty.price).toLocaleString('en-IN', { minimumFractionDigits: 2 });
        const el = document.getElementById("in-idx-nifty-chg");
        if (el) {
          el.textContent = `${nifty.change_pct >= 0 ? '+' : ''}${nifty.change_pct}% ${nifty.change_pct >= 0 ? '🟢' : '🔴'}`;
          el.className = `indian-idx-chg ${nifty.change_pct >= 0 ? 'green' : 'red-text'}`;
        }
      }

      if (bn && document.getElementById("in-idx-banknifty")) {
        document.getElementById("in-idx-banknifty").textContent = Number(bn.price).toLocaleString('en-IN', { minimumFractionDigits: 2 });
        const el = document.getElementById("in-idx-banknifty-chg");
        if (el) {
          el.textContent = `${bn.change_pct >= 0 ? '+' : ''}${bn.change_pct}% ${bn.change_pct >= 0 ? '🟢' : '🔴'}`;
          el.className = `indian-idx-chg ${bn.change_pct >= 0 ? 'green' : 'red-text'}`;
        }
      }

      if (sensex && document.getElementById("in-idx-sensex")) {
        document.getElementById("in-idx-sensex").textContent = Number(sensex.price).toLocaleString('en-IN', { minimumFractionDigits: 2 });
        const el = document.getElementById("in-idx-sensex-chg");
        if (el) {
          el.textContent = `${sensex.change_pct >= 0 ? '+' : ''}${sensex.change_pct}% ${sensex.change_pct >= 0 ? '🟢' : '🔴'}`;
          el.className = `indian-idx-chg ${sensex.change_pct >= 0 ? 'green' : 'red-text'}`;
        }
      }

      if (vix && document.getElementById("in-idx-vix")) {
        document.getElementById("in-idx-vix").textContent = Number(vix.price).toFixed(2);
        const el = document.getElementById("in-idx-vix-chg");
        if (el) {
          el.textContent = `${vix.change_pct >= 0 ? '+' : ''}${vix.change_pct}% ⚡`;
          el.className = `indian-idx-chg ${vix.change_pct <= 0 ? 'green' : 'gold'}`;
        }
      }

      if (usdinr && document.getElementById("in-idx-usdinr")) {
        document.getElementById("in-idx-usdinr").textContent = `₹${Number(usdinr.price).toFixed(2)}`;
        const el = document.getElementById("in-idx-usdinr-chg");
        if (el) {
          el.textContent = `${usdinr.change_pct >= 0 ? '+' : ''}${usdinr.change_pct}% ⚪`;
        }
      }
    }

    // 2. Render Intraday Stock Radar
    if (data.stocks && data.stocks.length > 0) {
      cachedIndianStocks = data.stocks;
      renderIndianStockScreener();
    }

    // 3. Render F&O Options Intelligence Matrix
    if (data.options) {
      renderOptionsIntel(data.options);
    }

    // 4. Render Indian Financial News Feed
    if (data.news && data.news.length > 0) {
      renderIndianNewsFeed(data.news);
    }

    if (isManual) {
      alert("✅ Indian Equities & Options Data Refreshed!");
    }
  } catch (err) {
    console.debug("Indian market data fetch notice:", err);
  }
}

function filterIndianStocks(sector, btn) {
  currentStockFilter = sector;
  const parent = btn?.parentElement;
  if (parent) {
    parent.querySelectorAll(".news-filter-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");
  renderIndianStockScreener();
}

function renderIndianStockScreener() {
  const tbody = document.getElementById("india-stocks-tbody");
  if (!tbody) return;

  let list = cachedIndianStocks || [];
  if (currentStockFilter === 'bull') {
    list = list.filter(s => (s.signal || '').includes('BUY'));
  } else if (currentStockFilter === 'bear') {
    list = list.filter(s => (s.signal || '').includes('SELL'));
  } else if (currentStockFilter === 'bank') {
    list = list.filter(s => (s.sector || '').toLowerCase().includes('bank'));
  } else if (currentStockFilter === 'it') {
    list = list.filter(s => (s.sector || '').toLowerCase().includes('it') || (s.sector || '').toLowerCase().includes('tech'));
  }

  if (list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center empty-state">No NSE stocks found for sector filter '${currentStockFilter}'.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(stk => {
    const isBull = (stk.signal || '').includes('BUY');
    const isBear = (stk.signal || '').includes('SELL');
    let sigBadge = `<span class="tsm-badge-pill font-mono">⚪ RANGE</span>`;
    if (isBull) sigBadge = `<span class="tsm-badge-pill admin font-mono">🟢 ${escapeHtml(stk.signal)}</span>`;
    else if (isBear) sigBadge = `<span class="tsm-badge-pill gold font-mono" style="border-color:rgba(255,51,102,0.5); color:#ff3366;">🔴 ${escapeHtml(stk.signal)}</span>`;

    const chgClass = stk.change_pct >= 0 ? 'green' : 'red-text';
    const chgSign = stk.change_pct >= 0 ? '+' : '';

    return `
      <tr>
        <td><strong class="cyan" style="font-family:var(--font-orb);">${escapeHtml(stk.symbol)}</strong></td>
        <td>
          <div style="font-weight:600;">${escapeHtml(stk.name)}</div>
          <div style="font-size:9.5px; color:var(--text-muted);">${escapeHtml(stk.sector)}</div>
        </td>
        <td class="font-mono" style="font-size:13px; font-weight:700;">₹${Number(stk.ltp).toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
        <td class="font-mono ${chgClass}"><strong>${chgSign}${stk.change_pct}%</strong></td>
        <td class="font-mono" style="font-size:10.5px;">
          <span class="green">H: ₹${Number(stk.high).toFixed(1)}</span><br>
          <span class="red-text">L: ₹${Number(stk.low).toFixed(1)}</span>
        </td>
        <td>${sigBadge}</td>
        <td class="font-mono green">₹${Number(stk.target1).toLocaleString('en-IN')}</td>
        <td class="font-mono green">₹${Number(stk.target2).toLocaleString('en-IN')}</td>
        <td class="font-mono red-text">₹${Number(stk.stop_loss).toLocaleString('en-IN')}</td>
      </tr>
    `;
  }).join("");
}

function renderOptionsIntel(options) {
  if (!options) return;

  // NIFTY 50 Options
  const nifty = options.nifty;
  if (nifty) {
    const pcrBadge = document.getElementById("nifty-pcr-badge");
    if (pcrBadge) {
      pcrBadge.textContent = `PCR: ${nifty.pcr} (${nifty.pcr >= 1 ? '🟢 BULLISH' : '🔴 BEARISH'})`;
      pcrBadge.className = `tsm-badge-pill ${nifty.pcr >= 1 ? 'admin' : 'gold'}`;
    }

    if (document.getElementById("nifty-spot-val")) {
      document.getElementById("nifty-spot-val").textContent = `₹${Number(nifty.spot_ltp).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }
    if (document.getElementById("nifty-maxpain-val")) {
      document.getElementById("nifty-maxpain-val").textContent = `₹${nifty.max_pain}`;
    }
    if (document.getElementById("nifty-res-val")) {
      document.getElementById("nifty-res-val").textContent = `₹${nifty.call_resistance_wall}`;
    }
    if (document.getElementById("nifty-sup-val")) {
      document.getElementById("nifty-sup-val").textContent = `₹${nifty.put_support_wall}`;
    }
    if (document.getElementById("nifty-opt-strategy")) {
      document.getElementById("nifty-opt-strategy").innerHTML = `
        <strong>${escapeHtml(nifty.recommended_strategy)}</strong> 
        <div style="font-size:10px; color:var(--text-dim); margin-top:2px;">Sentiment: <span class="${nifty.pcr >= 1 ? 'green' : 'red-text'}">${escapeHtml(nifty.pcr_bias || '')}</span> • India VIX: <span class="cyan">${nifty.india_vix}</span></div>
      `;
    }

    const chainTbody = document.getElementById("nifty-chain-tbody");
    if (chainTbody && nifty.chain) {
      chainTbody.innerHTML = nifty.chain.map(c => `
        <tr style="${c.is_atm ? 'background:rgba(0,240,144,0.08); font-weight:700;' : ''}">
          <td class="font-mono green">₹${Number(c.ce_ltp).toFixed(2)}</td>
          <td class="font-mono text-dim">${Number(c.ce_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono text-center"><strong class="${c.is_atm ? 'cyan' : ''}">${c.strike}${c.is_atm ? ' <span style="font-size:8px; color:var(--neon-green);">(ATM)</span>' : ''}</strong></td>
          <td class="font-mono text-dim">${Number(c.pe_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono red-text">₹${Number(c.pe_ltp).toFixed(2)}</td>
        </tr>
      `).join("");
    }
  }

  // BANK NIFTY Options
  const bn = options.banknifty;
  if (bn) {
    const pcrBadge = document.getElementById("bn-pcr-badge");
    if (pcrBadge) {
      pcrBadge.textContent = `PCR: ${bn.pcr} (${bn.pcr >= 1 ? '🟢 BULLISH' : '🔴 BEARISH'})`;
      pcrBadge.className = `tsm-badge-pill ${bn.pcr >= 1 ? 'admin' : 'gold'}`;
    }

    if (document.getElementById("bn-spot-val")) {
      document.getElementById("bn-spot-val").textContent = `₹${Number(bn.spot_ltp).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }
    if (document.getElementById("bn-maxpain-val")) {
      document.getElementById("bn-maxpain-val").textContent = `₹${bn.max_pain}`;
    }
    if (document.getElementById("bn-res-val")) {
      document.getElementById("bn-res-val").textContent = `₹${bn.call_resistance_wall}`;
    }
    if (document.getElementById("bn-sup-val")) {
      document.getElementById("bn-sup-val").textContent = `₹${bn.put_support_wall}`;
    }
    if (document.getElementById("bn-opt-strategy")) {
      document.getElementById("bn-opt-strategy").innerHTML = `
        <strong>${escapeHtml(bn.recommended_strategy)}</strong>
        <div style="font-size:10px; color:var(--text-dim); margin-top:2px;">Sentiment: <span class="${bn.pcr >= 1 ? 'green' : 'red-text'}">${escapeHtml(bn.pcr_bias || '')}</span></div>
      `;
    }

    const chainTbody = document.getElementById("bn-chain-tbody");
    if (chainTbody && bn.chain) {
      chainTbody.innerHTML = bn.chain.map(c => `
        <tr style="${c.is_atm ? 'background:rgba(0,212,255,0.08); font-weight:700;' : ''}">
          <td class="font-mono green">₹${Number(c.ce_ltp).toFixed(2)}</td>
          <td class="font-mono text-dim">${Number(c.ce_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono text-center"><strong class="${c.is_atm ? 'cyan' : ''}">${c.strike}${c.is_atm ? ' <span style="font-size:8px; color:var(--neon-cyan);">(ATM)</span>' : ''}</strong></td>
          <td class="font-mono text-dim">${Number(c.pe_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono red-text">₹${Number(c.pe_ltp).toFixed(2)}</td>
        </tr>
      `).join("");
    }
  }

  // BSE SENSEX Options
  const sx = options.sensex;
  if (sx) {
    const pcrBadge = document.getElementById("sensex-pcr-badge");
    if (pcrBadge) {
      pcrBadge.textContent = `PCR: ${sx.pcr} (${sx.pcr >= 1 ? '🟢 BULLISH' : '🔴 BEARISH'})`;
      pcrBadge.className = `tsm-badge-pill ${sx.pcr >= 1 ? 'admin' : 'gold'}`;
    }

    if (document.getElementById("sensex-spot-val")) {
      document.getElementById("sensex-spot-val").textContent = `₹${Number(sx.spot_ltp).toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;
    }
    if (document.getElementById("sensex-maxpain-val")) {
      document.getElementById("sensex-maxpain-val").textContent = `₹${sx.max_pain}`;
    }
    if (document.getElementById("sensex-res-val")) {
      document.getElementById("sensex-res-val").textContent = `₹${sx.call_resistance_wall}`;
    }
    if (document.getElementById("sensex-sup-val")) {
      document.getElementById("sensex-sup-val").textContent = `₹${sx.put_support_wall}`;
    }
    if (document.getElementById("sensex-opt-strategy")) {
      document.getElementById("sensex-opt-strategy").innerHTML = `
        <strong>${escapeHtml(sx.recommended_strategy)}</strong>
        <div style="font-size:10px; color:var(--text-dim); margin-top:2px;">Sentiment: <span class="${sx.pcr >= 1 ? 'green' : 'red-text'}">${escapeHtml(sx.pcr_bias || '')}</span></div>
      `;
    }

    const chainTbody = document.getElementById("sensex-chain-tbody");
    if (chainTbody && sx.chain) {
      chainTbody.innerHTML = sx.chain.map(c => `
        <tr style="${c.is_atm ? 'background:rgba(255,215,0,0.08); font-weight:700;' : ''}">
          <td class="font-mono green">₹${Number(c.ce_ltp).toFixed(2)}</td>
          <td class="font-mono text-dim">${Number(c.ce_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono text-center"><strong class="${c.is_atm ? 'gold' : ''}">${c.strike}${c.is_atm ? ' <span style="font-size:8px; color:var(--neon-gold);">(ATM)</span>' : ''}</strong></td>
          <td class="font-mono text-dim">${Number(c.pe_oi).toLocaleString('en-IN')}</td>
          <td class="font-mono red-text">₹${Number(c.pe_ltp).toFixed(2)}</td>
        </tr>
      `).join("");
    }
  }
}

function switchOptionsTab(tab, btn) {
  const parent = btn?.parentElement;
  if (parent) {
    parent.querySelectorAll(".news-filter-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");

  const niftyCard = document.getElementById("opt-panel-nifty");
  const bnCard = document.getElementById("opt-panel-banknifty");
  const sxCard = document.getElementById("opt-panel-sensex");
  const grid = document.getElementById("options-matrix-grid");

  if (tab === 'all') {
    if (niftyCard) niftyCard.classList.remove("hidden");
    if (bnCard) bnCard.classList.remove("hidden");
    if (sxCard) sxCard.classList.remove("hidden");
    if (grid) grid.style.gridTemplateColumns = "repeat(3, 1fr)";
  } else if (tab === 'nifty') {
    if (niftyCard) niftyCard.classList.remove("hidden");
    if (bnCard) bnCard.classList.add("hidden");
    if (sxCard) sxCard.classList.add("hidden");
    if (grid) grid.style.gridTemplateColumns = "1fr";
  } else if (tab === 'banknifty') {
    if (niftyCard) niftyCard.classList.add("hidden");
    if (bnCard) bnCard.classList.remove("hidden");
    if (sxCard) sxCard.classList.add("hidden");
    if (grid) grid.style.gridTemplateColumns = "1fr";
  } else if (tab === 'sensex') {
    if (niftyCard) niftyCard.classList.add("hidden");
    if (bnCard) bnCard.classList.add("hidden");
    if (sxCard) sxCard.classList.remove("hidden");
    if (grid) grid.style.gridTemplateColumns = "1fr";
  }
}

function renderIndianNewsFeed(newsItems) {
  const container = document.getElementById("india-news-container");
  if (!container || !newsItems || newsItems.length === 0) return;

  container.innerHTML = newsItems.map(item => `
    <div class="news-item-card">
      <div class="news-item-head">
        <div style="display:flex; gap:6px; align-items:center;">
          <span class="tsm-partner-badge cyan">${escapeHtml(item.source || 'NSE/BSE Wire')}</span>
          <span class="tsm-partner-badge gold">🇮🇳 INDIA EQUITIES</span>
          <span class="${(item.sentiment || '').includes('BULL') ? 'news-sentiment-bull' : 'news-sentiment-bear'}">${(item.sentiment || 'BULLISH').toUpperCase()}</span>
        </div>
        <span class="font-mono" style="font-size:9.5px; color:var(--text-muted);">Impact: <strong class="green">${item.impact_score || 75}/100</strong></span>
      </div>
      <a href="${item.url || '#'}" target="_blank" class="news-item-title">${escapeHtml(item.title)}</a>
      <p style="font-size:11px; color:var(--text-dim); line-height:1.4;">${escapeHtml(item.summary || '')}</p>
      ${item.ai_takeaway ? `<div class="news-item-ai">🧠 <strong>Market Impact:</strong> ${escapeHtml(item.ai_takeaway)}</div>` : ''}
    </div>
  `).join("");
}

async function triggerNewsScan() {
  try {
    const res = await fetch("/api/news/trigger-scan", { method: "POST" });
    const data = await res.json();
    alert("✅ " + (data.message || "News scan refreshed!"));
    fetchNewsData();
  } catch (err) {
    alert("Scan notice: " + err);
  }
}

async function broadcastNewsToTelegram() {
  try {
    const res = await fetch("/api/news/broadcast-telegram", { method: "POST" });
    const data = await res.json();
    if (res.ok) {
      alert("📢 " + (data.message || "Live News & Indian Market Intel dispatched to Telegram!"));
    } else {
      alert("⚠️ " + (data.message || "Failed to dispatch to Telegram."));
    }
  } catch (err) {
    alert("Broadcast error: " + err);
  }
}
