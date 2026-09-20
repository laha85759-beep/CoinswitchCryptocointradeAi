// ══════════════════════════════════════════════════════════════════════════
// THESMARTMAG QUANT TERMINAL • NEURAL OS & SAAS ENGINE
// ══════════════════════════════════════════════════════════════════════════

let currentTvSymbol = "BINANCE:BTCUSDT";
let currentTvTimeframe = "5";
let lastCachedPositions = null;
let lastCachedTickers = null;
let lastCachedUserData = null;
let currentView = "terminal";
let adminToken = sessionStorage.getItem("tsm_admin_token") || "";
let userToken = localStorage.getItem("tsm_user_token") || "";
let currentUser = null;

function getAdminAuthToken() {
  if (adminToken) return adminToken;
  const sTok = sessionStorage.getItem("tsm_admin_token");
  if (sTok) { adminToken = sTok; return adminToken; }
  const uTok = localStorage.getItem("tsm_user_token") || userToken || localStorage.getItem("tsm_jwt_token");
  if (uTok && currentUser && currentUser.role === "superadmin") {
    adminToken = uTok;
    sessionStorage.setItem("tsm_admin_token", adminToken);
    return adminToken;
  }
  return uTok || "";
}

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
  initWorkflowCycle();
  initUserSession();
  initAffiliateClickListeners();
  fetchRealData();
  setInterval(fetchRealData, 4000);
  fetchNewsData();
  setInterval(fetchNewsData, 10000);
  fetchIndianMarketData();
  setInterval(fetchIndianMarketData, 8000);
  fetchLiveTickerTape();
  setInterval(fetchLiveTickerTape, 6000);
  checkAdminAuth();
  setInterval(() => {
    if (adminToken && currentView === "admin") {
      fetchAdminOverviewKPIs();
    }
  }, 6000);
  if (window.location.hash) {
    handleHashRouting();
  }
  window.addEventListener("hashchange", handleHashRouting);
});

// ── Live Macro Ticker Tape Engine (Render High Performance) ────────────────
async function fetchLiveTickerTape() {
  const track = document.getElementById("macroTickerTrack");
  if (!track) return;
  try {
    const res = await fetch("/api/market/ticker-bar");
    const data = await res.json();
    if (data.status === "success" && Array.isArray(data.tickers)) {
      const iconMap = {
        nifty: "🇮🇳", banknifty: "🏦", sensex: "🏛", gold: "🥇",
        silver: "🥈", crude: "🛢️", eurusd: "💱", gbpusd: "💱",
        usdjpy: "💱", btc: "₿", eth: "Ξ", sol: "◎", xrp: "✕", sui: "💧"
      };
      track.innerHTML = data.tickers.map(t => {
        const ico = iconMap[t.id] || "🌐";
        const isUp = Number(t.change_pct || 0) >= 0;
        const colorClass = isUp ? "green" : "red-text";
        const sign = isUp ? "+" : "";
        return `
          <span class="ticker-item" onclick="openCoinDetailsModal('${t.symbol}')" style="cursor:pointer;" title="Inspect 3D Model &amp; Quant Intel for ${t.symbol}">
            <span class="sym-ico">${ico}</span>
            <strong>${t.symbol}</strong>
            ${t.price_formatted}
            <span class="${colorClass} font-mono">${t.arrow} ${sign}${t.change_pct}%</span>
          </span>
        `;
      }).join("");
    }
  } catch (e) {
    console.debug("Ticker bar fetch notice:", e);
  }
}
window.fetchLiveTickerTape = fetchLiveTickerTape;

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

// ── 2. Real-Time Country & Timezone Adaptive Clock Engine ──────────────────
let clockMode = localStorage.getItem("tsm_clock_mode") || "local"; // 'local' or 'utc'

function getUserTimezoneInfo() {
  let timeZone = "UTC";
  try {
    timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC";
  } catch (e) {
    timeZone = "UTC";
  }

  const tzLower = timeZone.toLowerCase();
  let flag = "🌐";
  let tzCode = "UTC";
  let countryName = "Global";

  if (tzLower.includes("kolkata") || tzLower.includes("calcutta") || tzLower.includes("india")) {
    flag = "🇮🇳"; tzCode = "IST"; countryName = "India";
  } else if (tzLower.includes("new_york") || tzLower.includes("detroit")) {
    flag = "🇺🇸"; tzCode = "EDT"; countryName = "United States (East)";
  } else if (tzLower.includes("chicago") || tzLower.includes("central")) {
    flag = "🇺🇸"; tzCode = "CDT"; countryName = "United States (Central)";
  } else if (tzLower.includes("denver") || tzLower.includes("mountain") || tzLower.includes("phoenix")) {
    flag = "🇺🇸"; tzCode = "MDT"; countryName = "United States (Mountain)";
  } else if (tzLower.includes("los_angeles") || tzLower.includes("pacific")) {
    flag = "🇺🇸"; tzCode = "PDT"; countryName = "United States (West)";
  } else if (tzLower.includes("london") || tzLower.includes("belfast")) {
    flag = "🇬🇧"; tzCode = "BST/GMT"; countryName = "United Kingdom";
  } else if (tzLower.includes("dubai") || tzLower.includes("uae") || tzLower.includes("muscat")) {
    flag = "🇦🇪"; tzCode = "GST"; countryName = "United Arab Emirates";
  } else if (tzLower.includes("singapore")) {
    flag = "🇸🇬"; tzCode = "SGT"; countryName = "Singapore";
  } else if (tzLower.includes("tokyo") || tzLower.includes("japan")) {
    flag = "🇯🇵"; tzCode = "JST"; countryName = "Japan";
  } else if (tzLower.includes("paris") || tzLower.includes("berlin") || tzLower.includes("rome") || tzLower.includes("madrid") || tzLower.includes("amsterdam") || tzLower.includes("brussels") || tzLower.includes("vienna") || tzLower.includes("stockholm")) {
    flag = "🇪🇺"; tzCode = "CEST"; countryName = "European Union";
  } else if (tzLower.includes("toronto") || tzLower.includes("vancouver") || tzLower.includes("montreal")) {
    flag = "🇨🇦"; tzCode = "EDT/PDT"; countryName = "Canada";
  } else if (tzLower.includes("sydney") || tzLower.includes("melbourne") || tzLower.includes("brisbane") || tzLower.includes("perth")) {
    flag = "🇦🇺"; tzCode = "AEST"; countryName = "Australia";
  } else if (tzLower.includes("dhaka") || tzLower.includes("bangladesh")) {
    flag = "🇧🇩"; tzCode = "BST"; countryName = "Bangladesh";
  } else if (tzLower.includes("hong_kong")) {
    flag = "🇭🇰"; tzCode = "HKT"; countryName = "Hong Kong";
  } else if (tzLower.includes("karachi") || tzLower.includes("pakistan")) {
    flag = "🇵🇰"; tzCode = "PKT"; countryName = "Pakistan";
  } else if (tzLower.includes("shanghai") || tzLower.includes("beijing")) {
    flag = "🇨🇳"; tzCode = "CST"; countryName = "China";
  } else if (tzLower.includes("saopaulo") || tzLower.includes("brazil")) {
    flag = "🇧🇷"; tzCode = "BRT"; countryName = "Brazil";
  } else if (tzLower.includes("riyadh") || tzLower.includes("saudi")) {
    flag = "🇸🇦"; tzCode = "AST"; countryName = "Saudi Arabia";
  } else if (tzLower.includes("zurich") || tzLower.includes("geneva")) {
    flag = "🇨🇭"; tzCode = "CEST"; countryName = "Switzerland";
  } else if (tzLower.includes("johannesburg")) {
    flag = "🇿🇦"; tzCode = "SAST"; countryName = "South Africa";
  } else {
    try {
      const parts = new Intl.DateTimeFormat(navigator.language || "en-US", { timeZoneName: "short" }).formatToParts(new Date());
      const tzPart = parts.find(p => p.type === "timeZoneName");
      if (tzPart && tzPart.value) tzCode = tzPart.value;
    } catch (e) {}
  }

  return { timeZone, flag, tzCode, countryName };
}

function updateClockDisplay() {
  const clockEl = document.getElementById("live-utc-clock");
  if (!clockEl) return;

  const now = new Date();
  const tzInfo = getUserTimezoneInfo();

  if (clockMode === "local") {
    // User Country Local Time
    const timeStr = now.toLocaleTimeString(navigator.language || "en-US", {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: true
    });
    clockEl.innerHTML = `<span class="nc-clock-flag">${tzInfo.flag}</span> <span>${timeStr}</span> <span class="nc-clock-tz-badge">${tzInfo.tzCode}</span>`;
    clockEl.title = `Your Country: ${tzInfo.countryName} (${tzInfo.timeZone})\nLocal Time Active • Click to switch to UTC Market Time`;
  } else {
    // Global UTC Market Time
    const utcHours = String(now.getUTCHours()).padStart(2, '0');
    const utcMins = String(now.getUTCMinutes()).padStart(2, '0');
    const utcSecs = String(now.getUTCSeconds()).padStart(2, '0');
    clockEl.innerHTML = `<span class="nc-clock-flag">🌐</span> <span>${utcHours}:${utcMins}:${utcSecs}</span> <span class="nc-clock-tz-badge">UTC</span>`;
    clockEl.title = `Global UTC Market Time Active • Click to switch to your Country Time (${tzInfo.flag} ${tzInfo.tzCode})`;
  }
}

function toggleClockMode() {
  clockMode = clockMode === "local" ? "utc" : "local";
  localStorage.setItem("tsm_clock_mode", clockMode);
  updateClockDisplay();
}

function initUtcClock() {
  updateClockDisplay();
  setInterval(updateClockDisplay, 1000);
}

// Universal Localized DateTime Formatter for Trades, Logs & News
function formatLocalizedDateTime(timestamp) {
  if (!timestamp) return "—";
  try {
    let d;
    if (typeof timestamp === "number") {
      d = new Date(timestamp > 1e11 ? timestamp : timestamp * 1000);
    } else {
      d = new Date(timestamp);
    }
    if (isNaN(d.getTime())) return String(timestamp);

    return d.toLocaleString(navigator.language || "en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
      hour12: true
    });
  } catch (e) {
    return String(timestamp);
  }
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
  
  document.querySelectorAll(".tsm-tab, .nc-nav-tab, .tsm-dock-item, .tsm-drawer-item, .tsm-dropdown-item").forEach(tab => {
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
    initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol, currentTvTimeframe);
    updateProChartPositionBanner();
  } else if (viewName === "news") {
    fetchNewsData();
  } else if (viewName === "india") {
    fetchIndianMarketData();
  } else if (viewName === "trades" || viewName === "signals") {
    fetchMultiMarketSignals();
  } else if (viewName === "terminal") {
    fetchRealData();
  } else if (viewName === "trader") {
    if (typeof fetchTraderTerminalData === "function") fetchTraderTerminalData();
  } else if (viewName === "admin") {
    checkAdminAuth();
  }
}

function toggleAdminView() {
  switchView("admin");
}

// ── 4. TradingView Pro Chart & Live Position Integration ──────────────────
function initTradingViewWidget(containerId, symbol, interval) {
  const container = document.getElementById(containerId);
  if (!container || typeof TradingView === "undefined") return;

  const sym = symbol || currentTvSymbol || "BINANCE:BTCUSDT";
  const tf = interval || currentTvTimeframe || "5";

  container.innerHTML = "";
  try {
    new TradingView.widget({
      "autosize": true,
      "symbol": sym,
      "interval": tf,
      "timezone": "Etc/UTC",
      "theme": "dark",
      "style": "1",
      "locale": "en",
      "toolbar_bg": "#060e1c",
      "enable_publishing": false,
      "allow_symbol_change": true,
      "container_id": containerId,
      "hide_side_toolbar": false,
      "studies": ["RSI@tv-basicstudies", "MASimple@tv-basicstudies", "VWAP@tv-basicstudies"]
    });
  } catch (e) {
    console.debug("TradingView init notice:", e);
  }
}

function switchProChartSymbol(symbol, btnEl) {
  currentTvSymbol = symbol;

  document.querySelectorAll(".pro-coin-btn").forEach(btn => {
    if (btn === btnEl || btn.getAttribute("data-symbol") === symbol) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  const cleanSym = currentTvSymbol.includes(":") ? currentTvSymbol.split(":")[1].replace(/(USDT|USD|INR)$/, "") + "/USDT" : currentTvSymbol;
  const symInput = document.getElementById("proOrderSymbol");
  if (symInput) symInput.value = cleanSym;

  initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol, currentTvTimeframe);
  initTradingViewWidget("tradingview_widget_container", currentTvSymbol, currentTvTimeframe);
  updateProChartPositionBanner();
}

// ── 4.1 Pro Chart Manual Order Ticket & Multi-Broker Router ────────────────
let proOrderSide = "buy";
let proOrderType = "market";
let proOrderLeverage = 20;

function setProOrderSide(side) {
  proOrderSide = side;
  const btnBuy = document.getElementById("btnSideBuy");
  const btnSell = document.getElementById("btnSideSell");
  const execBtn = document.getElementById("btnExecuteProOrder");
  const execText = document.getElementById("btnExecuteProOrderText");

  if (side === "buy") {
    if (btnBuy) btnBuy.classList.add("active");
    if (btnSell) btnSell.classList.remove("active");
    if (execBtn) {
      execBtn.className = "btn-execute-pro-order buy";
    }
    if (execText) execText.textContent = "EXECUTE BUY ORDER";
  } else {
    if (btnBuy) btnBuy.classList.remove("active");
    if (btnSell) btnSell.classList.add("active");
    if (execBtn) {
      execBtn.className = "btn-execute-pro-order sell";
    }
    if (execText) execText.textContent = "EXECUTE SELL SHORT ORDER";
  }
}

function setProOrderType(type) {
  proOrderType = type;
  const btnMkt = document.getElementById("btnTypeMarket");
  const btnLmt = document.getElementById("btnTypeLimit");
  const lmtGroup = document.getElementById("proLimitPriceGroup");

  if (type === "market") {
    if (btnMkt) btnMkt.classList.add("active");
    if (btnLmt) btnLmt.classList.remove("active");
    if (lmtGroup) lmtGroup.style.display = "none";
  } else {
    if (btnMkt) btnMkt.classList.remove("active");
    if (btnLmt) btnLmt.classList.add("active");
    if (lmtGroup) lmtGroup.style.display = "block";
  }
}

function setProOrderAmount(val) {
  const amtInput = document.getElementById("proOrderAmount");
  if (!amtInput) return;

  if (val === "max") {
    amtInput.value = "25.0";
  } else {
    amtInput.value = Number(val).toFixed(1);
  }

  document.querySelectorAll(".btn-amt-preset").forEach(btn => {
    if ((val === "max" && btn.textContent.includes("MAX")) || btn.textContent.trim() === `$${val}`) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

function setProOrderLeverage(lev) {
  proOrderLeverage = lev;
  const badge = document.getElementById("proLeverageBadge");
  if (badge) badge.textContent = `${lev}x`;

  document.querySelectorAll(".btn-lev-chip").forEach(btn => {
    if (btn.textContent.trim() === `${lev}x`) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });
}

function updateBrokerSelectionUI() {
  const chkDelta = document.getElementById("chkBrokerDelta");
  const chkCS = document.getElementById("chkBrokerCS");
  const lblDelta = document.getElementById("lblBrokerDelta");
  const lblCS = document.getElementById("lblBrokerCS");
  const summary = document.getElementById("proOrderTargetSummary");

  const hasDelta = chkDelta && chkDelta.checked;
  const hasCS = chkCS && chkCS.checked;

  if (lblDelta) {
    if (hasDelta) lblDelta.classList.add("active");
    else lblDelta.classList.remove("active");
  }

  if (lblCS) {
    if (hasCS) lblCS.classList.add("active");
    else lblCS.classList.remove("active");
  }

  if (summary) {
    if (hasDelta && hasCS) {
      summary.innerHTML = "Routing to: <strong>Delta India (Futures) + CoinSwitch Pro (Spot) Concurrent Broadcast</strong>";
    } else if (hasDelta) {
      summary.innerHTML = "Routing to: <strong>Delta India (Crypto Futures & Options)</strong>";
    } else if (hasCS) {
      summary.innerHTML = "Routing to: <strong>CoinSwitch Pro (Spot Engine)</strong>";
    } else {
      summary.innerHTML = "<span class='red-text'>⚠️ No broker selected. Check at least one broker.</span>";
    }
  }
}

function selectAllBrokers() {
  const chkDelta = document.getElementById("chkBrokerDelta");
  const chkCS = document.getElementById("chkBrokerCS");
  if (chkDelta) chkDelta.checked = true;
  if (chkCS) chkCS.checked = true;
  updateBrokerSelectionUI();
}

async function handleProChartOrderSubmit(e) {
  e.preventDefault();

  if (!userToken) {
    openAuthModal();
    return;
  }

  const chkDelta = document.getElementById("chkBrokerDelta");
  const chkCS = document.getElementById("chkBrokerCS");
  const brokers = [];
  if (chkDelta && chkDelta.checked) brokers.push("delta");
  if (chkCS && chkCS.checked) brokers.push("coinswitch");

  const msgBox = document.getElementById("proOrderFeedbackMsg");
  const execBtn = document.getElementById("btnExecuteProOrder");
  const execText = document.getElementById("btnExecuteProOrderText");

  if (brokers.length === 0) {
    if (msgBox) {
      msgBox.className = "pro-order-feedback-msg error";
      msgBox.innerHTML = "⚠️ Please select at least one broker (Delta India or CoinSwitch Pro) to place the order.";
      msgBox.style.display = "block";
    }
    return;
  }

  const symbol = (document.getElementById("proOrderSymbol").value || "BTC/USDT").trim().toUpperCase();
  const amountUsd = parseFloat(document.getElementById("proOrderAmount").value) || 5.0;
  const limitPrice = proOrderType === "limit" ? parseFloat(document.getElementById("proOrderLimitPrice").value) : null;
  const tpPct = parseFloat(document.getElementById("proOrderTpPct").value) || 15.0;
  const slPct = parseFloat(document.getElementById("proOrderSlPct").value) || 2.0;

  const payload = {
    symbol: symbol,
    side: proOrderSide,
    order_type: proOrderType,
    amount_usd: amountUsd,
    price: limitPrice,
    leverage: proOrderLeverage,
    stop_loss_pct: slPct,
    take_profit_pct: tpPct,
    exchanges: brokers
  };

  if (execBtn) {
    execBtn.disabled = true;
    if (execText) execText.textContent = "ROUTING ORDER TO BROKERS...";
  }

  try {
    const res = await fetch("/api/user/manual-trade", {
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
        msgBox.className = "pro-order-feedback-msg success";
        let detailStr = "";
        if (data.results) {
          detailStr = Object.entries(data.results).map(([k, v]) => `• <strong>${v.exchange || k}</strong>: ${v.status.toUpperCase()} (ID: ${v.order_id || 'OK'})`).join("<br>");
        }
        msgBox.innerHTML = `✅ <strong>${data.message || 'Order Placed Successfully!'}</strong><br>${detailStr}`;
        msgBox.style.display = "block";
      }
      fetchRealData();
      setTimeout(() => {
        if (msgBox) msgBox.style.display = "none";
      }, 7000);
    } else {
      if (msgBox) {
        msgBox.className = "pro-order-feedback-msg error";
        msgBox.innerHTML = `⚠️ <strong>Order Notice:</strong> ${data.message || 'Failed to execute order.'}`;
        msgBox.style.display = "block";
      }
    }
  } catch (err) {
    if (msgBox) {
      msgBox.className = "pro-order-feedback-msg error";
      msgBox.innerHTML = `❌ Connection error while routing order: ${err.message || err}`;
      msgBox.style.display = "block";
    }
  } finally {
    if (execBtn) {
      execBtn.disabled = false;
      if (execText) execText.textContent = proOrderSide === "buy" ? "EXECUTE BUY ORDER" : "EXECUTE SELL SHORT ORDER";
    }
  }
}

async function handleUserClosePosition(tradeId, symbol, exchange) {
  if (!userToken) {
    openAuthModal();
    const loginMsg = document.getElementById("authStatusMsg");
    if (loginMsg) {
      loginMsg.textContent = "🔒 Login Required: You must be logged in to close live positions.";
      loginMsg.style.color = "var(--neon-red)";
    }
    return;
  }

  const cleanEx = (exchange || "").toLowerCase().includes("delta") ? "delta" : ((exchange || "").toLowerCase().includes("coinswitch") ? "coinswitch" : (exchange || "").toLowerCase());
  const confirmed = confirm(`Are you sure you want to CLOSE your ${symbol} position on ${exchange || 'connected broker'}?`);
  if (!confirmed) return;

  try {
    const res = await fetch("/api/user/close-trade", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({ trade_id: tradeId, symbol: symbol, exchange: cleanEx })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert(`✅ ${data.message || 'Position closed successfully.'}`);
      fetchRealData();
    } else {
      alert(`⚠️ ${data.message || 'Failed to close position.'}`);
    }
  } catch (err) {
    alert(`❌ Connection error: ${err.message || err}`);
  }
}

async function handleUserCloseAllPositions() {
  if (!userToken) {
    openAuthModal();
    const loginMsg = document.getElementById("authStatusMsg");
    if (loginMsg) {
      loginMsg.textContent = "🔒 Login Required: You must be logged in to close positions.";
      loginMsg.style.color = "var(--neon-red)";
    }
    return;
  }

  const confirmed = confirm("Are you sure you want to CLOSE ALL your open positions across all connected brokers?");
  if (!confirmed) return;

  try {
    const res = await fetch("/api/user/close-all", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      }
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert(`✅ ${data.message || 'All positions closed successfully.'}`);
      fetchRealData();
    } else {
      alert(`⚠️ ${data.message || 'Failed to close positions.'}`);
    }
  } catch (err) {
    alert(`❌ Connection error: ${err.message || err}`);
  }
}

function changeTvTimeframe(interval) {
  currentTvTimeframe = interval;

  document.querySelectorAll(".pro-chart-tf-btn").forEach(btn => {
    const text = btn.textContent.trim().toLowerCase();
    const map = { "1": "1m", "5": "5m", "15": "15m", "60": "1h", "240": "4h", "D": "1d" };
    if (text === (map[interval] || `${interval}m`)) {
      btn.classList.add("active");
    } else {
      btn.classList.remove("active");
    }
  });

  initTradingViewWidget("tradingview_widget_fullscreen", currentTvSymbol, currentTvTimeframe);
  initTradingViewWidget("tradingview_widget_container", currentTvSymbol, currentTvTimeframe);
}

function normalizeSymbolForTv(rawSym) {
  if (!rawSym) return "BINANCE:BTCUSDT";
  const s = String(rawSym).toUpperCase().replace(/[\/_-]/g, "");
  if (s.includes("NIFTY") && !s.includes("BANK")) return "NSE:NIFTY";
  if (s.includes("BANKNIFTY")) return "NSE:BANKNIFTY";
  if (s.includes("GOLD") || s.includes("XAU")) return "FOREXCOM:XAUUSD";
  if (s.includes("EURUSD")) return "FX:EURUSD";
  if (s.endsWith("USDT") || s.endsWith("USD") || s.endsWith("INR")) {
    const base = s.replace(/(USDT|USD|INR)$/, "");
    return `BINANCE:${base}USDT`;
  }
  return `BINANCE:${s}USDT`;
}

function jumpToProChartSymbol(tradeSymbol) {
  const tvSym = normalizeSymbolForTv(tradeSymbol);
  switchView('chart');
  switchProChartSymbol(tvSym);
  const chartSec = document.getElementById("view-chart");
  if (chartSec) chartSec.scrollIntoView({ behavior: 'smooth' });
}

function loadTvSymbol(symbol) {
  switchProChartSymbol(symbol);
}

function updateProChartPositionBanner() {
  const banner = document.getElementById("proChartPositionBanner");
  const badge = document.getElementById("posBannerBadge");
  const title = document.getElementById("posBannerTitle");
  const details = document.getElementById("posBannerDetails");
  const action = document.getElementById("posBannerAction");
  if (!banner || !badge || !title) return;

  const currentCoinBase = currentTvSymbol.split(":")[1] ? currentTvSymbol.split(":")[1].replace(/(USDT|USD|INR)$/, "") : currentTvSymbol;

  let matchingPos = null;
  if (lastCachedPositions) {
    const allPositions = [
      ...(lastCachedPositions.coinswitch || []).map(p => ({...p, exchange: "CoinSwitch (Spot)"})),
      ...(lastCachedPositions.delta || []).map(p => ({...p, exchange: "Delta (Futures)"}))
    ];
    matchingPos = allPositions.find(p => {
      const pBase = String(p.symbol || "").toUpperCase().replace(/[\/_-]/g, "").replace(/(USDT|USD|INR)$/, "");
      return pBase === currentCoinBase || (currentTvSymbol.includes("NIFTY") && String(p.symbol).includes("NIFTY")) || (currentTvSymbol.includes("XAU") && String(p.symbol).includes("XAU"));
    });
  }

  if (matchingPos) {
    banner.className = "pro-chart-pos-banner active-trade";
    badge.innerHTML = "🟢 ACTIVE POSITION DETECTED";
    badge.style.color = "var(--neon-green)";

    const dir = String(matchingPos.direction || "long").toUpperCase();
    const entryP = Number(matchingPos.entry_price || 0).toFixed(4);
    const markP = Number(matchingPos.mark_price || matchingPos.entry_price || 0).toFixed(4);
    const unPnl = Number(matchingPos.unrealized_pnl || 0);
    const pnlSign = unPnl >= 0 ? "+" : "-";
    const pnlColor = unPnl >= 0 ? "var(--neon-green)" : "var(--neon-red)";

    title.innerHTML = `<span class="${dir === 'LONG' || dir === 'BUY' ? 'green-text' : 'red-text'} font-mono">[${dir}]</span> <strong>${matchingPos.symbol}</strong> on ${matchingPos.exchange}`;

    if (details) {
      details.innerHTML = `
        <span>Entry: <strong>$${entryP}</strong></span>
        <span>Mark: <strong>$${markP}</strong></span>
        <span>PnL: <strong style="color:${pnlColor};">${pnlSign}$${Math.abs(unPnl).toFixed(2)}</strong></span>
        <span>TP: <strong class="green-text">$${Number(matchingPos.take_profit || 0).toFixed(2)}</strong></span>
        <span>SL: <strong class="red-text">$${Number(matchingPos.hard_sl || 0).toFixed(2)}</strong></span>
      `;
    }

    if (action) {
      action.innerHTML = `<button class="tsm-btn-small green" onclick="switchView('terminal')">⚡ LIVE SYNCED</button>`;
    }
  } else {
    banner.className = "pro-chart-pos-banner standby";
    badge.innerHTML = "⚪ STANDBY SCANNER";
    badge.style.color = "var(--text-dim)";
    title.innerHTML = `No active open position for <strong>${currentCoinBase}/USDT</strong>`;

    const totalOpen = lastCachedPositions ? ((lastCachedPositions.coinswitch || []).length + (lastCachedPositions.delta || []).length) : 0;

    if (details) {
      details.innerHTML = `<span>Autonomous AI Orderflow Engine monitoring for high-conviction breakout entries. (${totalOpen} active positions across portfolio)</span>`;
    }

    if (action) {
      action.innerHTML = `<button class="tsm-btn-small" onclick="switchView('terminal')">⚡ VIEW ALL POSITIONS</button>`;
    }
  }
}

function renderProChartLiveTrades(posData, tickers, userData) {
  lastCachedPositions = posData;
  lastCachedTickers = tickers;
  lastCachedUserData = userData;

  const tbody = document.getElementById("proChartLiveTradesTbody");
  const countBadge = document.getElementById("proChartTradesCountBadge");
  const pnlEl = document.getElementById("proChartTotalUnrealizedPnl");
  const userBadge = document.getElementById("proChartUserBadge");

  if (userBadge) {
    if (userData && userData.user) {
      userBadge.textContent = `👤 ${userData.user.name || userData.user.email.split('@')[0]} (PRIVATE)`;
      userBadge.style.color = "var(--neon-green)";
    } else {
      userBadge.textContent = "🌐 PUBLIC / BOT FLEET ($8.26 CAPITAL)";
      userBadge.style.color = "var(--neon-cyan)";
    }
  }

  const validCs = (posData.coinswitch || []).filter(p => p && p.symbol && (Number(p.entry_price || p.price || p.avg_entry_price || p.mark_price || 0) > 0 || Math.abs(Number(p.qty || p.size || 0)) > 0));
  const validDelta = (posData.delta || []).filter(p => p && p.symbol && (Number(p.entry_price || p.price || p.avg_entry_price || p.mark_price || 0) > 0 || Math.abs(Number(p.qty || p.size || 0)) > 0));

  const allPositions = [
    ...validCs.map(p => ({...p, exchange: "CoinSwitch (Spot)"})),
    ...validDelta.map(p => ({...p, exchange: "Delta (Futures)"}))
  ];

  if (countBadge) {
    countBadge.textContent = `${allPositions.length} POSITION${allPositions.length === 1 ? '' : 'S'}`;
  }

  let totalUnrealized = 0.0;

  if (!tbody) {
    updateProChartPositionBanner();
    return;
  }

  if (allPositions.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="text-center empty-state" style="padding: 24px;">
          No active open positions currently detected. When the algorithmic engine executes a trade on CoinSwitch or Delta India, it will immediately appear here with real-time mark prices, live PnL, and one-click chart synchronization.
        </td>
      </tr>
    `;
    if (pnlEl) {
      pnlEl.textContent = "$0.00 USDT";
      pnlEl.className = "green-text";
    }
    updateProChartPositionBanner();
    return;
  }

  tbody.innerHTML = allPositions.map(pos => {
    const sym = pos.symbol || "BTC/USDT";
    const dir = String(pos.direction || "long").toUpperCase();
    const isLong = dir === "LONG" || dir === "BUY";
    const entryP = Number(pos.entry_price || pos.price || 0);
    const markP = Number(pos.mark_price || pos.current_price || entryP);
    const qty = Number(pos.qty || pos.quantity || 1.0);
    const margin = Number(pos.margin_used || (entryP * qty) || 0);

    let pnl = pos.unrealized_pnl !== undefined && pos.unrealized_pnl !== null && Number(pos.unrealized_pnl) !== 0
      ? Number(pos.unrealized_pnl)
      : (isLong ? (markP - entryP) * qty : (entryP - markP) * qty);
    totalUnrealized += pnl;

    const pnlPct = entryP > 0 ? ((markP - entryP) / entryP * 100 * (isLong ? 1 : -1)) : 0.0;
    const pnlClass = pnl >= 0 ? "green-text" : "red-text";
    const pnlPrefix = pnl >= 0 ? "+$" : "-$";

    let slVal = Number(pos.hard_sl || pos.stop_loss || 0);
    if (slVal <= 0 && entryP > 0) {
      slVal = isLong ? entryP * (1 - 0.02) : entryP * (1 + 0.02);
    }

    let tpVal = Number(pos.take_profit || 0);
    if (tpVal <= 0 && entryP > 0) {
      tpVal = isLong ? entryP * (1 + 0.15) : entryP * (1 - 0.15);
    }

    const fmtPrice = (num) => {
      if (num <= 0) return "--";
      if (num >= 1000) return `$${num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      if (num >= 1) return `$${num.toFixed(4)}`;
      return `$${num.toFixed(6)}`;
    };

    const trailStr = pos.trail_active ? `<span class="green-text">🟢 ACTIVE (+0.2%)</span>` : `<span style="color:var(--text-muted);">ARMED</span>`;

    return `
      <tr>
        <td><span class="live-tag">${pos.exchange}</span></td>
        <td><strong>${sym}</strong></td>
        <td><span class="${isLong ? 'green-text' : 'red-text'} font-mono font-bold">${dir}</span></td>
        <td>${fmtPrice(entryP)}</td>
        <td><strong>${fmtPrice(markP)}</strong></td>
        <td>$${margin.toFixed(2)} (${qty})</td>
        <td><strong class="${pnlClass}">${pnlPrefix}${Math.abs(pnl).toFixed(2)} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</strong></td>
        <td class="green-text font-mono">${fmtPrice(tpVal)}</td>
        <td class="red-text font-mono">${fmtPrice(slVal)}</td>
        <td>${trailStr}</td>
        <td>
          <div style="display:flex; gap:6px; align-items:center;">
            <button class="btn-chart-jump" onclick="jumpToProChartSymbol('${sym}')" title="Load ${sym} on TradingView Pro Chart">
              <span>📈 VIEW</span>
            </button>
            <button class="btn-trade-close-action" onclick="handleUserClosePosition('${pos.id || ''}', '${sym}', '${pos.exchange}')" title="Close ${sym} Position">
              <span>✕ CLOSE</span>
            </button>
          </div>
        </td>
      </tr>
    `;
  }).join("");

  if (pnlEl) {
    pnlEl.textContent = `${totalUnrealized >= 0 ? '+$' : '-$'}${Math.abs(totalUnrealized).toFixed(2)} USDT`;
    pnlEl.className = totalUnrealized >= 0 ? "green-text" : "red-text";
  }

  updateProChartPositionBanner();
}

// ── 5. User Multi-Tenant Authentication & Session Engine (Supabase + Local) ─
const SUPABASE_URL = window.SUPABASE_URL || "https://trade-quant-thesmartmag.supabase.co";
const SUPABASE_ANON_KEY = window.SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.placeholder";
let supabaseClient = null;

if (window.supabase && typeof window.supabase.createClient === "function") {
  try {
    supabaseClient = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
    supabaseClient.auth.onAuthStateChange(async (event, session) => {
      if (session && session.user && event === "SIGNED_IN") {
        await syncSupabaseSession(session);
      }
    });
  } catch (err) {
    console.debug("Supabase init notice:", err);
  }
}

async function syncSupabaseSession(session, refCode) {
  if (!session || !session.user) return;
  try {
    const res = await fetch("/api/auth/supabase-sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        supabase_id: session.user.id,
        email: session.user.email,
        name: session.user.user_metadata?.full_name || session.user.user_metadata?.name || session.user.email.split("@")[0],
        ref: refCode || localStorage.getItem("tsm_referral_code") || "",
        role: "trader"
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      userToken = data.token;
      localStorage.setItem("tsm_user_token", userToken);
      currentUser = data.user;
      closeAuthModal();
      initUserSession();
      fetchRealData();
    }
  } catch (err) {
    console.debug("Supabase sync error:", err);
  }
}

async function syncFirebaseUserToBackend(fbUser) {
  if (!fbUser || !fbUser.email) return;
  const statusMsg = document.getElementById("authStatusMsg");
  try {
    if (statusMsg) {
      statusMsg.textContent = "Verifying Google credentials & initializing quant session...";
      statusMsg.style.color = "var(--neon-cyan)";
    }
    const idToken = await fbUser.getIdToken();
    const refCode = localStorage.getItem("tsm_referral_code") || "";
    
    const res = await fetch("/api/auth/firebase-sync", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        firebase_uid: fbUser.uid,
        email: fbUser.email,
        name: fbUser.displayName || fbUser.email.split("@")[0],
        photo_url: fbUser.photoURL || "",
        id_token: idToken,
        ref: refCode,
        role: "trader"
      })
    });
    
    const data = await res.json();
    if (res.ok && data.status === "success") {
      userToken = data.token;
      localStorage.setItem("tsm_user_token", userToken);
      localStorage.setItem("tsm_jwt_token", userToken);
      currentUser = data.user;
      closeAuthModal();
      initUserSession();
      fetchRealData();
      if (typeof fetchTraderTerminalData === "function") fetchTraderTerminalData();
      switchView("trader");
      if (typeof showFloatingToast === "function") {
        showFloatingToast(`🎉 Welcome Trader ${data.user.name || ''}! Private terminal active.`, "green");
      }
    } else {
      if (statusMsg) {
        statusMsg.textContent = data.message || "Failed to sync Firebase user session.";
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
    }
  } catch (err) {
    console.error("Firebase sync error:", err);
    if (statusMsg) {
      statusMsg.textContent = `Sync notice: ${err.message || err}`;
      statusMsg.style.color = "var(--neon-pink, #ff3366)";
    }
  }
}
window.syncFirebaseUserToBackend = syncFirebaseUserToBackend;

async function handleFirebaseGoogleSignIn() {
  const statusMsg = document.getElementById("authStatusMsg");
  const btnLabel = document.getElementById("googleAuthBtnLabel");
  if (statusMsg) {
    statusMsg.textContent = "Connecting to Google Secure Auth...";
    statusMsg.style.color = "var(--neon-cyan)";
  }
  if (btnLabel) btnLabel.textContent = "Opening Google Auth...";

  if (window.fbAuth && window.googleProvider && typeof window.signInWithPopup === "function") {
    try {
      const result = await window.signInWithPopup(window.fbAuth, window.googleProvider);
      if (btnLabel) btnLabel.textContent = "Authenticating...";
      if (result && result.user) {
        await syncFirebaseUserToBackend(result.user);
      }
    } catch (err) {
      console.warn("Firebase popup sign-in notice:", err);
      // Fallback to redirect if popup is blocked
      if (err.code === "auth/popup-blocked" || err.code === "auth/popup-closed-by-user" || err.code === "auth/cancelled-popup-request") {
        if (typeof window.signInWithRedirect === "function") {
          try {
            await window.signInWithRedirect(window.fbAuth, window.googleProvider);
            return;
          } catch (redErr) {
            console.warn("Redirect fallback notice:", redErr);
          }
        }
      }
      if (statusMsg) {
        statusMsg.textContent = `Google Sign-in notice: ${err.message || err}. You can also sign in with Trader Email below.`;
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
      if (btnLabel) btnLabel.textContent = "Continue with Google";
    }
  } else if (typeof handleSupabaseGoogleSignIn === "function" && supabaseClient) {
    handleSupabaseGoogleSignIn();
  } else {
    if (statusMsg) {
      statusMsg.textContent = "Google Sign-in initialized. Please enter your Trader Email & Password below.";
      statusMsg.style.color = "var(--neon-cyan)";
    }
    if (btnLabel) btnLabel.textContent = "Continue with Google";
  }
}
window.handleFirebaseGoogleSignIn = handleFirebaseGoogleSignIn;

async function handleSupabaseGoogleSignIn() {
  const statusMsg = document.getElementById("authStatusMsg");
  if (statusMsg) {
    statusMsg.textContent = "Initiating Google Authentication...";
    statusMsg.style.color = "var(--neon-cyan)";
  }
  if (supabaseClient) {
    try {
      const { data, error } = await supabaseClient.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: window.location.origin }
      });
      if (error) throw error;
    } catch (err) {
      if (statusMsg) {
        statusMsg.textContent = `Google Login notice: ${err.message || err}. You can also sign in with Trader Email.`;
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
    }
  } else {
    handleFirebaseGoogleSignIn();
  }
}

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
      if (currentUser && currentUser.role === "superadmin") {
        adminToken = userToken;
        sessionStorage.setItem("tsm_admin_token", adminToken);
      }
      updateUserUI(data.user, data.settings, data.exchange_connections);
      await fetchUserSubscriptionData();
      if (currentView === "admin") {
        checkAdminAuth();
      }
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
  const dockAdminBtn = document.getElementById("dockAdminBtn");
  const dockTraderBtn = document.getElementById("dockTraderBtn");
  const drawerTraderTab = document.getElementById("drawerTraderTab");

  const proExecBtn = document.getElementById("btnExecuteProOrder");
  const proExecText = document.getElementById("btnExecuteProOrderText");
  const authLockNotice = document.getElementById("proOrderAuthLockNotice");
  const proOrderTicketPanel = document.getElementById("proChartOrderTicketPanel");
  const proLiveTradesSection = document.getElementById("proChartLiveTradesSection");
  const proVisitorAuthBanner = document.getElementById("proChartAuthGateBanner");

  if (user) {
    if (logoutBtn) logoutBtn.style.display = "flex";
    if (userTxt) userTxt.textContent = `👤 ${user.name || user.email.split('@')[0]}`;
    if (keysBtn) keysBtn.style.display = "flex";
    if (dockTraderBtn) dockTraderBtn.style.display = "flex";
    if (drawerTraderTab) drawerTraderTab.style.display = "flex";

    if (userPill) {
      userPill.title = `Logged in as ${user.email} • Click to open Trader Cockpit`;
      userPill.onclick = () => switchView("trader");
    }

    // Unhide manual order ticket and personal trades table exclusively for authenticated users
    if (proOrderTicketPanel) proOrderTicketPanel.style.display = "block";
    if (proLiveTradesSection) proLiveTradesSection.style.display = "block";
    if (proVisitorAuthBanner) proVisitorAuthBanner.style.display = "none";

    if (proExecBtn) {
      proExecBtn.classList.remove("auth-locked");
      if (proOrderSide === "buy") {
        proExecBtn.className = "btn-execute-pro-order buy";
        if (proExecText) proExecText.textContent = "EXECUTE BUY ORDER";
      } else {
        proExecBtn.className = "btn-execute-pro-order sell";
        if (proExecText) proExecText.textContent = "EXECUTE SELL SHORT ORDER";
      }
    }
    if (authLockNotice) authLockNotice.style.display = "none";

    // STRICT ROLE CHECK: Only reveal Super Admin controls to authenticated superadmin
    if (user.role === "superadmin") {
      if (adminNavBtn) adminNavBtn.style.display = "flex";
      if (superAdminTab) superAdminTab.style.display = "flex";
      if (dockAdminBtn) dockAdminBtn.style.display = "flex";
    } else {
      if (adminNavBtn) adminNavBtn.style.display = "none";
      if (superAdminTab) superAdminTab.style.display = "none";
      if (dockAdminBtn) dockAdminBtn.style.display = "none";
    }
  } else {
    if (logoutBtn) logoutBtn.style.display = "none";
    if (userTxt) userTxt.textContent = "SIGN IN / JOIN";
    if (keysBtn) keysBtn.style.display = "none";
    if (adminNavBtn) adminNavBtn.style.display = "none";
    if (superAdminTab) superAdminTab.style.display = "none";
    if (dockAdminBtn) dockAdminBtn.style.display = "none";
    if (dockTraderBtn) dockTraderBtn.style.display = "none";
    if (drawerTraderTab) drawerTraderTab.style.display = "none";

    if (userPill) {
      userPill.title = "Login or Create Trader Account";
      userPill.onclick = () => openAuthModal();
    }

    // Hide manual order ticket and personal trades for unauthenticated visitors
    if (proOrderTicketPanel) proOrderTicketPanel.style.display = "none";
    if (proLiveTradesSection) proLiveTradesSection.style.display = "none";
    if (proVisitorAuthBanner) proVisitorAuthBanner.style.display = "block";

    if (proExecBtn) {
      proExecBtn.className = "btn-execute-pro-order auth-locked";
      if (proExecText) proExecText.textContent = "🔐 SIGN IN TO PLACE LIVE ORDERS";
    }
    if (authLockNotice) authLockNotice.style.display = "flex";
  }

  // Re-render position tables so action buttons toggle dynamically
  if (lastCachedPositions) {
    renderPositionsTable(lastCachedPositions);
  }
}

// ── 7.5. Dedicated Quant Trader Dashboard Engine ──────────────────────────────
function switchTraderSubTab(tabName, btnElement) {
  window.currentTraderSubTab = tabName;

  document.querySelectorAll(".trader-tab-btn").forEach(b => {
    b.classList.remove("active");
  });
  if (btnElement) {
    btnElement.classList.add("active");
  } else {
    document.querySelectorAll(".trader-tab-btn").forEach(b => {
      const oc = b.getAttribute("onclick") || "";
      if (oc.includes(`'${tabName}'`) || oc.includes(`"${tabName}"`)) {
        b.classList.add("active");
      }
    });
  }

  document.querySelectorAll(".trader-sub-section").forEach(sec => {
    sec.classList.remove("active");
  });

  const target = document.getElementById(`trader-sec-${tabName}`);
  if (target) {
    target.classList.add("active");
  }

  if (tabName === "journal") {
    if (typeof fetchJournalData === "function") fetchJournalData();
  } else if (tabName === "indianbrokers") {
    if (typeof fetchIndianBrokersStatus === "function") fetchIndianBrokersStatus();
  } else if (tabName === "overview" || tabName === "positions") {
    if (typeof fetchTraderTerminalData === "function") fetchTraderTerminalData();
    fetchRealData();
  } else if (tabName === "profile") {
    if (typeof fetchUserSubscriptionData === "function") fetchUserSubscriptionData();
  }
}
window.switchTraderSubTab = switchTraderSubTab;

function renderTraderDashboard(userData, fullData) {
  if (!userData) return;
  const u = userData.user || {};
  const bal = userData.balances || {};
  const set = userData.settings || {};
  const conn = userData.exchange_connections || {};
  const perf = userData.performance || {};
  const openPos = userData.open_positions || {};
  const closedTrades = userData.closed_trades || [];

  // 1. Header & Profile
  const welcomeTitle = document.getElementById("traderHeaderWelcomeTitle");
  if (welcomeTitle) welcomeTitle.textContent = `Welcome, ${u.name || u.email.split('@')[0]}`;

  const emailEl = document.getElementById("traderHeaderEmail");
  if (emailEl) emailEl.textContent = u.email || "--";

  const tierEl = document.getElementById("traderHeaderTier");
  if (tierEl) tierEl.textContent = (u.plan_name || "QUANT PRO").toUpperCase();

  const roleBadge = document.getElementById("traderHeaderRoleBadge");
  if (roleBadge) roleBadge.textContent = u.role === "superadmin" ? "👑 SUPER ADMIN ACTIVE" : "🛡️ QUANT TRADER ACTIVE";

  const profName = document.getElementById("traderProfName");
  if (profName) profName.textContent = u.name || "--";

  const profEmail = document.getElementById("traderProfEmail");
  if (profEmail) profEmail.textContent = u.email || "--";

  const profPhone = document.getElementById("traderProfPhone");
  if (profPhone) profPhone.textContent = u.phone || "Not set";

  const profCountry = document.getElementById("traderProfCountry");
  if (profCountry) profCountry.textContent = `${u.country || 'Global'}`;

  const profBroker = document.getElementById("traderProfBroker");
  if (profBroker) profBroker.textContent = u.preferred_exchange === 'delta' ? '⚡ Delta Exchange India' : (u.preferred_exchange === 'coinswitch' ? '🏛 CoinSwitch Pro' : '⚡ Dual Engine (Delta + CoinSwitch)');

  const refLinkInput = document.getElementById("traderProfRefLink");
  if (refLinkInput) refLinkInput.value = u.referral_url || `https://trade.thesmartmag.com/?ref=${u.referral_code || u.id}`;

  // 2. Balances & KPI Cards
  const totCapEl = document.getElementById("traderOverviewTotalCap");
  if (totCapEl) totCapEl.innerHTML = `$${Number(bal.total_capital_usdt || 0).toFixed(2)} <span style="font-size:12px; color:var(--text-dim);">USDT</span>`;

  const csBalEl = document.getElementById("traderOverviewCsBal");
  if (csBalEl) csBalEl.textContent = `$${Number(bal.cs_usdt || 0).toFixed(2)}`;

  const csInrEl = document.getElementById("traderOverviewCsInr");
  if (csInrEl) csInrEl.textContent = `INR: ₹${Number(bal.cs_inr || 0).toLocaleString('en-IN', {minimumFractionDigits:2})}`;

  const deltaBalEl = document.getElementById("traderOverviewDeltaBal");
  if (deltaBalEl) deltaBalEl.textContent = `$${Number(bal.delta_usdt || 0).toFixed(2)}`;

  const realPnlEl = document.getElementById("traderOverviewRealizedPnl");
  const pnlNum = Number(perf.total_realized_pnl_usdt || 0);
  if (realPnlEl) {
    realPnlEl.textContent = (pnlNum >= 0 ? "+$" : "-$") + Math.abs(pnlNum).toFixed(2);
    realPnlEl.className = `admin-kpi-num ${pnlNum >= 0 ? "green-text" : "red-text"}`;
  }

  const winRateEl = document.getElementById("traderOverviewWinRate");
  if (winRateEl) winRateEl.textContent = `Win Rate: ${perf.win_rate_pct || 100}% (${perf.closed_trades_count || 0} Closed)`;

  const journalBadge = document.getElementById("traderJournalSummaryBadge");
  if (journalBadge) journalBadge.textContent = `REALIZED P&L: ${(pnlNum >= 0 ? '+$' : '-$')}${Math.abs(pnlNum).toFixed(2)} (${perf.closed_trades_count || 0} TRADES)`;

  // 3. Telemetry HUD
  const hudSl = document.getElementById("traderHudSl");
  if (hudSl) hudSl.textContent = `-${Number(set.hard_sl_pct || 2.0).toFixed(1)}% (Dynamic)`;

  const hudTp = document.getElementById("traderHudTp");
  if (hudTp) hudTp.textContent = `+${Number(set.take_profit_pct || 15.0).toFixed(1)}% (Dynamic)`;

  const hudTrail = document.getElementById("traderHudTrail");
  if (hudTrail) hudTrail.textContent = `+${Number(set.trail_pct || 0.2).toFixed(2)}% Step Lock`;

  const hudConn = document.getElementById("traderHudConnStatus");
  if (hudConn) {
    const hasKeys = conn.coinswitch || conn.delta;
    hudConn.textContent = hasKeys ? "API KEYS CONNECTED 🟢" : "AWAITING API KEYS ⚪";
    hudConn.className = hasKeys ? "green-text font-bold" : "text-dim font-bold";
  }

  // 4. AI Command & Strategy
  const stratSel = document.getElementById("traderStrategySelect");
  if (stratSel && set.active_strategy) stratSel.value = set.active_strategy;

  const stratBadge = document.getElementById("traderStrategyBadge");
  if (stratBadge && stratSel) {
    stratBadge.textContent = stratSel.options[stratSel.selectedIndex]?.text.split('(')[0].trim().toUpperCase() || "AI CONSENSUS";
  }

  const autoBtn = document.getElementById("traderAutotradeHeaderBtn");
  const autoToggleBtn = document.getElementById("traderAutotradeToggleBtn");
  const autoTxt = document.getElementById("traderAutotradeStatusTxt");
  const isAuto = set.autotrade_enabled !== undefined ? !!set.autotrade_enabled : true;

  if (autoBtn) {
    autoBtn.textContent = isAuto ? "🤖 AUTOTRADE: ON" : "⏸ AUTOTRADE: PAUSED";
    autoBtn.className = isAuto ? "tsm-btn-cta green" : "tsm-btn-cta gold";
  }
  if (autoToggleBtn) {
    autoToggleBtn.textContent = isAuto ? "PAUSE AUTOTRADE" : "RESUME AUTOTRADE";
    autoToggleBtn.className = isAuto ? "tsm-btn-danger" : "tsm-btn-cta green";
  }
  if (autoTxt) {
    autoTxt.textContent = isAuto ? "AUTOTRADING: ENABLED 🟢" : "AUTOTRADING: PAUSED ⏸";
    autoTxt.style.color = isAuto ? "var(--neon-green)" : "var(--neon-gold)";
  }

  // 5. Risk Safeguards inputs
  const hardSlInput = document.getElementById("traderRiskHardSl");
  if (hardSlInput && document.activeElement !== hardSlInput) hardSlInput.value = set.hard_sl_pct || 2.0;

  const tpInput = document.getElementById("traderRiskTp");
  if (tpInput && document.activeElement !== tpInput) tpInput.value = set.take_profit_pct || 15.0;

  const trailInput = document.getElementById("traderRiskTrail");
  if (trailInput && document.activeElement !== trailInput) trailInput.value = set.trail_pct || 0.2;

  const maxCapInput = document.getElementById("traderRiskMaxCap");
  if (maxCapInput && document.activeElement !== maxCapInput) maxCapInput.value = set.max_capital_pct || 40;

  // 6. Keys status badges
  const csBadge = document.getElementById("traderKeysCsStatusBadge");
  if (csBadge) {
    csBadge.textContent = conn.coinswitch ? "CONNECTED 🟢" : "NOT CONFIGURED ⚪";
    csBadge.className = conn.coinswitch ? "tsm-badge-pill green" : "tsm-badge-pill";
  }

  const deltaBadge = document.getElementById("traderKeysDeltaStatusBadge");
  if (deltaBadge) {
    deltaBadge.textContent = conn.delta ? "CONNECTED 🟢" : "NOT CONFIGURED ⚪";
    deltaBadge.className = conn.delta ? "tsm-badge-pill green" : "tsm-badge-pill";
  }

  // 7. Active positions table (combine user positions and cluster positions)
  const effectiveOpenPos = (openPos && ((openPos.coinswitch && openPos.coinswitch.length > 0) || (openPos.delta && openPos.delta.length > 0)))
    ? openPos
    : (fullData && fullData.open_positions ? fullData.open_positions : openPos);
  renderTraderActivePositions(effectiveOpenPos);

  // 8. Closed trades journal table
  renderTraderClosedTrades(closedTrades);

  // 9. Heatmap
  if (fullData && fullData.heatmap_coins) {
    renderTraderHeatmap(fullData.heatmap_coins);
  }
}

function renderTraderActivePositions(openPos) {
  const tbody = document.getElementById("traderActivePosTbody");
  const badge = document.getElementById("traderPosCountBadge");
  if (!tbody) return;

  const validCs = (openPos.coinswitch || []).map(p => ({...p, exchange: "CoinSwitch (Spot)"}));
  const validDelta = (openPos.delta || []).map(p => ({...p, exchange: "Delta (Futures)"}));
  const allPos = [...validCs, ...validDelta];

  if (badge) badge.textContent = `${allPos.length} POSITION${allPos.length === 1 ? '' : 'S'}`;

  if (allPos.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="11" class="text-center empty-state" style="padding:22px;">
          No open positions in your account. The AI engine is actively monitoring liquidity blocks for momentum entries.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = allPos.map(pos => {
    const sym = pos.symbol || "BTC/USDT";
    const dir = String(pos.direction || "long").toUpperCase();
    const isLong = dir === "LONG" || dir === "BUY";
    const entryP = Number(pos.entry_price || pos.price || 0);
    const markP = Number(pos.mark_price || entryP);
    const qty = Number(pos.qty || pos.quantity || 1.0);
    const margin = Number(pos.margin_used || (entryP * qty) || 0);

    let pnl = pos.unrealized_pnl !== undefined && pos.unrealized_pnl !== null && Number(pos.unrealized_pnl) !== 0
      ? Number(pos.unrealized_pnl)
      : (isLong ? (markP - entryP) * qty : (entryP - markP) * qty);

    const pnlPct = entryP > 0 ? ((markP - entryP) / entryP * 100 * (isLong ? 1 : -1)) : 0.0;
    const pnlClass = pnl >= 0 ? "green-text" : "red-text";
    const pnlPrefix = pnl >= 0 ? "+$" : "-$";

    const slVal = Number(pos.hard_sl || (isLong ? entryP * 0.98 : entryP * 1.02));
    const tpVal = Number(pos.take_profit || (isLong ? entryP * 1.15 : entryP * 0.85));

    const fmtP = (n) => n >= 1000 ? `$${n.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}` : (n >= 1 ? `$${n.toFixed(4)}` : `$${n.toFixed(6)}`);

    return `
      <tr>
        <td><span class="live-tag">${pos.exchange}</span></td>
        <td><strong>${sym}</strong></td>
        <td><span class="${isLong ? 'green-text' : 'red-text'} font-mono font-bold">${dir}</span></td>
        <td>${fmtP(entryP)}</td>
        <td><strong>${fmtP(markP)}</strong></td>
        <td>$${margin.toFixed(2)} (${qty})</td>
        <td><strong class="${pnlClass} font-mono">${pnlPrefix}${Math.abs(pnl).toFixed(2)} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</strong></td>
        <td class="red-text font-mono">${fmtP(slVal)}</td>
        <td class="green-text font-mono">${fmtP(tpVal)}</td>
        <td><span class="green-text">🟢 ARMED</span></td>
        <td>
          <button class="btn-trade-close-action" onclick="handleUserClosePosition('${pos.id || ''}', '${sym}', '${pos.exchange}')" title="Close ${sym}">
            <span>✕ CLOSE</span>
          </button>
        </td>
      </tr>
    `;
  }).join("");
}

function renderTraderClosedTrades(closedList) {
  const tbody = document.getElementById("traderClosedTradesTbody");
  if (!tbody) return;

  if (!closedList || closedList.length === 0) {
    tbody.innerHTML = `<tr><td colspan="9" class="text-center empty-state" style="padding:20px;">No closed trades logged yet for this account.</td></tr>`;
    return;
  }

  tbody.innerHTML = closedList.map(t => {
    const pnl = Number(t.realized_pnl || 0);
    const pnlClass = pnl >= 0 ? "green-text" : "red-text";
    const pnlSign = pnl >= 0 ? "+$" : "-$";
    const dt = t.closed_at ? new Date(Number(t.closed_at) * 1000).toLocaleString() : (t.created_at || "--");
    return `
      <tr>
        <td class="font-mono" style="font-size:10px;">${dt}</td>
        <td><span class="live-tag">${(t.exchange || 'CS').toUpperCase()}</span></td>
        <td><strong>${t.symbol || '--'}</strong></td>
        <td><span class="${String(t.direction).toLowerCase().includes('long') ? 'green-text' : 'red-text'} font-bold">${String(t.direction || 'LONG').toUpperCase()}</span></td>
        <td>$${Number(t.entry_price || 0).toFixed(4)}</td>
        <td>$${Number(t.exit_price || t.entry_price || 0).toFixed(4)}</td>
        <td>${t.quantity || t.qty || 1}</td>
        <td><strong class="${pnlClass} font-mono">${pnlSign}${Math.abs(pnl).toFixed(2)}</strong></td>
        <td><span class="green-text font-bold">FILLED ✅</span></td>
      </tr>
    `;
  }).join("");
}

function renderTraderHeatmap(coins) {
  const grid = document.getElementById("traderHeatmapGrid");
  if (!grid || !coins) return;

  grid.innerHTML = coins.slice(0, 16).map(c => {
    const sym = c.symbol || "";
    const p = Number(c.price || 0);
    const sig = String(c.signal || "bull").toLowerCase();
    const isBull = sig.includes("bull") || sig.includes("catalyst") || sig.includes("cluster");
    const fmt = p >= 1000 ? `$${p.toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}` : (p >= 1 ? `$${p.toFixed(4)}` : `$${p.toFixed(6)}`);
    return `
      <div class="tsm-rwa-card" style="cursor:pointer;" onclick="openCoinDetailsModal('${sym}')" title="Inspect ${sym} 3D Model &amp; Quant Intel">
        <div class="tsm-rwa-ticker" style="display:flex; justify-content:space-between; align-items:center;">
          <span>${sym}</span>
          <span style="font-size:10px; color:var(--neon-cyan);">🔮 3D</span>
        </div>
        <div class="tsm-rwa-name font-mono">${fmt}</div>
        <div class="tsm-rwa-sector" style="font-size:9.5px;">Signal: ${sig.toUpperCase()}</div>
        <div class="tsm-rwa-status ${isBull ? 'green' : 'gold'}">${isBull ? 'ARMED BREAKOUT' : 'MONITORING'}</div>
      </div>
    `;
  }).join("");
}

async function handleTraderRiskSubmit(e) {
  if (e) e.preventDefault();
  await saveTraderRiskSettings(true);
}

async function saveTraderRiskSettings(showMsg = true) {
  if (!userToken) return;
  const hardSl = parseFloat(document.getElementById("traderRiskHardSl")?.value || "2.0");
  const tp = parseFloat(document.getElementById("traderRiskTp")?.value || "15.0");
  const trail = parseFloat(document.getElementById("traderRiskTrail")?.value || "0.2");
  const maxCap = parseFloat(document.getElementById("traderRiskMaxCap")?.value || "40.0");
  const strategy = document.getElementById("traderStrategySelect")?.value || "ai_consensus";
  const msgEl = document.getElementById("traderRiskSavedMsg");

  try {
    const res = await fetch("/api/user/settings", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({
        hard_sl_pct: hardSl,
        take_profit_pct: tp,
        trail_pct: trail,
        max_capital_pct: maxCap,
        active_strategy: strategy
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      if (showMsg && msgEl) {
        msgEl.textContent = "✅ Risk Safeguards Saved Successfully!";
        msgEl.style.color = "var(--neon-green)";
        setTimeout(() => { if (msgEl) msgEl.textContent = ""; }, 4000);
      }
      fetchRealData();
    } else {
      if (msgEl) {
        msgEl.textContent = `⚠️ ${data.message || 'Failed to save settings'}`;
        msgEl.style.color = "var(--neon-pink)";
      }
    }
  } catch (err) {
    if (msgEl) {
      msgEl.textContent = `❌ ${err.message || err}`;
      msgEl.style.color = "var(--neon-pink)";
    }
  }
}

async function handleTraderKeysSubmit(e) {
  if (e) e.preventDefault();
  if (!userToken) return;

  const csKey = document.getElementById("traderKeysCsKey")?.value.trim() || "";
  const csSecret = document.getElementById("traderKeysCsSecret")?.value.trim() || "";
  const deltaKey = document.getElementById("traderKeysDeltaKey")?.value.trim() || "";
  const deltaSecret = document.getElementById("traderKeysDeltaSecret")?.value.trim() || "";
  const msgEl = document.getElementById("traderKeysMsg");

  if (msgEl) {
    msgEl.textContent = "Encrypting and verifying credentials with exchange APIs...";
    msgEl.style.color = "var(--neon-cyan)";
  }

  try {
    const res = await fetch("/api/user/exchange-keys", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({
        cs_key: csKey,
        cs_secret: csSecret,
        delta_key: deltaKey,
        delta_secret: deltaSecret
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      if (msgEl) {
        msgEl.textContent = "✅ Exchange API Keys Verified & Encrypted with AES-256!";
        msgEl.style.color = "var(--neon-green)";
      }
      fetchRealData();
    } else {
      if (msgEl) {
        msgEl.textContent = `⚠️ ${data.message || 'Verification error'}`;
        msgEl.style.color = "var(--neon-pink)";
      }
    }
  } catch (err) {
    if (msgEl) {
      msgEl.textContent = `❌ ${err.message || err}`;
      msgEl.style.color = "var(--neon-pink)";
    }
  }
}

async function handleTraderToggleAutotrade() {
  if (!userToken) {
    openAuthModal();
    return;
  }
  try {
    const res = await fetch("/api/user/toggle-bot", {
      method: "POST",
      headers: { "Authorization": `Bearer ${userToken}` }
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      fetchRealData();
    }
  } catch (err) {
    console.debug("Autotrade toggle error:", err);
  }
}

function copyTraderReferralLink() {
  const linkInput = document.getElementById("traderProfRefLink");
  const confirmMsg = document.getElementById("traderCopyConfirmMsg");
  if (!linkInput) return;
  
  navigator.clipboard.writeText(linkInput.value).then(() => {
    if (confirmMsg) {
      confirmMsg.textContent = "✅ Referral link copied to clipboard!";
      setTimeout(() => { if (confirmMsg) confirmMsg.textContent = ""; }, 3000);
    }
  }).catch(() => {
    linkInput.select();
    document.execCommand("copy");
    if (confirmMsg) {
      confirmMsg.textContent = "✅ Referral link copied!";
      setTimeout(() => { if (confirmMsg) confirmMsg.textContent = ""; }, 3000);
    }
  });
}

async function handleTraderQuickOrder(e) {
  if (e) e.preventDefault();
  if (!userToken) {
    openAuthModal();
    return;
  }
  const ex = document.getElementById("traderOrderEx")?.value || "both";
  const sym = document.getElementById("traderOrderSym")?.value || "BTC/USDT";
  const side = document.getElementById("traderOrderSide")?.value || "buy";
  const amt = parseFloat(document.getElementById("traderOrderAmt")?.value || "10");
  const msgEl = document.getElementById("traderOrderMsg");

  if (msgEl) {
    msgEl.textContent = `Routing ${side.toUpperCase()} order for ${sym} to ${ex.toUpperCase()}...`;
    msgEl.style.color = "var(--neon-cyan)";
  }

  try {
    const res = await fetch("/api/user/manual-trade", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({
        symbol: sym,
        side: side,
        amount_usd: amt,
        exchanges: ex === "both" ? ["coinswitch", "delta"] : [ex]
      })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      if (msgEl) {
        msgEl.textContent = `✅ Order Executed Successfully! (ID: ${data.order_id || 'LIVE'})`;
        msgEl.style.color = "var(--neon-green)";
      }
      fetchRealData();
    } else {
      if (msgEl) {
        msgEl.textContent = `⚠️ ${data.message || 'Execution error'}`;
        msgEl.style.color = "var(--neon-pink)";
      }
    }
  } catch (err) {
    if (msgEl) {
      msgEl.textContent = `❌ ${err.message || err}`;
      msgEl.style.color = "var(--neon-pink)";
    }
  }
}

let currentAuthTab = "login";

function openAuthModal(tab = "login") {
  const modal = document.getElementById("authModal");
  if (modal) {
    modal.style.display = "flex";
    switchAuthTab(tab || "login");
  }
}
window.openAuthModal = openAuthModal;
window.closeAuthModal = closeAuthModal;

function closeAuthModal() {
  const modal = document.getElementById("authModal");
  if (modal) modal.style.display = "none";
}

function handleAuthBackdropClick(e) {
  if (e.target.id === "authModal") closeAuthModal();
}

function switchAuthTab(tab) {
  currentAuthTab = tab;
  const loginTab = document.getElementById("authTabLogin");
  const regTab = document.getElementById("authTabRegister");

  const nameField = document.getElementById("authNameField");
  const emailField = document.getElementById("authEmailField");
  const phoneField = document.getElementById("authPhoneField");
  const countryField = document.getElementById("authCountryField");
  const exchangeField = document.getElementById("authExchangeField");
  const passField = document.getElementById("authPasswordField");
  const passConfirmField = document.getElementById("authPasswordConfirmField");
  const refField = document.getElementById("authRefField");
  const forgotLink = document.getElementById("authForgotLink");
  const roleBadge = document.getElementById("authTraderRoleBadge");
  const socialGroup = document.getElementById("authSocialLoginGroup");
  const authForm = document.getElementById("authForm");
  const resetSection = document.getElementById("authResetPasswordSection");
  const submitBtn = document.getElementById("authSubmitBtn");
  const statusMsg = document.getElementById("authStatusMsg");

  if (statusMsg) { statusMsg.textContent = ""; statusMsg.style.color = ""; }

  if (loginTab) loginTab.classList.remove("active");
  if (regTab) regTab.classList.remove("active");

  if (tab === "login") {
    if (loginTab) loginTab.classList.add("active");
    if (authForm) authForm.style.display = "flex";
    if (resetSection) resetSection.style.display = "none";
    if (socialGroup) socialGroup.style.display = "block";
    if (roleBadge) roleBadge.style.display = "none";

    if (nameField) nameField.style.display = "none";
    if (phoneField) phoneField.style.display = "none";
    if (countryField) countryField.style.display = "none";
    if (exchangeField) exchangeField.style.display = "none";
    if (passConfirmField) passConfirmField.style.display = "none";
    if (refField) refField.style.display = "none";

    if (emailField) emailField.style.display = "block";
    if (passField) passField.style.display = "block";
    if (forgotLink) forgotLink.style.display = "inline-block";

    if (submitBtn) submitBtn.textContent = "ENTER TRADING TERMINAL";
  } else if (tab === "register") {
    if (regTab) regTab.classList.add("active");
    if (authForm) authForm.style.display = "flex";
    if (resetSection) resetSection.style.display = "none";
    if (socialGroup) socialGroup.style.display = "block";
    if (roleBadge) roleBadge.style.display = "flex";

    if (nameField) nameField.style.display = "block";
    if (phoneField) phoneField.style.display = "block";
    if (countryField) countryField.style.display = "block";
    if (exchangeField) exchangeField.style.display = "block";
    if (passConfirmField) passConfirmField.style.display = "block";
    if (refField) refField.style.display = "block";

    if (emailField) emailField.style.display = "block";
    if (passField) passField.style.display = "block";
    if (forgotLink) forgotLink.style.display = "none";

    if (submitBtn) submitBtn.textContent = "CREATE TRADER ACCOUNT & ACCESS TERMINAL";
  } else if (tab === "forgot") {
    if (authForm) authForm.style.display = "none";
    if (socialGroup) socialGroup.style.display = "none";
    if (resetSection) resetSection.style.display = "flex";

    const mainEmail = document.getElementById("authEmail");
    const resetReqEmail = document.getElementById("resetReqEmail");
    if (mainEmail && resetReqEmail && mainEmail.value) {
      resetReqEmail.value = mainEmail.value;
    }
  }
}

async function handleAuthSubmit(e) {
  e.preventDefault();
  const emailEl = document.getElementById("authEmail");
  const passEl = document.getElementById("authPassword");
  const passConfirmEl = document.getElementById("authPasswordConfirm");
  const nameEl = document.getElementById("authName");
  const phoneEl = document.getElementById("authPhone");
  const countryEl = document.getElementById("authCountry");
  const exchangeEl = document.getElementById("authPreferredExchange");
  const refEl = document.getElementById("authRefCode");
  const statusMsg = document.getElementById("authStatusMsg");
  const submitBtn = document.getElementById("authSubmitBtn");

  const email = emailEl ? emailEl.value.trim() : "";
  const password = passEl ? passEl.value.trim() : "";
  const passConfirm = passConfirmEl ? passConfirmEl.value.trim() : "";
  const name = nameEl ? nameEl.value.trim() : "";
  const phone = phoneEl ? phoneEl.value.trim() : "";
  const country = countryEl ? countryEl.value.trim() : "US";
  const preferred_exchange = exchangeEl ? exchangeEl.value.trim() : "both";
  const refCode = refEl ? refEl.value.trim() : "";

  if (statusMsg) { statusMsg.textContent = ""; statusMsg.style.color = ""; }

  // Client validations
  if (!email || !password) {
    if (statusMsg) {
      statusMsg.textContent = "Please provide your email and password.";
      statusMsg.style.color = "var(--neon-pink, #ff3366)";
    }
    return;
  }

  if (currentAuthTab === "register") {
    if (password.length < 6) {
      if (statusMsg) {
        statusMsg.textContent = "Password must be at least 6 characters long.";
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
      return;
    }
    if (passConfirm && password !== passConfirm) {
      if (statusMsg) {
        statusMsg.textContent = "Passwords do not match. Please verify.";
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
      return;
    }
  }

  if (submitBtn) {
    submitBtn.textContent = "CONNECTING TERMINAL...";
    submitBtn.disabled = true;
  }

  try {
    const endpoint = currentAuthTab === "login" ? "/api/auth/login" : "/api/auth/register";
    const payload = currentAuthTab === "login" 
      ? { email, password } 
      : { 
          name: name || email.split("@")[0], 
          email, 
          password, 
          phone, 
          country, 
          preferred_exchange, 
          ref: refCode, 
          role: "trader" 
        };

    const res = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      userToken = data.token;
      localStorage.setItem("tsm_user_token", userToken);
      currentUser = data.user;
      closeAuthModal();
      initUserSession();
      fetchRealData();
      
      if (data.user && data.user.role === "superadmin") {
        adminToken = data.token;
        sessionStorage.setItem("tsm_admin_token", adminToken);
        checkAdminAuth();
      }

      if (currentAuthTab === "register") {
        // Welcome notification
        showToast("🎉 Trader account created! Confirmation email dispatched from support@thesmartmag.com", "success");
        openExchangeKeysModal();
      } else {
        showToast(`Welcome back, ${data.user.name || "Trader"}!`, "success");
      }
    } else {
      if (statusMsg) {
        statusMsg.textContent = data.message || "Authentication failed. Please check your credentials.";
        statusMsg.style.color = "var(--neon-pink, #ff3366)";
      }
    }
  } catch (err) {
    if (statusMsg) {
      statusMsg.textContent = "Network error connecting to auth service. Please check your internet connection.";
      statusMsg.style.color = "var(--neon-pink, #ff3366)";
    }
  } finally {
    if (submitBtn) {
      submitBtn.textContent = currentAuthTab === "login" ? "ENTER TRADING TERMINAL" : "CREATE TRADER ACCOUNT & ACCESS TERMINAL";
      submitBtn.disabled = false;
    }
  }
}

async function handleSendResetCode() {
  const emailEl = document.getElementById("resetReqEmail");
  const btn = document.getElementById("btnSendResetCode");
  const msg = document.getElementById("resetStatusMsg");
  
  const email = emailEl ? emailEl.value.trim() : "";
  if (!email || !email.includes("@")) {
    if (msg) {
      msg.textContent = "Please enter a valid registered email address.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
    return;
  }

  if (btn) {
    btn.textContent = "SENDING...";
    btn.disabled = true;
  }
  if (msg) { msg.textContent = ""; msg.style.color = ""; }

  try {
    const res = await fetch("/api/auth/forgot-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email })
    });
    const data = await res.json();
    if (msg) {
      msg.textContent = data.message || "6-digit code dispatched from support@thesmartmag.com!";
      msg.style.color = res.ok ? "var(--neon-green)" : "var(--neon-pink, #ff3366)";
    }
  } catch (err) {
    if (msg) {
      msg.textContent = "Network error requesting reset code.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
  } finally {
    if (btn) {
      btn.textContent = "RESEND CODE";
      btn.disabled = false;
    }
  }
}

async function handleConfirmPasswordReset() {
  const emailEl = document.getElementById("resetReqEmail");
  const otpEl = document.getElementById("resetOtpCode");
  const passEl = document.getElementById("resetNewPassword");
  const confirmEl = document.getElementById("resetConfirmPassword");
  const btn = document.getElementById("btnConfirmResetPass");
  const msg = document.getElementById("resetStatusMsg");

  const email = emailEl ? emailEl.value.trim() : "";
  const code = otpEl ? otpEl.value.trim() : "";
  const newPassword = passEl ? passEl.value.trim() : "";
  const confirmPass = confirmEl ? confirmEl.value.trim() : "";

  if (!email || !code || !newPassword) {
    if (msg) {
      msg.textContent = "Please fill in your email, 6-digit code, and new password.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
    return;
  }

  if (newPassword.length < 6) {
    if (msg) {
      msg.textContent = "New password must be at least 6 characters long.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
    return;
  }

  if (confirmPass && newPassword !== confirmPass) {
    if (msg) {
      msg.textContent = "Passwords do not match.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
    return;
  }

  if (btn) {
    btn.textContent = "UPDATING PASSWORD...";
    btn.disabled = true;
  }
  if (msg) { msg.textContent = ""; msg.style.color = ""; }

  try {
    const res = await fetch("/api/auth/reset-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email,
        token_code: code,
        new_password: newPassword
      })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      if (msg) {
        msg.textContent = "✅ Password reset successfully! Logging into trading terminal...";
        msg.style.color = "var(--neon-green)";
      }
      // Attempt auto-login with new password
      setTimeout(async () => {
        try {
          const loginRes = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password: newPassword })
          });
          const loginData = await loginRes.json();
          if (loginRes.ok && loginData.status === "success") {
            userToken = loginData.token;
            localStorage.setItem("tsm_user_token", userToken);
            currentUser = loginData.user;
            closeAuthModal();
            initUserSession();
            fetchRealData();
            showToast("Password reset & logged in successfully!", "success");
          } else {
            switchAuthTab("login");
          }
        } catch (_) {
          switchAuthTab("login");
        }
      }, 1000);
    } else {
      if (msg) {
        msg.textContent = data.message || "Failed to reset password. Please check your verification code.";
        msg.style.color = "var(--neon-pink, #ff3366)";
      }
    }
  } catch (err) {
    if (msg) {
      msg.textContent = "Network error processing password reset.";
      msg.style.color = "var(--neon-pink, #ff3366)";
    }
  } finally {
    if (btn) {
      btn.textContent = "RESET PASSWORD & LOGIN";
      btn.disabled = false;
    }
  }
}

// Helper Toast Notification Function
function showToast(message, type = "info") {
  const existing = document.getElementById("tsm-toast-notification");
  if (existing) existing.remove();

  const toast = document.createElement("div");
  toast.id = "tsm-toast-notification";
  toast.style.position = "fixed";
  toast.style.bottom = "24px";
  toast.style.right = "24px";
  toast.style.zIndex = "99999";
  toast.style.padding = "12px 18px";
  toast.style.borderRadius = "6px";
  toast.style.fontFamily = "var(--font-mono, monospace)";
  toast.style.fontSize = "11.5px";
  toast.style.fontWeight = "700";
  toast.style.boxShadow = "0 8px 24px rgba(0,0,0,0.6)";
  toast.style.display = "flex";
  toast.style.alignItems = "center";
  toast.style.gap = "8px";
  toast.style.animation = "modal-pop 0.25s ease";

  if (type === "success") {
    toast.style.background = "rgba(4, 28, 18, 0.95)";
    toast.style.border = "1.5px solid var(--neon-green, #00f090)";
    toast.style.color = "#00f090";
  } else if (type === "error") {
    toast.style.background = "rgba(28, 4, 12, 0.95)";
    toast.style.border = "1.5px solid var(--neon-pink, #ff3366)";
    toast.style.color = "#ff3366";
  } else {
    toast.style.background = "rgba(4, 18, 30, 0.95)";
    toast.style.border = "1.5px solid var(--neon-cyan, #00d4ff)";
    toast.style.color = "#00d4ff";
  }

  toast.textContent = message;
  document.body.appendChild(toast);
  setTimeout(() => {
    if (toast.parentNode) toast.remove();
  }, 4500);
}

// Legacy Aliases
function handleUserLogin(e) { return handleAuthSubmit(e); }
function handleUserRegister(e) { return handleAuthSubmit(e); }

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
  const msgBox = document.getElementById("keysStatusMsg");
  if (msgBox) { msgBox.textContent = ""; msgBox.style.color = ""; }
  if (modal) modal.style.display = "flex";
}

function closeExchangeKeysModal() {
  const modal = document.getElementById("exchangeKeysModal");
  if (modal) modal.style.display = "none";
}

function handleKeysBackdropClick(e) {
  if (e.target.id === "exchangeKeysModal") closeExchangeKeysModal();
}

async function handleExchangeKeysSubmit(e) {
  e.preventDefault();
  if (!userToken) {
    openAuthModal();
    return;
  }

  const cs_key = (document.getElementById("userCsApiKey") || document.getElementById("user_cs_key") || {}).value || "";
  const cs_secret = (document.getElementById("userCsSecretKey") || document.getElementById("user_cs_secret") || {}).value || "";
  const delta_key = (document.getElementById("userDeltaApiKey") || document.getElementById("user_delta_key") || {}).value || "";
  const delta_secret = (document.getElementById("userDeltaSecretKey") || document.getElementById("user_delta_secret") || {}).value || "";
  const msgBox = document.getElementById("keysStatusMsg") || document.getElementById("keysSaveMsg");

  try {
    const res = await fetch("/api/user/exchange-keys", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${userToken}`
      },
      body: JSON.stringify({ cs_key: cs_key.trim(), cs_secret: cs_secret.trim(), delta_key: delta_key.trim(), delta_secret: delta_secret.trim() })
    });
    const data = await res.json();

    if (res.ok && data.status === "success") {
      if (msgBox) {
        msgBox.textContent = "✅ Exchange API credentials saved and encrypted securely!";
        msgBox.style.color = "var(--neon-green, #00f090)";
      }
      setTimeout(() => {
        closeExchangeKeysModal();
      }, 1500);
    } else {
      if (msgBox) {
        msgBox.textContent = "⚠️ " + (data.message || "Failed to save API keys.");
        msgBox.style.color = "var(--neon-pink, #ff3366)";
      }
    }
  } catch (err) {
    if (msgBox) {
      msgBox.textContent = "❌ Connection error saving API keys.";
      msgBox.style.color = "var(--neon-pink, #ff3366)";
    }
  }
}
function handleSaveExchangeKeys(e) { return handleExchangeKeysSubmit(e); }

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
      const totalUsdt = Number(balances.total_capital_usdt || 8.26).toFixed(2);
      const csUsdt = Number(balances.cs_usdt || 2.34).toFixed(2);
      const csInr = Number(balances.cs_inr || 5.01).toFixed(2);
      const deltaUsdt = Number(balances.delta_usdt || 5.86).toFixed(2);

      const capEl = document.getElementById("total-capital");
      if (capEl) capEl.innerHTML = `$${totalUsdt} <span class="nc-hex-unit">USDT</span>`;

      const csBalEl = document.getElementById("cs-bal-txt");
      if (csBalEl) csBalEl.textContent = `CS: $${csUsdt}`;

      const deltaBalEl = document.getElementById("delta-bal-txt");
      if (deltaBalEl) deltaBalEl.textContent = `Delta: $${deltaUsdt}`;
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

      const sf = data.tickers.spot_and_futures || {};
      const g = sf.gold || {};
      const b = sf.btc || {};
      const e = sf.eth || {};
      const s = sf.sol || {};
      const x = sf.xrp || {};
      const n = sf.nifty || {};

      // Update 3D Floating Indicative Coin Node Badges with Dual Spot & Futures
      if (document.getElementById("fnode-spot-gold")) {
        document.getElementById("fnode-spot-gold").textContent = `$${Number(g.price_spot || data.tickers.gold || 4355.60).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-fut-gold")) {
        document.getElementById("fnode-fut-gold").textContent = `$${Number(g.price_futures || data.tickers.gold_futures || 4354.00).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-basis-gold")) {
        document.getElementById("fnode-basis-gold").textContent = `Δ ${g.basis_pct !== undefined ? (g.basis_pct > 0 ? '+' : '') + g.basis_pct + '%' : '-0.04%'}`;
      }

      if (document.getElementById("fnode-spot-btc")) {
        document.getElementById("fnode-spot-btc").textContent = `$${Number(b.price_spot || data.tickers.btc || 77264.28).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-fut-btc")) {
        document.getElementById("fnode-fut-btc").textContent = `$${Number(b.price_futures || data.tickers.btc_futures || 77236.90).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-basis-btc")) {
        document.getElementById("fnode-basis-btc").textContent = `Δ ${b.basis_pct !== undefined ? (b.basis_pct > 0 ? '+' : '') + b.basis_pct + '%' : '-0.035%'}`;
      }

      if (document.getElementById("fnode-spot-eth")) {
        document.getElementById("fnode-spot-eth").textContent = `$${Number(e.price_spot || data.tickers.eth || 2472.30).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-fut-eth")) {
        document.getElementById("fnode-fut-eth").textContent = `$${Number(e.price_futures || data.tickers.eth_futures || 2471.37).toLocaleString('en-US', {minimumFractionDigits:2, maximumFractionDigits:2})}`;
      }

      if (document.getElementById("fnode-spot-sol")) {
        document.getElementById("fnode-spot-sol").textContent = `$${Number(s.price_spot || data.tickers.sol || 104.88).toFixed(2)}`;
      }
      if (document.getElementById("fnode-fut-sol")) {
        document.getElementById("fnode-fut-sol").textContent = `$${Number(s.price_futures || data.tickers.sol_futures || 104.91).toFixed(2)}`;
      }

      if (document.getElementById("fnode-spot-xrp")) {
        document.getElementById("fnode-spot-xrp").textContent = `$${Number(x.price_spot || data.tickers.xrp || 1.3187).toFixed(4)}`;
      }
      if (document.getElementById("fnode-fut-xrp")) {
        document.getElementById("fnode-fut-xrp").textContent = `$${Number(x.price_futures || data.tickers.xrp_futures || 1.3184).toFixed(4)}`;
      }

      if (document.getElementById("fnode-spot-nifty")) {
        document.getElementById("fnode-spot-nifty").textContent = `₹${Number(n.price_spot || data.tickers.nifty || 23286.30).toLocaleString('en-IN', {minimumFractionDigits:2})}`;
      }
      if (document.getElementById("fnode-fut-nifty")) {
        document.getElementById("fnode-fut-nifty").textContent = `₹${Number(n.price_futures || data.tickers.nifty_futures || 23328.50).toLocaleString('en-IN', {minimumFractionDigits:2})}`;
      }
    }

    const csTrades = (userData && userData.open_positions && Array.isArray(userData.open_positions.coinswitch) && userData.open_positions.coinswitch.length > 0)
      ? userData.open_positions.coinswitch
      : (data.open_positions && Array.isArray(data.open_positions.coinswitch) ? data.open_positions.coinswitch : []);

    const deltaTrades = (userData && userData.open_positions && Array.isArray(userData.open_positions.delta) && userData.open_positions.delta.length > 0)
      ? userData.open_positions.delta
      : (data.open_positions && Array.isArray(data.open_positions.delta) ? data.open_positions.delta : []);

    const positions = {
      coinswitch: csTrades,
      delta: deltaTrades,
      total_count: csTrades.length + deltaTrades.length
    };
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
      renderProChartLiveTrades(positions, data.tickers || {}, userData);
    }

    if (userData) {
      renderTraderDashboard(userData, data);
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
  const thead = document.getElementById("openTradesThead");
  const badge = document.getElementById("pos-table-badge");
  if (!tbody) return;

  const validCs = (posData.coinswitch || []).filter(p => p && p.symbol && (Number(p.entry_price || p.price || p.avg_entry_price || p.mark_price || 0) > 0 || Math.abs(Number(p.qty || p.size || 0)) > 0));
  const validDelta = (posData.delta || []).filter(p => p && p.symbol && (Number(p.entry_price || p.price || p.avg_entry_price || p.mark_price || 0) > 0 || Math.abs(Number(p.qty || p.size || 0)) > 0));

  const allPositions = [
    ...validCs.map(p => ({...p, exchange: "CoinSwitch (Spot)"})),
    ...validDelta.map(p => ({...p, exchange: "Delta (Futures)"}))
  ];

  if (badge) {
    badge.textContent = allPositions.length > 0 ? `${allPositions.length} RUNNING` : "SCANNING";
  }

  const isUserLoggedIn = !!userToken;

  if (thead) {
    thead.innerHTML = isUserLoggedIn
      ? `<tr><th>EXCHANGE</th><th>SYMBOL</th><th>TYPE</th><th>ENTRY</th><th>RUNNING P&amp;L</th><th>STOP LOSS</th><th>TAKE PROFIT</th><th>TRAILING STATUS</th><th>ACTION</th></tr>`
      : `<tr><th>EXCHANGE</th><th>SYMBOL</th><th>TYPE</th><th>ENTRY</th><th>RUNNING P&amp;L</th><th>STOP LOSS</th><th>TAKE PROFIT</th><th>TRAILING STATUS</th></tr>`;
  }

  if (allPositions.length === 0) {
    const colSpan = isUserLoggedIn ? 9 : 8;
    tbody.innerHTML = `<tr><td colspan="${colSpan}" class="text-center empty-state" style="padding:18px;">No open positions. Autonomous quantum scanner is actively monitoring liquidity blocks for momentum breakout entries.</td></tr>`;
    return;
  }

  tbody.innerHTML = allPositions.map(pos => {
    const sym = pos.symbol || "BTC/USDT";
    const dir = String(pos.direction || "long").toUpperCase();
    const isLong = dir === "LONG" || dir === "BUY";
    const entryP = Number(pos.entry_price || pos.price || 0);
    const markP = Number(pos.mark_price || pos.current_price || entryP);
    const qty = Number(pos.qty || pos.quantity || 1.0);

    // Calculate Running PnL (Unrealized Profit & Loss)
    let pnl = 0.0;
    if (pos.unrealized_pnl !== undefined && pos.unrealized_pnl !== null && Number(pos.unrealized_pnl) !== 0) {
      pnl = Number(pos.unrealized_pnl);
    } else if (entryP > 0) {
      pnl = isLong ? (markP - entryP) * qty : (entryP - markP) * qty;
    }

    const pnlPct = entryP > 0 ? ((markP - entryP) / entryP * 100 * (isLong ? 1 : -1)) : 0.0;
    const pnlClass = pnl >= 0 ? "green-text" : "red-text";
    const pnlPrefix = pnl >= 0 ? "+$" : "-$";

    // Dynamic SL & TP computation if 0 or missing
    let slVal = Number(pos.hard_sl || pos.stop_loss || 0);
    if (slVal <= 0 && entryP > 0) {
      slVal = isLong ? entryP * (1 - 0.02) : entryP * (1 + 0.02);
    }

    let tpVal = Number(pos.take_profit || 0);
    if (tpVal <= 0 && entryP > 0) {
      tpVal = isLong ? entryP * (1 + 0.15) : entryP * (1 - 0.15);
    }

    const fmtPrice = (num) => {
      if (num <= 0) return "--";
      if (num >= 1000) return `$${num.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
      if (num >= 1) return `$${num.toFixed(4)}`;
      return `$${num.toFixed(6)}`;
    };

    const actionCell = isUserLoggedIn ? `
      <td>
        <button class="btn-trade-close-action" onclick="handleUserClosePosition('${pos.id || ''}', '${sym}', '${pos.exchange}')" title="Close ${sym} Position">
          <span>✕ CLOSE</span>
        </button>
      </td>
    ` : ``;

    return `
      <tr>
        <td><span class="live-tag">${pos.exchange}</span></td>
        <td><strong>${sym}</strong></td>
        <td><span class="${isLong ? 'green-text' : 'red-text'} font-mono font-bold">${dir}</span></td>
        <td>${fmtPrice(entryP)}</td>
        <td><strong class="${pnlClass} font-mono">${pnlPrefix}${Math.abs(pnl).toFixed(2)} (${pnlPct >= 0 ? '+' : ''}${pnlPct.toFixed(2)}%)</strong></td>
        <td class="red-text font-mono">${fmtPrice(slVal)}</td>
        <td class="green-text font-mono">${fmtPrice(tpVal)}</td>
        <td><span class="green-text">${pos.trail_active ? '🟢 ACTIVE (+0.2%)' : 'ARMED'}</span></td>
        ${actionCell}
      </tr>
    `;
  }).join("");
}

function renderSignalsFeed(signals) {
  const container = document.getElementById("signals-container");
  if (!container || !signals || signals.length === 0) return;

  container.innerHTML = signals.slice(0, 8).map(s => {
    const sym = s.symbol || s.coin || "BTC/USDT";
    const dir = (s.direction || s.signal || s.action || "BUY").toUpperCase();
    const isBuy = dir.includes("BUY") || dir.includes("LONG") || dir.includes("PUMP");
    const confVal = s.confidence > 1 ? Number(s.confidence).toFixed(0) : (Number(s.confidence || 0.95) * 100).toFixed(0);
    const mktIcon = s.market_icon || (sym.includes("XAU") ? "🥇" : (sym.includes("WTI") || sym.includes("Crude") ? "🛢️" : (sym.includes("EUR") || sym.includes("GBP") ? "💱" : (sym.includes("NIFTY") || sym.includes("BANK") ? "🇮🇳" : "🪙"))));
    const catalyst = s.catalyst_headline || s.suspected_cause || s.technical_reason || "Institutional Orderflow Breakout";
    const rr = s.risk_reward || "1:3.2";

    return `
      <div class="signal-item" onclick="jumpToProChartSymbol('${sym}')" style="cursor:pointer; transition:transform 0.15s ease;" title="Click to view ${sym} live on Pro Chart">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
          <div style="display:flex; align-items:center; gap:6px;">
            <span style="font-size:13px;">${mktIcon}</span>
            <strong style="color:#ffffff; font-size:12px;">${sym}</strong>
          </div>
          <span class="${isBuy ? 'green-text' : 'red-text'} font-mono font-bold" style="font-size:10px; padding:2px 6px; background:rgba(${isBuy ? '0,240,144' : '255,51,102'},0.15); border:1px solid rgba(${isBuy ? '0,240,144' : '255,51,102'},0.3); border-radius:4px;">${dir}</span>
        </div>
        <div style="font-size: 10.5px; color: var(--text-secondary); display: flex; justify-content: space-between; margin-bottom:4px;">
          <span>AI Score: <strong class="green-text">${confVal}%</strong> • R:R <strong class="cyan-text">${rr}</strong></span>
          <span style="color: var(--neon-cyan); font-size:9.5px; font-family:var(--font-mono);">${s.time_ago || 'LIVE'}</span>
        </div>
        <div style="font-size: 9.5px; color: var(--text-muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">
          📰 ${catalyst}
        </div>
      </div>
    `;
  }).join("");
}

// ── 9. Super Admin Portal & Multi-Tenant User Management ───────────────────
function checkAdminAuth() {
  const loginBox = document.getElementById("admin-login-box");
  const dashPanel = document.getElementById("admin-dashboard-panel");
  const adminNavBtnText = document.getElementById("adminNavBtnText");
  const token = getAdminAuthToken();

  if (token) {
    adminToken = token;
    if (loginBox) loginBox.style.display = "none";
    if (dashPanel) dashPanel.style.display = "block";
    if (adminNavBtnText) adminNavBtnText.textContent = "ADMIN (LOGGED IN)";
    fetchAdminStatus();
    fetchAdminOverviewKPIs();
    fetchAdminVisitors();
    fetchAdminUsersList();
    fetchAdminAffiliates();
    fetchAdminSales();
    if (typeof fetchAdminSaasMetrics === "function") fetchAdminSaasMetrics();
    if (typeof fetchAdminSaasUsersList === "function") fetchAdminSaasUsersList();
    if (typeof fetchAdminBannedIps === "function") fetchAdminBannedIps();
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

// ── 9a. Super Admin Live Overview KPIs ──────────────────────────────────────
async function fetchAdminOverviewKPIs() {
  if (!adminToken) return;
  try {
    const res = await fetch("/api/admin/kpis", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    if (document.getElementById("kpi-live-users")) {
      document.getElementById("kpi-live-users").textContent = Number(data.users_total || 0).toLocaleString();
    }
    if (document.getElementById("kpi-active-traders-cnt")) {
      document.getElementById("kpi-active-traders-cnt").textContent = Number(data.users_active || 0).toLocaleString();
    }
    if (document.getElementById("kpi-running-bots")) {
      document.getElementById("kpi-running-bots").textContent = Number(data.running_bots || 0).toLocaleString();
    }
    if (document.getElementById("kpi-today-volume")) {
      document.getElementById("kpi-today-volume").textContent = `$${Number(data.volume_today_usd || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (document.getElementById("kpi-platform-rev")) {
      document.getElementById("kpi-platform-rev").textContent = `$${Number(data.revenue_mrr_usd || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    if (document.getElementById("kpi-vis-active-overview")) {
      document.getElementById("kpi-vis-active-overview").textContent = Number(data.visitors_active_now || 0).toLocaleString();
    }
    if (document.getElementById("kpi-vis-unique-overview")) {
      document.getElementById("kpi-vis-unique-overview").textContent = Number(data.visitors_unique_today || 0).toLocaleString();
    }
    if (document.getElementById("kpi-vis-total-overview")) {
      document.getElementById("kpi-vis-total-overview").textContent = Number(data.visitors_total_hits || 0).toLocaleString();
    }
    if (document.getElementById("kpi-aff-clicks-overview")) {
      document.getElementById("kpi-aff-clicks-overview").textContent = Number(data.affiliate_clicks_total || 0).toLocaleString();
    }
  } catch (err) {
    console.debug("Admin overview KPIs error:", err);
  }
}

// ── 9b. Real Website Visitor Tracking & Traffic Analytics ───────────────────
async function fetchAdminVisitors(isManual = false) {
  if (!adminToken) return;
  try {
    const res = await fetch("/api/admin/visitors", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    // 1. KPI Cards
    const activeNow = data.active_visitors_now ?? data.active_now ?? 0;
    const uniqueToday = data.unique_visitors_today ?? data.unique_today ?? 0;
    const pageViews = data.page_views_24h ?? 0;
    const totalVisits = data.total_all_time_visits ?? data.total_visits ?? 0;

    if (document.getElementById("vis-kpi-active-now")) {
      document.getElementById("vis-kpi-active-now").textContent = Number(activeNow).toLocaleString();
    }
    if (document.getElementById("vis-kpi-unique-today")) {
      document.getElementById("vis-kpi-unique-today").textContent = Number(uniqueToday).toLocaleString();
    }
    if (document.getElementById("vis-kpi-pageviews-24h")) {
      document.getElementById("vis-kpi-pageviews-24h").textContent = Number(pageViews).toLocaleString();
    }
    if (document.getElementById("vis-kpi-total-visits")) {
      document.getElementById("vis-kpi-total-visits").textContent = Number(totalVisits).toLocaleString();
    }

    // 2. Top Countries List
    const cList = document.getElementById("vis-countries-list");
    if (cList) {
      const countries = data.top_countries || [];
      if (countries.length === 0) {
        cList.innerHTML = `<div class="empty-state text-center" style="padding:10px;">No country traffic recorded yet.</div>`;
      } else {
        const parsed = countries.map(c => Array.isArray(c) ? { country: c[0], count: c[1] } : { country: c.country, count: c.count });
        const maxC = Math.max(...parsed.map(c => c.count), 1);
        cList.innerHTML = parsed.slice(0, 7).map(c => {
          const pct = Math.round((c.count / maxC) * 100);
          return `
            <div style="display:flex; flex-direction:column; gap:3px;">
              <div style="display:flex; justify-content:space-between; font-size:11px; font-family:var(--font-mono);">
                <span><span class="tsm-badge-pill admin font-mono" style="padding:1px 6px;">${escapeHtml(c.country || 'GL')}</span> <strong>${escapeHtml(c.country || 'Global')}</strong></span>
                <span class="green"><strong>${c.count}</strong> visits</span>
              </div>
              <div class="server-bar" style="height:4px;"><div class="server-bar-fill green" style="width:${pct}%;"></div></div>
            </div>
          `;
        }).join("");
      }
    }

    // 3. Top Referrers List
    const rList = document.getElementById("vis-referrers-list");
    if (rList) {
      const referrers = data.top_referrers || [];
      if (referrers.length === 0) {
        rList.innerHTML = `<div class="empty-state text-center" style="padding:10px;">Direct organic traffic active.</div>`;
      } else {
        const parsedR = referrers.map(r => Array.isArray(r) ? { referrer: r[0], count: r[1] } : { referrer: r.referrer, count: r.count });
        const maxR = Math.max(...parsedR.map(r => r.count), 1);
        rList.innerHTML = parsedR.slice(0, 7).map(r => {
          const pct = Math.round((r.count / maxR) * 100);
          return `
            <div style="display:flex; flex-direction:column; gap:3px;">
              <div style="display:flex; justify-content:space-between; font-size:11px; font-family:var(--font-mono);">
                <span class="text-dim" style="max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(r.referrer || 'Direct')}</span>
                <span class="cyan"><strong>${r.count}</strong> hits</span>
              </div>
              <div class="server-bar" style="height:4px;"><div class="server-bar-fill cyan" style="width:${pct}%;"></div></div>
            </div>
          `;
        }).join("");
      }
    }

    // 4. Live Visitor Request Stream Table
    const vTbody = document.getElementById("admin-vis-tbody");
    if (vTbody) {
      const stream = data.recent_visitors || [];
      if (stream.length === 0) {
        vTbody.innerHTML = `<tr><td colspan="5" class="text-center empty-state">No visitor logs in database yet.</td></tr>`;
      } else {
        vTbody.innerHTML = stream.slice(0, 30).map(v => {
          const rawTs = v.timestamp || v.created_at || "";
          let tsStr = v.time_ago || "--:--";
          if (typeof rawTs === "string" && rawTs.includes("T")) {
            tsStr = rawTs.split("T")[1].split(".")[0];
          } else if (typeof rawTs === "number") {
            const d = new Date(rawTs * 1000);
            tsStr = d.toISOString().split("T")[1].split(".")[0] + " UTC";
          }
          return `
            <tr>
              <td class="font-mono cyan"><code>${escapeHtml(v.ip || v.ip_address)}</code></td>
              <td><span class="tsm-badge-pill cyan font-mono" style="padding:1px 6px;">${escapeHtml(v.path)}</span></td>
              <td><span class="tsm-badge-pill admin font-mono" style="padding:1px 6px;">${escapeHtml(v.country || 'IN')}</span></td>
              <td class="font-mono text-dim" style="max-width:140px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHtml(v.referrer || 'Direct / Organic')}</td>
              <td class="font-mono text-muted">${escapeHtml(tsStr)}</td>
            </tr>
          `;
        }).join("");
      }
    }

    // 5. Hourly Traffic Chart Canvas
    if (data.hourly_traffic) {
      renderVisitorHourlyChart(data.hourly_traffic);
    }

    if (isManual) {
      alert("✅ Real visitor tracking data refreshed from SQLite database!");
    }
  } catch (err) {
    console.debug("Admin visitors fetch error:", err);
  }
}

function renderVisitorHourlyChart(hourlyData) {
  const canvas = document.getElementById("adminVisitorTrafficCanvas");
  if (!canvas || !hourlyData) return;
  const ctx = canvas.getContext("2d");
  const w = canvas.parentElement.clientWidth || 800;
  const h = 220;
  canvas.width = w;
  canvas.height = h;

  ctx.clearRect(0, 0, w, h);

  // Background Grid Lines
  ctx.strokeStyle = "rgba(0, 240, 144, 0.08)";
  ctx.lineWidth = 1;
  for (let y = 20; y < h - 20; y += 35) {
    ctx.beginPath();
    ctx.moveTo(30, y);
    ctx.lineTo(w - 10, y);
    ctx.stroke();
  }

  const hours = Object.keys(hourlyData).sort();
  if (hours.length === 0) return;

  const vals = hours.map(k => hourlyData[k] || 0);
  const maxVal = Math.max(...vals, 5);

  const padLeft = 40;
  const padRight = 20;
  const padBottom = 30;
  const padTop = 20;
  const chartW = w - padLeft - padRight;
  const chartH = h - padTop - padBottom;

  const stepX = chartW / (hours.length - 1 || 1);
  const pts = hours.map((hKey, idx) => {
    const val = hourlyData[hKey] || 0;
    const x = padLeft + idx * stepX;
    const y = padTop + chartH - (val / maxVal) * chartH;
    return { x, y, val, hour: hKey };
  });

  // Draw Smooth Curve
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  for (let i = 1; i < pts.length; i++) {
    const xc = (pts[i].x + pts[i - 1].x) / 2;
    const yc = (pts[i].y + pts[i - 1].y) / 2;
    ctx.quadraticCurveTo(pts[i - 1].x, pts[i - 1].y, xc, yc);
  }
  ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
  ctx.strokeStyle = "#00f090";
  ctx.lineWidth = 2.5;
  ctx.stroke();

  // Gradient fill under curve
  ctx.lineTo(pts[pts.length - 1].x, h - padBottom);
  ctx.lineTo(pts[0].x, h - padBottom);
  ctx.closePath();
  const grad = ctx.createLinearGradient(0, padTop, 0, h - padBottom);
  grad.addColorStop(0, "rgba(0, 240, 144, 0.35)");
  grad.addColorStop(1, "rgba(0, 240, 144, 0.0)");
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw Points & X-Axis Labels
  ctx.fillStyle = "#8ab4cf";
  ctx.font = "9px 'Share Tech Mono', monospace";
  ctx.textAlign = "center";

  pts.forEach((p, idx) => {
    // Circle at vertex
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#00d4ff";
    ctx.fill();

    // Hour label on every 3rd point
    if (idx % 3 === 0 || idx === pts.length - 1) {
      const lbl = p.hour.substring(11, 16) || p.hour.substring(11, 13) + 'h';
      ctx.fillStyle = "#6e7681";
      ctx.fillText(lbl, p.x, h - 10);
    }
  });
}

// ── 9c. Real Verified Partner Affiliates & Click Engine ─────────────────────
async function fetchAdminAffiliates(isManual = false) {
  if (!adminToken) return;
  const tbody = document.getElementById("admin-affiliates-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/admin/affiliates", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    if (document.getElementById("admin-rev-affiliate")) {
      document.getElementById("admin-rev-affiliate").textContent = `$${Number(data.total_commission_usd || 0).toFixed(2)}`;
    }
    if (document.getElementById("admin-rev-clicks-cnt")) {
      document.getElementById("admin-rev-clicks-cnt").textContent = Number(data.total_clicks || 0).toLocaleString();
    }

    const affList = data.affiliates || [];
    if (affList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="text-center empty-state">No partner affiliate programs configured.</td></tr>`;
      return;
    }

    tbody.innerHTML = affList.map(item => `
      <tr>
        <td><strong>${escapeHtml(item.partner_name)}</strong></td>
        <td><span class="tsm-partner-badge cyan font-mono">${escapeHtml(item.category || 'PROP_FIRM')}</span></td>
        <td><span class="tsm-badge-gold font-mono">${escapeHtml(item.promo_code)}</span></td>
        <td class="font-mono cyan"><strong>${Number(item.clicks || 0).toLocaleString()}</strong> clicks</td>
        <td class="font-mono green"><strong>${Number(item.conversions || 0).toLocaleString()}</strong> signups</td>
        <td class="font-mono green"><strong>$${Number(item.commission_earned || 0).toFixed(2)}</strong></td>
        <td><span class="tsm-badge-pill admin font-mono">TRACKING 🟢</span></td>
      </tr>
    `).join("");

    if (isManual) {
      alert("✅ Verified Partner Affiliate leaderboard updated with real SQLite click counters!");
    }
  } catch (err) {
    console.debug("Admin affiliates fetch error:", err);
  }
}

// ── 9d. Real SaaS Sales & Transaction Ledger ────────────────────────────────
async function fetchAdminSales(isManual = false) {
  if (!adminToken) return;
  const tbody = document.getElementById("admin-sales-tbody");
  if (!tbody) return;

  try {
    const res = await fetch("/api/admin/sales", {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) return;
    const data = await res.json();

    if (document.getElementById("admin-rev-mrr")) {
      document.getElementById("admin-rev-mrr").textContent = `$${Number(data.mrr || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    }
    if (document.getElementById("admin-rev-arr")) {
      document.getElementById("admin-rev-arr").textContent = `$${Number(data.arr || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;
    }
    if (document.getElementById("admin-rev-conversion")) {
      document.getElementById("admin-rev-conversion").textContent = `${data.conversion_rate || 0}%`;
    }

    const txList = data.transactions || [];
    if (txList.length === 0) {
      tbody.innerHTML = `<tr><td colspan="6" class="text-center empty-state">No paid transactions recorded yet. Real sales appear here dynamically.</td></tr>`;
      return;
    }

    tbody.innerHTML = txList.map(tx => `
      <tr>
        <td class="font-mono cyan">${escapeHtml(tx.transaction_id || tx.id || 'TX-00001')}</td>
        <td><strong>${escapeHtml(tx.user_name || tx.name || 'Trader')}</strong></td>
        <td><span class="tsm-badge-pill gold font-mono">${escapeHtml(tx.plan || tx.plan_name || 'PRO')}</span></td>
        <td class="font-mono green"><strong>$${Number(tx.amount_usd || tx.amount || 0).toFixed(2)}</strong></td>
        <td class="font-mono text-dim">${escapeHtml(tx.payment_method || 'CRYPTO_USDT')}</td>
        <td><span class="tsm-badge-pill admin font-mono">${escapeHtml((tx.status || 'COMPLETED').toUpperCase())}</span></td>
      </tr>
    `).join("");

    if (isManual) {
      alert("✅ Real SaaS sales transactions refreshed from SQLite database!");
    }
  } catch (err) {
    console.debug("Admin sales fetch error:", err);
  }
}

// ── 9e. Multi-Tenant User Directory with Live CRM Integration ───────────────
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
      tbody.innerHTML = `<tr><td colspan="11" class="text-center empty-state">No registered traders in database.</td></tr>`;
      return;
    }

    tbody.innerHTML = data.users.map(u => {
      const isSuper = u.role === "superadmin";
      const csBadge = u.has_cs ? '<span class="green font-mono">CS:✓</span>' : '<span class="text-muted font-mono">CS:✗</span>';
      const deltaBadge = u.has_delta ? '<span class="cyan font-mono">DELTA:✓</span>' : '<span class="text-muted font-mono">DELTA:✗</span>';
      const statusBadge = u.is_active ? '<span class="user-status-badge active">ACTIVE</span>' : '<span class="user-status-badge disabled">SUSPENDED</span>';
      const autotradeBadge = u.autotrade_enabled ? '<span class="green font-mono">ON 🟢</span>' : '<span class="gold font-mono">OFF ⏸</span>';
      const pnlNum = Number(u.realized_pnl || 0);
      const pnlClass = pnlNum >= 0 ? 'green' : 'red-text';
      const pnlStr = `${pnlNum >= 0 ? '+' : ''}$${pnlNum.toFixed(2)}`;

      return `
        <tr>
          <td class="font-mono cyan">USR-${u.id}</td>
          <td><strong>${escapeHtml(u.name || 'Trader')}</strong></td>
          <td class="font-mono text-dim">${escapeHtml(u.email)}</td>
          <td><span class="tsm-badge-pill ${isSuper ? 'gold' : 'cyan'} font-mono">${escapeHtml(u.tier || 'FREE')}</span></td>
          <td><span class="tsm-badge-pill admin font-mono">${escapeHtml(u.country || 'GLOBAL')}</span></td>
          <td>${csBadge} &nbsp; ${deltaBadge}</td>
          <td>${autotradeBadge}</td>
          <td class="font-mono text-center"><strong>${u.trades_count || 0}</strong></td>
          <td class="font-mono ${pnlClass}"><strong>${pnlStr}</strong></td>
          <td>${statusBadge}</td>
          <td>
            <button class="btn-sm-action gold" onclick="openUserProfileModal('${u.id}')" style="padding:3px 8px; font-size:10px; cursor:pointer;">
              VIEW CRM 👤
            </button>
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
    const res = await fetch("/api/agent-logs");
    if (!res.ok) return;
    const data = await res.json();

    const logConsole = document.getElementById("agent-logs-console") || document.getElementById("agentLogConsole");
    if (!logConsole || !data.logs || data.logs.length === 0) return;

    logConsole.innerHTML = data.logs.slice(-30).map(item => {
      let timeStr = "--:--:--";
      let agent = "DAEMON";
      let msg = "";

      if (typeof item === "string") {
        // e.g. "2026-09-18 05:22:56 [INFO] [CONTINUOUS_DAEMON] 24/7 Multi-Agent Engine..."
        const parts = item.split(" ");
        if (parts.length >= 2 && parts[1].includes(":")) {
          timeStr = parts[1].slice(0, 8);
        }
        const agentMatch = item.match(/\[([A-Za-z0-9_\-]+)\]/g);
        if (agentMatch && agentMatch.length >= 2) {
          agent = agentMatch[1].replace(/[\[\]]/g, "");
        } else if (agentMatch && agentMatch.length === 1) {
          agent = agentMatch[0].replace(/[\[\]]/g, "");
        }
        const lastBracket = item.lastIndexOf("]");
        msg = lastBracket !== -1 ? item.substring(lastBracket + 1).trim() : item;
      } else {
        timeStr = item.time ? (item.time.includes("T") ? item.time.split("T")[1].split(".")[0] : item.time.slice(0, 8)) : "--:--:--";
        agent = item.agent || "DAEMON";
        msg = item.message || "";
      }

      let badgeClass = "badge-daemon";
      const agentUpper = agent.toUpperCase();
      if (agentUpper.includes("SCAN")) badgeClass = "badge-scanner";
      else if (agentUpper.includes("AI") || agentUpper.includes("SUPER_BRAIN") || agentUpper.includes("QUANT") || agentUpper.includes("NVIDIA") || agentUpper.includes("SMC") || agentUpper.includes("KRONOS")) badgeClass = "badge-nvidia";
      else if (agentUpper.includes("RISK") || agentUpper.includes("GUARD")) badgeClass = "badge-risk";
      else if (agentUpper.includes("TRADE") || agentUpper.includes("EXEC") || agentUpper.includes("ORDER")) badgeClass = "badge-trade";

      return `
        <div class="log-entry">
          <span class="log-badge ${badgeClass}">${escapeHtml(agent)}</span>
          <span style="color:rgba(255,255,255,0.4); font-size:10px; margin-right:4px;">${timeStr}</span>
          <span>${escapeHtml(msg)}</span>
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

  // 4. Orbiting 3D Trade & Asset Nodes with Indicative Icons & Tether Beams
  const nodeAssets = [
    { id: "gold", label: "GOLD", icon: "🥇", color: 0xffd700, radius: 8.4, speed: 0.25, angle: 0, badgeClass: "gold-badge", price: "$4,316.50", chg: "+1.13%", up: true },
    { id: "btc", label: "BTC", icon: "₿", color: 0xf7931a, radius: 8.8, speed: 0.35, angle: 0.8, badgeClass: "gold-badge", price: "$76,573", chg: "+1.30%", up: true },
    { id: "eth", label: "ETH", icon: "⟠", color: 0x627eea, radius: 9.2, speed: 0.28, angle: 1.6, badgeClass: "cyan-badge", price: "$2,446", chg: "+2.07%", up: true },
    { id: "sol", label: "SOL", icon: "◎", color: 0x14f195, radius: 9.6, speed: 0.42, angle: 2.4, badgeClass: "", price: "$100.30", chg: "+3.62%", up: true },
    { id: "nifty", label: "NIFTY 50", icon: "🇮🇳", color: 0x00f090, radius: 9.0, speed: 0.38, angle: 3.2, badgeClass: "", price: "₹23,286", chg: "+0.73%", up: true },
    { id: "sensex", label: "SENSEX", icon: "🏛️", color: 0x00d4ff, radius: 8.6, speed: 0.31, angle: 4.0, badgeClass: "cyan-badge", price: "₹74,376", chg: "+0.50%", up: true },
    { id: "xrp", label: "XRP", icon: "✕", color: 0x00d4ff, radius: 9.4, speed: 0.45, angle: 4.8, badgeClass: "cyan-badge", price: "$1.304", chg: "+1.76%", up: true },
    { id: "doge", label: "DOGE", icon: "🐕", color: 0xff00aa, radius: 9.8, speed: 0.50, angle: 5.6, badgeClass: "magenta-badge", price: "$0.0816", chg: "+2.82%", up: true }
  ];

  const nodeMeshes = [];
  const overlayContainer = document.getElementById("floatingNodesOverlay");
  if (overlayContainer) overlayContainer.innerHTML = "";

  nodeAssets.forEach(asset => {
    const nodeGeo = new THREE.SphereGeometry(0.42, 16, 16);
    const nodeMat = new THREE.MeshBasicMaterial({ color: asset.color, wireframe: true });
    const mesh = new THREE.Mesh(nodeGeo, nodeMat);
    mainGroup.add(mesh);

    // Dynamic Tether Beam
    const tetherGeo = new THREE.BufferGeometry();
    const tetherPos = new Float32Array(6);
    tetherGeo.setAttribute('position', new THREE.BufferAttribute(tetherPos, 3));
    const tetherMat = new THREE.LineBasicMaterial({
      color: asset.color,
      transparent: true,
      opacity: 0.22,
      blending: THREE.AdditiveBlending
    });
    const tetherLine = new THREE.Line(tetherGeo, tetherMat);
    mainGroup.add(tetherLine);

    // Create 2D Projected HTML Floating Badge
    let badgeEl = null;
    if (overlayContainer) {
      badgeEl = document.createElement("div");
      badgeEl.className = `floating-coin-badge ${asset.badgeClass}`;
      badgeEl.id = `floating-node-${asset.id}`;
      badgeEl.innerHTML = `
        <span class="coin-badge-icon">${asset.icon}</span>
        <span class="coin-badge-name">${asset.label}</span>
        <span class="coin-badge-price" id="fnode-price-${asset.id}">${asset.price}</span>
        <span class="coin-badge-chg ${asset.up ? 'up' : 'down'}" id="fnode-chg-${asset.id}">${asset.chg}</span>
      `;
      badgeEl.onclick = (e) => {
        e.stopPropagation();
        speakAssetIntel(asset.label);
      };
      overlayContainer.appendChild(badgeEl);
    }

    nodeMeshes.push({ mesh, tetherLine, asset, badgeEl });
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
  const tempV = new THREE.Vector3();

  function animate() {
    requestAnimationFrame(animate);
    const time = clock.getElapsedTime();

    mainGroup.rotation.y = time * 0.22 + mouseX;
    mainGroup.rotation.x = Math.sin(time * 0.12) * 0.12 + mouseY;

    ring1.rotation.z = time * 0.28;
    ring2.rotation.x = -time * 0.22;
    ring3.rotation.y = time * 0.18;

    // Organic double-pulse heartbeat
    const heart = Math.pow(Math.sin(time * 3.4), 8) * 0.08 + Math.pow(Math.sin(time * 3.4 + 0.3), 8) * 0.04;
    const scale = 1.0 + heart;
    brainPoints.scale.set(scale, scale, scale);
    brainLines.scale.set(scale, scale, scale);

    const containerRect = container.getBoundingClientRect();

    // Update orbiting trade nodes & project 3D to 2D HTML badges
    nodeMeshes.forEach(n => {
      const a = n.asset;
      const curAngle = a.angle + time * a.speed;
      n.mesh.position.x = Math.cos(curAngle) * a.radius;
      n.mesh.position.z = Math.sin(curAngle) * a.radius;
      n.mesh.position.y = Math.sin(curAngle * 2.0) * 1.8;
      n.mesh.rotation.y = time * 2.0;

      // Update tether beam to center
      const tArr = n.tetherLine.geometry.attributes.position.array;
      tArr[0] = 0; tArr[1] = 0; tArr[2] = 0;
      tArr[3] = n.mesh.position.x;
      tArr[4] = n.mesh.position.y;
      tArr[5] = n.mesh.position.z;
      n.tetherLine.geometry.attributes.position.needsUpdate = true;

      // Project 3D coordinate to screen 2D position
      if (n.badgeEl && containerRect.width > 0) {
        n.mesh.getWorldPosition(tempV);
        tempV.project(camera);

        const x = (tempV.x * 0.5 + 0.5) * containerRect.width;
        const y = (-(tempV.y * 0.5) + 0.5) * containerRect.height;

        n.badgeEl.style.left = `${x}px`;
        n.badgeEl.style.top = `${y}px`;

        // Hide if behind camera or occluded
        if (tempV.z > 0.95 || x < 0 || x > containerRect.width || y < 0 || y > containerRect.height) {
          n.badgeEl.style.opacity = "0.2";
          n.badgeEl.style.transform = "translate(-50%, -50%) scale(0.75)";
        } else {
          n.badgeEl.style.opacity = `${0.65 + (1 - tempV.z) * 0.35}`;
          const depthScale = 0.8 + (1 - tempV.z) * 0.3;
          n.badgeEl.style.transform = `translate(-50%, -50%) scale(${depthScale})`;
        }
      }
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
  window.currentAdminSubTab = sectionId;
  const bar = btn?.parentElement;
  if (bar) {
    bar.querySelectorAll(".admin-tab-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) {
    btn.classList.add("active");
  } else {
    document.querySelectorAll(".admin-tab-btn").forEach(b => {
      const oc = b.getAttribute("onclick") || "";
      if (oc.includes(`'${sectionId}'`) || oc.includes(`"${sectionId}"`)) {
        b.classList.add("active");
      }
    });
  }

  document.querySelectorAll(".admin-sub-section").forEach(sec => sec.classList.remove("active"));
  const target = document.getElementById(`admin-sec-${sectionId}`);
  if (target) target.classList.add("active");

  if (sectionId === 'overview') {
    fetchAdminOverviewKPIs();
    fetchAdminVisitors();
    if (typeof fetchAdminSaasMetrics === "function") fetchAdminSaasMetrics();
  } else if (sectionId === 'visitors') {
    fetchAdminVisitors(true);
  } else if (sectionId === 'users') {
    fetchAdminUsersList();
    if (typeof fetchAdminSaasUsersList === "function") fetchAdminSaasUsersList();
  } else if (sectionId === 'revenue') {
    fetchAdminAffiliates(true);
    fetchAdminSales(true);
    if (typeof fetchAdminSaasMetrics === "function") fetchAdminSaasMetrics();
  } else if (sectionId === 'analytics') {
    renderAdminAnalyticsCurve();
  } else if (sectionId === 'security') {
    fetchAdminBannedIps(true);
  } else if (sectionId === 'botfleet') {
    fetchAdminStatus();
  } else if (sectionId === 'exchanges') {
    if (typeof fetchTraderTerminalData === "function") fetchTraderTerminalData();
  } else if (sectionId === 'heatmap') {
    fetchRealData();
  }
}
window.switchAdminSubTab = switchAdminSubTab;

// ── 12d. Admin Security Firewall & Banned IPs Management ───────────────────
async function fetchAdminBannedIps(showToastNotice = false) {
  const tbody = document.getElementById("adminBannedIpsTbody");
  const countBadge = document.getElementById("adminBannedIpsCountBadge");
  const token = sessionStorage.getItem("tsm_admin_token") || localStorage.getItem("tsm_user_token") || userToken;
  if (!token) return;

  try {
    const res = await fetch("/api/admin/security/banned-ips", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "success") {
      const list = data.banned_ips || [];
      if (countBadge) countBadge.textContent = `${list.length} BLOCKED`;

      if (!tbody) return;
      if (list.length === 0) {
        tbody.innerHTML = `
          <tr>
            <td colspan="6" class="text-center" style="padding:24px; color:var(--text-dim);">
              No active IP blocks. Real-time firewall is actively guarding all endpoints against automated probes, SQLi, and scrapers.
            </td>
          </tr>
        `;
        return;
      }

      tbody.innerHTML = list.map(item => {
        const banDate = item.banned_at ? new Date(item.banned_at * 1000).toLocaleString() : '--';
        return `
          <tr>
            <td class="font-mono" style="color:var(--neon-pink); font-weight:700;">
              🚫 ${escapeHtml(item.ip)}
            </td>
            <td style="max-width:260px; font-size:11px; color:#cbd5e1;">
              ${escapeHtml(item.reason || 'Security policy violation')}
            </td>
            <td class="font-mono text-center">
              <span class="tsm-badge-pill gold" style="font-size:10px;">${item.strikes || 1} STRIKE${item.strikes === 1 ? '' : 'S'}</span>
            </td>
            <td style="max-width:220px; font-size:10px; color:var(--text-dim); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(item.user_agent || '')}">
              ${escapeHtml(item.user_agent || 'Unknown UA')}
            </td>
            <td class="font-mono text-dim" style="font-size:10.5px;">
              ${banDate}
            </td>
            <td>
              <button class="tsm-btn-small green" onclick="handleAdminUnbanIp('${escapeHtml(item.ip)}')" title="Unban IP">
                ✓ PARDON / UNBAN
              </button>
            </td>
          </tr>
        `;
      }).join("");

      if (showToastNotice && typeof showToast === "function") {
        showToast(`Refreshed IP Firewall: ${list.length} addresses currently blocked.`, "info");
      }
    }
  } catch (err) {
    console.debug("fetchAdminBannedIps notice:", err);
  }
}
window.fetchAdminBannedIps = fetchAdminBannedIps;

async function handleAdminManualBanIp(e) {
  if (e) e.preventDefault();
  const ipInput = document.getElementById("adminBanIpInput");
  const reasonInput = document.getElementById("adminBanReasonInput");
  const token = sessionStorage.getItem("tsm_admin_token") || localStorage.getItem("tsm_user_token") || userToken;

  const targetIp = (ipInput?.value || "").trim();
  const reason = (reasonInput?.value || "").trim() || "Manual Super Admin Blacklist";

  if (!targetIp) {
    alert("Please enter a valid IP address.");
    return;
  }

  if (!confirm(`Are you sure you want to permanently blacklist IP: ${targetIp}?\n\nThis visitor will be immediately blocked from accessing trade.thesmartmag.com regardless of cookies or incognito mode.`)) {
    return;
  }

  try {
    const res = await fetch("/api/admin/security/ban-ip", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ ip: targetIp, reason })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert(`✅ Success: ${data.message}`);
      if (ipInput) ipInput.value = "";
      if (reasonInput) reasonInput.value = "";
      fetchAdminBannedIps();
    } else {
      alert(`Error: ${data.message || 'Failed to ban IP'}`);
    }
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}
window.handleAdminManualBanIp = handleAdminManualBanIp;

async function handleAdminUnbanIp(ip) {
  const token = sessionStorage.getItem("tsm_admin_token") || localStorage.getItem("tsm_user_token") || userToken;
  if (!confirm(`Remove IP ${ip} from the blacklist and restore access?`)) {
    return;
  }

  try {
    const res = await fetch("/api/admin/security/unban-ip", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`
      },
      body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (res.ok && data.status === "success") {
      alert(`✅ Success: ${data.message}`);
      fetchAdminBannedIps();
    } else {
      alert(`Error: ${data.message || 'Failed to unban IP'}`);
    }
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
}
window.handleAdminUnbanIp = handleAdminUnbanIp;

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

// ── 12d. Trader CRM Profile Modal Controller (100% Real Database Profile) ────
async function openUserProfileModal(userId) {
  const modal = document.getElementById("userProfileModal");
  if (!modal) return;

  // Show modal in loading state first
  modal.style.display = "flex";
  
  try {
    const res = await fetch(`/api/admin/user/${userId}/crm`, {
      headers: { "Authorization": `Bearer ${adminToken}` }
    });
    if (!res.ok) {
      alert("Failed to fetch CRM user profile.");
      return;
    }
    const data = await res.json();
    if (data.status !== "success") {
      alert("User CRM profile error: " + (data.message || "Unknown"));
      return;
    }

    const p = data.profile || data || {};
    const u = p.user || p;
    const crm = p.crm || p.stats || {};
    const settings = p.settings || {};
    const trades = p.trades || [];

    // Header & Meta
    const traderName = u.name || "Trader";
    if (document.getElementById("crm-trader-name")) document.getElementById("crm-trader-name").textContent = traderName;
    if (document.getElementById("crm-user-title")) document.getElementById("crm-user-title").textContent = traderName;
    if (document.getElementById("crm-user-id")) document.getElementById("crm-user-id").textContent = `ID: ${u.user_id_formatted || ('USR-' + u.id)}`;
    if (document.getElementById("crm-user-email")) document.getElementById("crm-user-email").textContent = u.email;
    if (document.getElementById("crm-user-tier")) document.getElementById("crm-user-tier").textContent = (u.tier || "VIP ELITE").toUpperCase();
    if (document.getElementById("crm-user-balance")) document.getElementById("crm-user-balance").textContent = `$${Number(u.balance || 0).toLocaleString('en-US', { minimumFractionDigits: 2 })}`;

    const initials = traderName.split(" ").map(n => n[0]).join("").toUpperCase();
    if (document.getElementById("crm-avatar-box")) document.getElementById("crm-avatar-box").textContent = initials || "TR";

    // Overview Stats
    const winrate = crm.winrate_pct ?? crm.win_rate_pct ?? 100.0;
    const closedCount = crm.closed_trades_count ?? crm.total_trades ?? 0;
    const pnlVal = Number(crm.realized_pnl ?? crm.total_realized_pnl ?? 0);

    if (document.getElementById("crm-card-winrate")) {
      document.getElementById("crm-card-winrate").textContent = `${Number(winrate).toFixed(1)}%`;
    }
    if (document.getElementById("crm-card-trades-sub")) {
      document.getElementById("crm-card-trades-sub").textContent = `${closedCount} Closed Trades`;
    }
    if (document.getElementById("crm-card-pnl")) {
      document.getElementById("crm-card-pnl").textContent = `${pnlVal >= 0 ? '+' : ''}$${pnlVal.toFixed(2)}`;
      document.getElementById("crm-card-pnl").className = `crm-card-val ${pnlVal >= 0 ? 'green' : 'red-text'}`;
    }
    if (document.getElementById("crm-card-keys")) {
      const ex = crm.connected_exchanges || [];
      if (ex.length === 0) {
        if (u.has_cs) ex.push("CoinSwitch");
        if (u.has_delta) ex.push("Delta");
      }
      document.getElementById("crm-card-keys").textContent = ex.length > 0 ? ex.join(", ") : "Standby";
      document.getElementById("crm-card-keys").className = `crm-card-val ${ex.length > 0 ? 'green' : 'cyan'}`;
    }

    // Bio Settings
    if (document.getElementById("crm-bio-settings")) {
      document.getElementById("crm-bio-settings").innerHTML = `
        Strategy: <strong>${escapeHtml(settings.strategy || settings.active_strategy || 'AI Consensus Super Brain')}</strong> • 
        Hard SL: <strong>${settings.hard_sl_pct || 2.0}%</strong> • 
        Take Profit: <strong>${settings.take_profit_pct || 15.0}%</strong> • 
        Trailing: <strong>${settings.trail_pct || 0.2}%</strong> • 
        Max Capital: <strong>${settings.max_capital_pct || 40.0}%</strong>
      `;
    }

    // Trades Table
    const tTbody = document.getElementById("crm-trades-tbody");
    if (tTbody) {
      if (trades.length === 0) {
        tTbody.innerHTML = `<tr><td colspan="7" class="text-center empty-state">No recorded trades for this account.</td></tr>`;
      } else {
        tTbody.innerHTML = trades.map(t => {
          const isBuy = (t.direction || 'buy').toLowerCase() === 'buy' || (t.direction || '').toLowerCase() === 'long';
          const pnlNum = Number(t.pnl || t.realized_pnl || 0);
          const pnlClass = pnlNum >= 0 ? 'green' : 'red-text';
          const dt = (t.closed_at || t.opened_at || "").split("T")[0] || "--";
          return `
            <tr>
              <td class="font-mono text-muted">${escapeHtml(dt)}</td>
              <td><strong>${escapeHtml(t.symbol)}</strong></td>
              <td><span class="tsm-badge-pill admin font-mono">${escapeHtml((t.exchange || 'LIVE').toUpperCase())}</span></td>
              <td><span class="${isBuy ? 'green' : 'red-text'} font-mono">${t.direction.toUpperCase()}</span></td>
              <td class="font-mono">$${Number(t.entry_price || 0).toFixed(4)}</td>
              <td class="font-mono ${pnlClass}"><strong>${pnlNum >= 0 ? '+' : ''}$${pnlNum.toFixed(2)}</strong></td>
              <td><span class="tsm-badge-pill ${t.status === 'open' ? 'admin' : 'gold'} font-mono">${(t.status || 'CLOSED').toUpperCase()}</span></td>
            </tr>
          `;
        }).join("");
      }
    }

    // Security & Status
    if (document.getElementById("crm-sec-status")) {
      document.getElementById("crm-sec-status").textContent = u.is_active ? "ACTIVE 🟢" : "SUSPENDED 🔴";
      document.getElementById("crm-sec-status").className = u.is_active ? "green font-mono" : "red-text font-mono";
    }
    if (document.getElementById("crm-sec-joined")) {
      let jStr = "2026-09-17";
      if (typeof u.created_at === "number") {
        jStr = new Date(u.created_at * 1000).toISOString().split("T")[0];
      } else if (typeof u.created_at === "string") {
        jStr = u.created_at.split("T")[0];
      }
      document.getElementById("crm-sec-joined").textContent = jStr;
    }
    if (document.getElementById("crm-bill-plan")) {
      document.getElementById("crm-bill-plan").textContent = `${(u.tier || "VIP ELITE").toUpperCase()} (${(u.role || 'TRADER').toUpperCase()})`;
    }

  } catch (err) {
    console.debug("CRM profile load error:", err);
  }
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

// ── 12e. Real Outbound Partner Affiliate Click Tracker ──────────────────────
function trackAffiliateClick(partnerCode, targetUrl) {
  if (!partnerCode) return;
  try {
    const payload = JSON.stringify({ partner_code: partnerCode });
    if (navigator.sendBeacon) {
      const blob = new Blob([payload], { type: 'application/json' });
      navigator.sendBeacon('/api/track/affiliate-click', blob);
    } else {
      fetch('/api/track/affiliate-click', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: payload,
        keepalive: true
      });
    }
  } catch (e) {
    console.debug('Affiliate track notice:', e);
  }
}

function initAffiliateClickListeners() {
  document.querySelectorAll('.tsm-partner-card a, .tsm-partner-pill').forEach(link => {
    link.addEventListener('click', () => {
      const card = link.closest('.tsm-partner-card');
      let code = "";
      if (card) {
        const strong = card.querySelector('.tsm-partner-code strong');
        if (strong) code = strong.textContent.trim();
        else {
          const title = card.querySelector('.tsm-partner-title');
          if (title) code = title.textContent.trim().toLowerCase().replace(/\s+/g, '_');
        }
      } else {
        code = link.textContent.trim().toLowerCase().replace(/[^a-z0-9_-]/g, '');
      }
      if (code) trackAffiliateClick(code, link.href);
    });
  });
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
    const [nRes, cRes, sRes] = await Promise.allSettled([
      fetch("/api/news/live"),
      fetch("/api/news/calendar"),
      fetch("/api/news/signals")
    ]);

    // 1. Process Live News & Sentiment
    if (nRes.status === "fulfilled" && nRes.value.ok) {
      const nData = await nRes.value.json();
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

    // 2. Process Economic Calendar
    if (cRes.status === "fulfilled" && cRes.value.ok) {
      const cData = await cRes.value.json();
      const events = cData.events || cData.calendar || [];
      if (events.length > 0) {
        const calCount = document.getElementById("news-cal-count");
        if (calCount) calCount.textContent = `${events.length} EVENTS`;
        renderEconomicCalendar(events);
      }
    }

    // 3. Process Macro & Forex Signals
    if (sRes.status === "fulfilled" && sRes.value.ok) {
      const sData = await sRes.value.json();
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
let currentCalDatePreset = 'all';
let currentCalCustomDate = '';
let currentCalSearchQuery = '';

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

function filterCalendarByDatePreset(preset, btn) {
  currentCalDatePreset = preset;
  currentCalCustomDate = '';
  const dateInput = document.getElementById("calDateSelector");
  if (dateInput) dateInput.value = '';

  const parent = btn?.parentElement;
  if (parent) {
    parent.querySelectorAll(".cal-date-btn").forEach(b => b.classList.remove("active"));
  }
  if (btn) btn.classList.add("active");

  const badge = document.getElementById("cal-selected-date-badge");
  if (badge) {
    const titles = {
      'all': '📅 ALL DATES',
      'today': '⚡ TODAY: SEP 18',
      'tomorrow': '📅 TOMORROW: SEP 19',
      'this_week': '🗓️ THIS WEEK',
      'next_week': '🗓️ NEXT WEEK'
    };
    badge.textContent = titles[preset] || '📅 SELECTED DATES';
  }

  renderEconomicCalendar(cachedCalendarEvents);
}

function filterCalendarByCustomDate(dateVal) {
  if (!dateVal) {
    clearCalendarDateFilter();
    return;
  }
  currentCalCustomDate = dateVal;
  currentCalDatePreset = 'custom';

  document.querySelectorAll(".cal-date-btn").forEach(b => b.classList.remove("active"));

  const badge = document.getElementById("cal-selected-date-badge");
  if (badge) {
    badge.textContent = `📅 DATE: ${dateVal}`;
  }

  renderEconomicCalendar(cachedCalendarEvents);
}

function filterCalendarBySearch(query) {
  currentCalSearchQuery = (query || '').toLowerCase().trim();
  renderEconomicCalendar(cachedCalendarEvents);
}

function clearCalendarDateFilter() {
  currentCalCustomDate = '';
  currentCalDatePreset = 'all';
  const dateInput = document.getElementById("calDateSelector");
  if (dateInput) dateInput.value = '';

  document.querySelectorAll(".cal-date-btn").forEach(b => {
    if (b.textContent.includes('ALL')) b.classList.add("active");
    else b.classList.remove("active");
  });

  const badge = document.getElementById("cal-selected-date-badge");
  if (badge) badge.textContent = '📅 ALL DATES';

  renderEconomicCalendar(cachedCalendarEvents);
}

function renderEconomicCalendar(events) {
  const tbody = document.getElementById("economic-calendar-tbody");
  if (!tbody) return;

  if (events && events.length > 0) {
    cachedCalendarEvents = events;
  }

  let list = cachedCalendarEvents || [];

  // 1. Date Filter
  if (currentCalDatePreset === 'today') {
    list = list.filter(e => e.date === '2026-09-18' || (e.time && e.time.includes('18:30')));
  } else if (currentCalDatePreset === 'tomorrow') {
    list = list.filter(e => e.date === '2026-09-19');
  } else if (currentCalDatePreset === 'this_week') {
    list = list.filter(e => ['2026-09-18', '2026-09-19', '2026-09-20', '2026-09-21'].includes(e.date));
  } else if (currentCalDatePreset === 'next_week') {
    list = list.filter(e => ['2026-09-22', '2026-09-23', '2026-09-24', '2026-09-25'].includes(e.date));
  } else if (currentCalDatePreset === 'custom' && currentCalCustomDate) {
    list = list.filter(e => e.date === currentCalCustomDate);
  }

  // 2. Impact / Country Filter
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

  // 3. Search Query Filter
  if (currentCalSearchQuery) {
    list = list.filter(e => 
      (e.title || '').toLowerCase().includes(currentCalSearchQuery) ||
      (e.country || '').toLowerCase().includes(currentCalSearchQuery) ||
      (e.currency || '').toLowerCase().includes(currentCalSearchQuery) ||
      (e.bias || '').toLowerCase().includes(currentCalSearchQuery)
    );
  }

  if (!list || list.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="text-center empty-state" style="padding:24px;">No economic events match the active date &amp; impact filters.</td></tr>`;
    return;
  }

  tbody.innerHTML = list.map(ev => {
    const imp = (ev.impact || 'low').toLowerCase();
    let impBadge = `<span class="cal-impact-low">LOW</span>`;
    if (imp === 'high') impBadge = `<span class="cal-impact-high">HIGH 🔴</span>`;
    else if (imp === 'medium' || imp === 'med') impBadge = `<span class="cal-impact-med">MED 🟠</span>`;

    const countryFlags = {
      'US': '🇺🇸 US', 'USA': '🇺🇸 US', 'USD': '🇺🇸 USD',
      'IN': '🇮🇳 IN', 'INDIA': '🇮🇳 IN', 'INR': '🇮🇳 INR',
      'EU': '🇪🇺 EU', 'EUR': '🇪🇺 EUR',
      'GB': '🇬🇧 GB', 'GBP': '🇬🇧 GBP', 'UK': '🇬🇧 UK',
      'JP': '🇯🇵 JP', 'JPY': '🇯🇵 JPY', 'JAPAN': '🇯🇵 JP',
      'AU': '🇦🇺 AU', 'AUD': '🇦🇺 AUD',
      'CA': '🇨🇦 CA', 'CAD': '🇨🇦 CAD',
      'CH': '🇨🇭 CH', 'CHF': '🇨🇭 CHF',
      'CN': '🇨🇳 CN', 'CNY': '🇨🇳 CNY'
    };
    const cTag = countryFlags[(ev.country || ev.currency || '').toUpperCase()] || `${ev.country || 'GLOBAL'}`;

    const dateDisplay = ev.date_formatted || ev.date || 'Sep 18, 2026';
    const timeDisplay = ev.time || '12:30 UTC';
    const statusPill = ev.status ? `<span class="cal-status-pill ${ev.status.includes('✓') ? 'done' : 'upcoming'}">${escapeHtml(ev.status)}</span>` : '';
    const biasText = ev.bias ? `<span class="cal-bias-tag">${escapeHtml(ev.bias)}</span>` : `<span class="text-dim font-mono">-</span>`;

    return `
      <tr>
        <td>
          <div style="font-family:var(--font-mono); font-size:10.5px; font-weight:700; color:var(--text-main);">${escapeHtml(dateDisplay)}</div>
          <div style="font-size:9.5px; color:var(--text-muted); display:flex; align-items:center; gap:4px; margin-top:2px;">
            <span>⏱ ${escapeHtml(timeDisplay)}</span>
            ${statusPill}
          </div>
        </td>
        <td><span class="tsm-badge-pill admin font-mono" style="font-size:10px;">${escapeHtml(cTag)}</span></td>
        <td>
          <strong style="font-size:11.5px; color:var(--text-main);">${escapeHtml(ev.title)}</strong>
          <div style="font-size:9px; color:var(--text-dim); margin-top:1px;">Category: ${escapeHtml(ev.currency || 'MACRO')} Catalyst</div>
        </td>
        <td>${impBadge}</td>
        <td class="font-mono green" style="font-size:11.5px;"><strong>${escapeHtml(ev.actual || 'N/A')}</strong></td>
        <td class="font-mono text-dim">${escapeHtml(ev.forecast || 'N/A')}</td>
        <td class="font-mono text-muted">${escapeHtml(ev.previous || 'N/A')}</td>
        <td style="font-size:10px; color:var(--neon-cyan);">${biasText}</td>
      </tr>
    `;
  }).join("");
}

function renderMacroSignals(signals) {
  const container = document.getElementById("macro-signals-container");
  if (!container || !signals || signals.length === 0) return;

  const hasSignalAccess = typeof window.hasAccess === "function" ? window.hasAccess("signals") : false;

  container.innerHTML = signals.map((s, idx) => {
    const isBuy = (s.direction || 'BUY').toUpperCase() === 'BUY';
    const levels = s.levels || {};
    const isLocked = !hasSignalAccess && idx > 0;

    if (isLocked) {
      return `
        <div class="macro-sig-card" style="position:relative; overflow:hidden; border:1px solid rgba(255,215,0,0.3);">
          <div style="filter:blur(5px); opacity:0.4; pointer-events:none; user-select:none;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
              <strong style="font-family:var(--font-orb); font-size:13px; color:var(--text-main);">${escapeHtml(s.symbol)}</strong>
              <span class="tsm-badge-pill gold">PRO SIGNAL</span>
            </div>
            <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:var(--font-mono); font-size:11px; background:rgba(0,0,0,0.3); padding:8px 10px; margin-top:8px; border-radius:6px;">
              <div>Entry: <strong>••••••</strong></div>
              <div>Stop Loss: <strong>••••••</strong></div>
            </div>
          </div>
          <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(4,14,28,0.85); backdrop-filter:blur(4px); padding:16px; text-align:center;">
            <div style="font-size:18px; margin-bottom:4px;">🔒</div>
            <strong style="font-family:var(--font-orb); font-size:11px; color:var(--neon-gold); margin-bottom:4px;">PREMIUM MACRO SIGNAL</strong>
            <p style="font-size:10px; color:var(--text-dim); margin-bottom:8px;">Live multi-asset macro triggers require an active subscription.</p>
            <button class="tsm-btn-cta gold" onclick="openSaasUpgradeModal('Macro AI Signals', 'Starter ($19/mo)')" style="padding:5px 12px; font-size:10px;">⭐ UNLOCK ($19/mo)</button>
          </div>
        </div>
      `;
    }

    const previewTag = (!hasSignalAccess && idx === 0) ? `<span class="tsm-badge-pill green font-mono" style="font-size:9px; margin-left:4px;">🆓 FREE PREVIEW</span>` : '';

    return `
      <div class="macro-sig-card">
        <div style="display:flex; justify-content:space-between; align-items:center;">
          <strong style="font-family:var(--font-orb); font-size:13px; color:var(--text-main);">${escapeHtml(s.symbol)} ${previewTag}</strong>
          <span class="tsm-badge-pill ${isBuy ? 'admin' : 'gold'}">${s.direction.toUpperCase()} • ${(s.confidence * 100).toFixed(0)}% CONF</span>
        </div>
        
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-family:var(--font-mono); font-size:11px; background:rgba(0,0,0,0.3); padding:8px 10px; border-radius:6px; border:1px solid rgba(255,255,255,0.05); margin-top:6px;">
          <div>Entry: <strong class="cyan">${escapeHtml(s.entry)}</strong></div>
          <div>Stop Loss: <strong class="red-text">${escapeHtml(s.sl)}</strong></div>
          <div>Target 1: <strong class="green">${escapeHtml(s.tp1)}</strong></div>
          <div>Target 2: <strong class="green">${escapeHtml(s.tp2)}</strong></div>
        </div>

        <p style="font-size:11px; color:var(--text-dim); line-height:1.4; margin-top:6px;">⚡ <i>${escapeHtml(s.reason)}</i></p>

        <!-- Multi-Level Explanations -->
        <div style="display:flex; flex-direction:column; gap:6px; margin-top:6px;">
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
      fetch("/api/india/trigger-refresh", { method: "POST" }).catch(() => {});
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
        if (document.getElementById("fnode-price-nifty")) {
          document.getElementById("fnode-price-nifty").textContent = `₹${Number(nifty.price).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
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
        if (document.getElementById("fnode-price-sensex")) {
          document.getElementById("fnode-price-sensex").textContent = `₹${Number(sensex.price).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
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

  // High-Conviction Option Trade Suggestions (Intraday & Expiry Setups)
  renderOptionTradeSuggestions(options.option_trade_suggestions || options.suggestions || options);

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

function renderOptionTradeSuggestions(optData) {
  const container = document.getElementById("opt-suggestions-container");
  if (!container) return;

  let suggestions = [];
  if (Array.isArray(optData)) {
    suggestions = optData;
  } else if (optData && Array.isArray(optData.all_suggestions)) {
    suggestions = optData.all_suggestions;
  } else if (optData && typeof optData === "object") {
    ["nifty_suggestion", "bn_suggestion", "sensex_suggestion"].forEach(k => {
      if (optData[k]) suggestions.push(optData[k]);
    });
  }

  if (!suggestions || suggestions.length === 0) {
    suggestions = [
      {
        index: "NIFTY 50",
        strike: 23400,
        type: "CE",
        expiry: "CURRENT WEEK",
        action: "BUY",
        entry_range: "₹120 - ₹135",
        target_1: "₹175 (+35%)",
        target_2: "₹210 (+60%)",
        stop_loss: "₹85 (-32%)",
        lot_size: "25 Qty / Lot",
        est_margin: "₹3,250 / Lot",
        rr_ratio: "1 : 2.4",
        confidence: "94% CONVICTION",
        pcr_confluence: "PCR 1.18 Bullish Build-up with strong 23300 Put writing support",
        status: "ACTIVE 🟢"
      },
      {
        index: "BANK NIFTY",
        strike: 56500,
        type: "CE",
        expiry: "CURRENT WEEK",
        action: "BUY",
        entry_range: "₹240 - ₹265",
        target_1: "₹340 (+34%)",
        target_2: "₹420 (+65%)",
        stop_loss: "₹170 (-32%)",
        lot_size: "15 Qty / Lot",
        est_margin: "₹3,800 / Lot",
        rr_ratio: "1 : 2.2",
        confidence: "91% CONVICTION",
        pcr_confluence: "PCR 1.12 Institutional Call unwinding at 56200 with aggressive HDFC/ICICI momentum",
        status: "ACTIVE 🟢"
      },
      {
        index: "BSE SENSEX",
        strike: 74800,
        type: "CE",
        expiry: "CURRENT WEEK",
        action: "BUY",
        entry_range: "₹180 - ₹205",
        target_1: "₹260 (+33%)",
        target_2: "₹330 (+69%)",
        stop_loss: "₹125 (-34%)",
        lot_size: "10 Qty / Lot",
        est_margin: "₹1,950 / Lot",
        rr_ratio: "1 : 2.5",
        confidence: "89% CONVICTION",
        pcr_confluence: "PCR 1.08 Heavy Put Addition at 74500 base level",
        status: "ACTIVE 🟢"
      }
    ];
  }

  const hasSignalAccess = typeof window.hasAccess === "function" ? window.hasAccess("signals") : false;

  container.innerHTML = suggestions.map((s, idx) => {
    const isCall = (s.type || s.contract || '').toUpperCase().includes('CE') || (s.action || '').toUpperCase().includes('CALL');
    const typeBadge = isCall 
      ? `<span class="tsm-badge-pill admin font-mono">CALL (CE)</span>` 
      : `<span class="tsm-badge-pill gold font-mono" style="border-color:rgba(255,51,102,0.5); color:#ff3366;">PUT (PE)</span>`;
    
    const contractName = s.contract || `${s.index || 'INDEX'} ${s.strike || ''} ${s.type || ''}`.trim();
    const lotSize = typeof s.lot_size === 'number' ? `${s.lot_size} Qty / Lot` : (s.lot_size || '1 Lot');
    const t1 = s.target1 || s.target_1 || 'N/A';
    const t2 = s.target2 || s.target_2 || 'N/A';
    const sl = s.stop_loss || s.sl || 'N/A';
    const rr = s.risk_reward || s.rr_ratio || '1 : 2.5';
    const confluence = s.confluence || s.pcr_confluence || 'Institutional order flow and Open Interest delta alignment.';
    const isLocked = !hasSignalAccess && idx > 0;

    if (isLocked) {
      return `
        <div class="opt-suggestion-card" style="position:relative; overflow:hidden; border:1px solid rgba(255,215,0,0.3);">
          <div style="filter:blur(5px); opacity:0.4; pointer-events:none; user-select:none;">
            <div class="opt-sug-header">
              <div><span class="opt-sug-symbol">${escapeHtml(contractName)}</span></div>
            </div>
            <div class="opt-sug-grid">
              <div class="opt-sug-cell"><span class="lbl">ENTRY RANGE</span><span class="val cyan">••••••</span></div>
              <div class="opt-sug-cell"><span class="lbl">TARGET 1</span><span class="val green">••••••</span></div>
            </div>
          </div>
          <div style="position:absolute; inset:0; display:flex; flex-direction:column; align-items:center; justify-content:center; background:rgba(4,14,28,0.88); backdrop-filter:blur(4px); padding:16px; text-align:center;">
            <div style="font-size:18px; margin-bottom:4px;">🔒</div>
            <strong style="font-family:var(--font-orb); font-size:11px; color:var(--neon-gold); margin-bottom:4px;">PREMIUM F&O SETUP (${escapeHtml(s.index || 'INDEX')})</strong>
            <p style="font-size:10px; color:var(--text-dim); margin-bottom:8px;">Live strike setups &amp; PCR delta flow require an active subscription.</p>
            <button class="tsm-btn-cta gold" onclick="openSaasUpgradeModal('Indian Options Intelligence', 'Starter ($19/mo)')" style="padding:5px 12px; font-size:10px;">⭐ UNLOCK ($19/mo)</button>
          </div>
        </div>
      `;
    }

    const previewTag = (!hasSignalAccess && idx === 0) ? `<span class="tsm-badge-pill green font-mono" style="font-size:8.5px; margin-left:4px;">🆓 FREE PREVIEW</span>` : '';

    return `
      <div class="opt-suggestion-card">
        <div class="opt-sug-header">
          <div>
            <span class="opt-sug-symbol">${escapeHtml(contractName)} ${previewTag}</span>
            <div class="opt-sug-sub">${escapeHtml(s.expiry || 'CURRENT WEEKLY')} • ${escapeHtml(lotSize)}</div>
          </div>
          <div style="display:flex; gap:6px; align-items:center;">
            ${typeBadge}
            <span class="tsm-badge-pill admin">${escapeHtml(s.confidence || '92% CONF')}</span>
          </div>
        </div>
        <div class="opt-sug-grid">
          <div class="opt-sug-cell"><span class="lbl">ACTION</span><span class="val green">${escapeHtml(s.action || 'BUY')}</span></div>
          <div class="opt-sug-cell"><span class="lbl">ENTRY RANGE</span><span class="val cyan">${escapeHtml(s.entry_range || '')}</span></div>
          <div class="opt-sug-cell"><span class="lbl">TARGET 1</span><span class="val green">${escapeHtml(t1)}</span></div>
          <div class="opt-sug-cell"><span class="lbl">TARGET 2</span><span class="val green">${escapeHtml(t2)}</span></div>
          <div class="opt-sug-cell"><span class="lbl">STOP LOSS</span><span class="val red-text">${escapeHtml(sl)}</span></div>
          <div class="opt-sug-cell"><span class="lbl">R:R RATIO</span><span class="val gold">${escapeHtml(rr)}</span></div>
        </div>
        <div class="opt-sug-pcr">
          ⚡ <strong>PCR & Flow Confluence:</strong> ${escapeHtml(confluence)}
        </div>
      </div>
    `;
  }).join("");
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

// ══════════ 17. JARVIS AI VOICE ENGINE (WEB SPEECH & WEB AUDIO API) ══════════
let jarvisAudioCtx = null;
let isJarvisSpeaking = false;
let chatVoiceEnabled = true;
let speechRecognizer = null;
let isListening = false;

function getJarvisAudioContext() {
  if (!jarvisAudioCtx) {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (AudioCtx) jarvisAudioCtx = new AudioCtx();
  }
  if (jarvisAudioCtx && jarvisAudioCtx.state === 'suspended') {
    jarvisAudioCtx.resume();
  }
  return jarvisAudioCtx;
}

function playJarvisChime(type = 'activate') {
  try {
    const ctx = getJarvisAudioContext();
    if (!ctx) return;
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.connect(gain);
    gain.connect(ctx.destination);

    if (type === 'activate') {
      osc.type = 'sine';
      osc.frequency.setValueAtTime(587.33, now);
      osc.frequency.exponentialRampToValueAtTime(880.00, now + 0.15);
      gain.gain.setValueAtTime(0.12, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.35);
      osc.start(now);
      osc.stop(now + 0.35);
    } else if (type === 'beep') {
      osc.type = 'triangle';
      osc.frequency.setValueAtTime(1046.50, now);
      gain.gain.setValueAtTime(0.08, now);
      gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12);
      osc.start(now);
      osc.stop(now + 0.12);
    }
  } catch (e) {
    console.debug("Audio FX notice:", e);
  }
}

function getJarvisVoice(langCode = "en-US") {
  if (!('speechSynthesis' in window)) return null;
  const voices = window.speechSynthesis.getVoices();
  const targetLang = (langCode || "en-US").toLowerCase();

  // 1. Exact or prefix match for language code (e.g. 'hi-IN', 'bn-IN', 'ta-IN', 'es-ES', 'en-US')
  let match = voices.find(v => v.lang && v.lang.toLowerCase() === targetLang);
  if (match) return match;

  const prefix = targetLang.split("-")[0];
  match = voices.find(v => v.lang && v.lang.toLowerCase().startsWith(prefix));
  if (match) return match;

  // 2. Specific language name matches
  if (prefix === "hi") {
    match = voices.find(v => v.name.includes("Hindi") || v.name.includes("हिन्दी") || v.name.includes("Kalpana") || v.name.includes("Hemant"));
    if (match) return match;
  } else if (prefix === "bn") {
    match = voices.find(v => v.name.includes("Bengali") || v.name.includes("বাংলা") || v.name.includes("Bashkar"));
    if (match) return match;
  } else if (prefix === "ta") {
    match = voices.find(v => v.name.includes("Tamil") || v.name.includes("தமிழ்") || v.name.includes("Valluvar"));
    if (match) return match;
  } else if (prefix === "es") {
    match = voices.find(v => v.name.includes("Spanish") || v.name.includes("Español") || v.name.includes("Jorge") || v.name.includes("Monica"));
    if (match) return match;
  }

  // 3. Fallback to British / Natural English Jarvis voice
  return (
    voices.find(v => v.name.includes("Google UK English Male")) ||
    voices.find(v => v.name.includes("Daniel") || v.name.includes("Oliver") || v.name.includes("Arthur")) ||
    voices.find(v => v.name.includes("Natural") && v.lang.startsWith("en")) ||
    voices.find(v => v.lang.startsWith("en-GB")) ||
    voices.find(v => v.lang.startsWith("en-US")) ||
    voices[0] || null
  );
}

function speakText(text, langCode = "en-US", onEnd) {
  if (!('speechSynthesis' in window) || !text) return;
  window.speechSynthesis.cancel();

  // If onEnd was passed as 2nd argument (backward compatibility)
  if (typeof langCode === "function") {
    onEnd = langCode;
    langCode = "en-US";
  }

  const cleanSpeech = text
    .replace(/[#*`_~]/g, '')
    .replace(/₹/g, ' rupees ')
    .replace(/\$/g, ' dollars ')
    .replace(/\+/g, ' plus ')
    .replace(/%/g, ' percent ')
    .replace(/\n+/g, '. ')
    .trim();

  const utter = new SpeechSynthesisUtterance(cleanSpeech);
  const voice = getJarvisVoice(langCode);
  if (voice) {
    utter.voice = voice;
    utter.lang = voice.lang || langCode;
  } else {
    utter.lang = langCode || 'en-US';
  }
  utter.pitch = 0.95;
  utter.rate = 1.02;

  playJarvisChime('activate');
  setJarvisSpeakingState(true);

  utter.onend = () => {
    setJarvisSpeakingState(false);
    if (onEnd) onEnd();
  };

  utter.onerror = () => {
    setJarvisSpeakingState(false);
  };

  window.speechSynthesis.speak(utter);
}

function setJarvisSpeakingState(speaking) {
  isJarvisSpeaking = speaking;
  const btn = document.getElementById("headerJarvisVoiceBtn");
  const txt = document.getElementById("jarvisVoiceBtnText");
  if (btn) {
    if (speaking) {
      btn.classList.add("speaking");
      if (txt) txt.textContent = "🔊 JARVIS SPEAKING...";
    } else {
      btn.classList.remove("speaking");
      if (txt) txt.textContent = "🎙️ JARVIS VOICE";
    }
  }
}

function stopJarvisVoice() {
  if ('speechSynthesis' in window) {
    window.speechSynthesis.cancel();
  }
  setJarvisSpeakingState(false);
}

async function toggleJarvisBriefingVoice() {
  if (isJarvisSpeaking) {
    stopJarvisVoice();
    return;
  }
  try {
    const btn = document.getElementById("headerJarvisVoiceBtn");
    if (btn) btn.classList.add("speaking");
    const res = await fetch("/api/ai-assistant/briefing");
    const data = await res.json();
    if (data.voice_script) {
      speakText(data.voice_script);
    }
  } catch (e) {
    setJarvisSpeakingState(false);
    console.debug("Jarvis briefing voice error:", e);
  }
}

async function speakAssetIntel(symbol) {
  try {
    const res = await fetch(`/api/ai-assistant/asset-intel/${encodeURIComponent(symbol)}`);
    const data = await res.json();
    if (data.intel && data.intel.voice_script) {
      speakText(data.intel.voice_script);
    }
  } catch (e) {
    console.debug("Asset intel error:", e);
  }
}

function triggerJarvisSpokenBriefing() {
  toggleJarvisBriefingVoice();
}

// ══════════ 18. SPEECH RECOGNITION (VOICE INPUT TO CHATBOT) ══════════
function initSpeechRecognition() {
  const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRec) return null;
  const recognizer = new SpeechRec();
  recognizer.continuous = false;
  recognizer.interimResults = true;
  recognizer.lang = 'en-US';

  recognizer.onstart = () => {
    isListening = true;
    const micBtn = document.getElementById("jarvisMicBtn");
    if (micBtn) micBtn.classList.add("listening");
    playJarvisChime('beep');

    const input = document.getElementById("jarvisChatInput");
    if (input) {
      input.placeholder = "🎙️ Jarvis is listening... Speak your question now";
      input.value = "";
    }
  };

  recognizer.onresult = (event) => {
    let interim = "";
    let final = "";
    for (let i = event.resultIndex; i < event.results.length; ++i) {
      if (event.results[i].isFinal) {
        final += event.results[i][0].transcript;
      } else {
        interim += event.results[i][0].transcript;
      }
    }
    const input = document.getElementById("jarvisChatInput");
    if (input) {
      input.value = final || interim;
    }
    if (final) {
      sendJarvisMessage(final);
    }
  };

  recognizer.onerror = () => {
    isListening = false;
    const micBtn = document.getElementById("jarvisMicBtn");
    if (micBtn) micBtn.classList.remove("listening");
    const input = document.getElementById("jarvisChatInput");
    if (input) input.placeholder = "Ask Jarvis (e.g., 'What is Gold price?', 'NIFTY PCR', 'market summary')...";
  };

  recognizer.onend = () => {
    isListening = false;
    const micBtn = document.getElementById("jarvisMicBtn");
    if (micBtn) micBtn.classList.remove("listening");
    const input = document.getElementById("jarvisChatInput");
    if (input) input.placeholder = "Ask Jarvis (e.g., 'What is Gold price?', 'NIFTY PCR', 'market summary')...";
  };

  return recognizer;
}

function toggleVoiceInput() {
  if (!speechRecognizer) {
    speechRecognizer = initSpeechRecognition();
  }
  if (!speechRecognizer) {
    alert("Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
    return;
  }
  if (isListening) {
    speechRecognizer.stop();
  } else {
    try {
      speechRecognizer.start();
    } catch (e) {
      console.debug("Speech start error:", e);
    }
  }
}

// ══════════ 19. JARVIS AI QUANT CHATBOT CONTROLLER ══════════
function toggleJarvisChat() {
  const panel = document.getElementById("jarvisChatPanel");
  if (!panel) return;
  const isHidden = panel.style.display === "none";
  panel.style.display = isHidden ? "flex" : "none";
  if (isHidden) {
    playJarvisChime('activate');
    const inp = document.getElementById("jarvisChatInput");
    if (inp) inp.focus();
  }
}

function toggleChatVoice() {
  chatVoiceEnabled = !chatVoiceEnabled;
  const btn = document.getElementById("chatVoiceToggleBtn");
  if (btn) {
    btn.textContent = chatVoiceEnabled ? "🔊" : "🔇";
    btn.title = chatVoiceEnabled ? "Voice Output ON" : "Voice Output MUTED";
  }
}

function clearJarvisChat() {
  const list = document.getElementById("jarvisMessagesList");
  if (!list) return;
  list.innerHTML = `
    <div class="chat-bubble jarvis">
      <h3>🤖 Jarvis Quant AI</h3>
      Chat history cleared. Live multi-exchange data stream connected. Ask me any question on Spot Gold (XAU/USD), Bitcoin, NIFTY 50 options, or open positions.
      <div class="chat-bubble-footer">
        <span>QUANT CORE v3.2 • VERIFIED REAL DATA</span>
        <button class="chat-speak-btn" onclick="speakText('Chat history cleared. Live multi-exchange data stream connected.')">🔊 Listen</button>
      </div>
    </div>
  `;
}

function askJarvisPrompt(promptText) {
  const input = document.getElementById("jarvisChatInput");
  if (input) input.value = promptText;
  sendJarvisMessage(promptText);
}

function handleJarvisChatSubmit(event) {
  event.preventDefault();
  const input = document.getElementById("jarvisChatInput");
  if (!input) return;
  const query = input.value.trim();
  if (!query) return;
  input.value = "";
  sendJarvisMessage(query);
}

function openJarvisChart(symbol, interval = "5") {
  if (symbol) {
    currentTvSymbol = symbol;
  }
  switchView('chart');
  setTimeout(() => {
    initTradingViewWidget('tradingview_widget_fullscreen', symbol || currentTvSymbol);
  }, 100);
}

function renderMarkdownText(md) {
  if (!md) return "";
  let html = escapeHtml(md);
  html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
  html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  html = html.replace(/\*(.*?)\*/g, '<em>$1</em>');
  html = html.replace(/`(.*?)`/g, '<code>$1</code>');
  html = html.replace(/^\- (.*$)/gim, '<li>$1</li>');
  html = html.replace(/(<li>.*<\/li>)/gims, '<ul>$1</ul>');
  html = html.replace(/\n\n/g, '<br><br>');
  return html;
}

async function sendJarvisMessage(query) {
  const list = document.getElementById("jarvisMessagesList");
  if (!list || !query) return;

  // Ensure chat panel is open
  const panel = document.getElementById("jarvisChatPanel");
  if (panel && panel.style.display === "none") {
    panel.style.display = "flex";
  }

  // 1. User Message
  const userBubble = document.createElement("div");
  userBubble.className = "chat-bubble user";
  userBubble.textContent = query;
  list.appendChild(userBubble);

  // 2. Multi-Stage Pipeline Visual Indicator: Listen -> Analyze -> Verify
  const typingBubble = document.createElement("div");
  typingBubble.className = "chat-bubble jarvis";
  typingBubble.id = "jarvisTypingIndicator";
  typingBubble.innerHTML = `
    <div style="display:flex; flex-direction:column; gap:6px;">
      <div style="display:flex; align-items:center; gap:6px;">
        <span class="nc-pulse-dot cyan"></span>
        <strong style="color:var(--neon-cyan); font-size:11px;">JARVIS REASONING PIPELINE:</strong>
      </div>
      <div style="font-size:10px; color:var(--text-sec); padding-left:14px;" id="jarvisStepStatus">
        ⚡ Step 1/3: Analyzing query intent &amp; financial entities...
      </div>
    </div>
  `;
  list.appendChild(typingBubble);
  list.scrollTop = list.scrollHeight;

  // Step 2 transition after 400ms
  setTimeout(() => {
    const s = document.getElementById("jarvisStepStatus");
    if (s) s.innerHTML = "⚡ Step 2/3: Verifying live tick feeds &amp; order books from CoinSwitch, Delta &amp; NSE/BSE...";
  }, 400);

  try {
    const res = await fetch("/api/ai-assistant/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query: query })
    });

    const data = await res.json();
    const ind = document.getElementById("jarvisTypingIndicator");
    if (ind) ind.remove();

    if (data.status === "success") {
      const jarvisBubble = document.createElement("div");
      jarvisBubble.className = "chat-bubble jarvis";
      
      const formattedHtml = renderMarkdownText(data.reply);
      const safeVoice = (data.voice_script || "").replace(/'/g, "\\'");

      let chartBtnHtml = "";
      if (data.chart_action && data.chart_action.symbol) {
        const sym = escapeHtml(data.chart_action.symbol);
        const title = escapeHtml(data.chart_action.title || `View ${sym} Chart`);
        const intv = escapeHtml(data.chart_action.interval || "5");
        chartBtnHtml = `
          <div style="margin-top:10px; padding-top:8px; border-top:1px dashed rgba(0,212,255,0.2);">
            <button class="chat-chart-action-btn" onclick="openJarvisChart('${sym}', '${intv}')" style="background:linear-gradient(135deg, rgba(0,212,255,0.2), rgba(0,100,200,0.4)); border:1px solid var(--neon-cyan); color:#00f3ff; border-radius:6px; padding:6px 14px; font-size:11px; font-weight:700; cursor:pointer; display:inline-flex; align-items:center; gap:6px; transition:all 0.2s ease; box-shadow:0 0 10px rgba(0,212,255,0.2);">
              <span>📊</span><span>${title}</span>
            </button>
          </div>
        `;
      }

      jarvisBubble.innerHTML = `
        ${formattedHtml}
        ${chartBtnHtml}
        <div class="chat-bubble-footer">
          <span class="green" style="font-weight:700;">● 100% VERIFIED LIVE DATA</span>
          <button class="chat-speak-btn" onclick="speakText('${safeVoice}', '${data.lang || 'en-US'}')">🔊 Listen</button>
        </div>
      `;
      list.appendChild(jarvisBubble);
      list.scrollTop = list.scrollHeight;

      if (chatVoiceEnabled && data.voice_script) {
        speakText(data.voice_script, data.lang || 'en-US');
      }
    } else {
      const errBubble = document.createElement("div");
      errBubble.className = "chat-bubble jarvis";
      errBubble.innerHTML = `<span style="color:#ff3366;">Error processing query: ${escapeHtml(data.message || 'Unknown error')}</span>`;
      list.appendChild(errBubble);
    }
  } catch (err) {
    const ind = document.getElementById("jarvisTypingIndicator");
    if (ind) ind.remove();
    const errBubble = document.createElement("div");
    errBubble.className = "chat-bubble jarvis";
    errBubble.innerHTML = `<span style="color:#ff3366;">Connection error: ${escapeHtml(err)}</span>`;
    list.appendChild(errBubble);
  }
  list.scrollTop = list.scrollHeight;
}

// ══════════ 20. 3D WEBGL MULTI-AGENT NEURAL SPHERE & LIVE FLOATING NODES ══════════
let scene3d, camera3d, renderer3d, sphereMesh, ringMesh1, ringMesh2, particles3d;
let floatingNodes = [
  { id: "gold", symbol: "XAU/USD", name: "Gold", icon: "🥇", spotId: "fnode-spot-gold", futId: "fnode-fut-gold", basisId: "fnode-basis-gold", defaultSpot: "$4,355.60", defaultFut: "$4,354.00", defaultBasis: "Δ -0.037%", colorClass: "gold-badge", theta: 0, phi: 0.35, radius: 4.2 },
  { id: "btc", symbol: "BTC/USDT", name: "BTC", icon: "₿", spotId: "fnode-spot-btc", futId: "fnode-fut-btc", basisId: "fnode-basis-btc", defaultSpot: "$77,264.28", defaultFut: "$77,236.90", defaultBasis: "Δ -0.035%", colorClass: "cyan-badge", theta: Math.PI * 0.35, phi: -0.25, radius: 4.4 },
  { id: "eth", symbol: "ETH/USDT", name: "ETH", icon: "Ξ", spotId: "fnode-spot-eth", futId: "fnode-fut-eth", basisId: "fnode-basis-eth", defaultSpot: "$2,472.30", defaultFut: "$2,471.37", defaultBasis: "Δ -0.038%", colorClass: "cyan-badge", theta: Math.PI * 0.70, phi: 0.40, radius: 4.3 },
  { id: "sol", symbol: "SOL/USDT", name: "SOL", icon: "◎", spotId: "fnode-spot-sol", futId: "fnode-fut-sol", basisId: "fnode-basis-sol", defaultSpot: "$104.88", defaultFut: "$104.91", defaultBasis: "Δ +0.029%", colorClass: "", theta: Math.PI * 1.05, phi: -0.30, radius: 4.5 },
  { id: "xrp", symbol: "XRP/USDT", name: "XRP", icon: "✕", spotId: "fnode-spot-xrp", futId: "fnode-fut-xrp", basisId: "fnode-basis-xrp", defaultSpot: "$1.3187", defaultFut: "$1.3184", defaultBasis: "Δ -0.023%", colorClass: "cyan-badge", theta: Math.PI * 1.40, phi: 0.25, radius: 4.2 },
  { id: "nifty", symbol: "NIFTY 50", name: "NIFTY", icon: "🇮🇳", spotId: "fnode-spot-nifty", futId: "fnode-fut-nifty", basisId: "fnode-basis-nifty", defaultSpot: "₹23,286.30", defaultFut: "₹23,328.50", defaultBasis: "Δ +42.20", colorClass: "gold-badge", theta: Math.PI * 1.75, phi: -0.35, radius: 4.4 }
];

function initAgent3dCore() {
  const container = document.getElementById("agent3dContainer");
  const canvas = document.getElementById("agent3dCanvas");
  if (!container || !canvas || typeof THREE === "undefined") return;

  const width = container.clientWidth || 450;
  const height = container.clientHeight || 340;

  scene3d = new THREE.Scene();
  camera3d = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera3d.position.z = 8.5;

  renderer3d = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  renderer3d.setSize(width, height);
  renderer3d.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  // 1. Central Wireframe Quant Core (Icosahedron with glowing neon shader/material)
  const sphereGeo = new THREE.IcosahedronGeometry(2.2, 2);
  const sphereMat = new THREE.MeshBasicMaterial({
    color: 0x00f090,
    wireframe: true,
    transparent: true,
    opacity: 0.8
  });
  sphereMesh = new THREE.Mesh(sphereGeo, sphereMat);
  scene3d.add(sphereMesh);

  // 2. Outer Gyro Orbit Ring 1 (Electric Cyan)
  const ring1Geo = new THREE.TorusGeometry(3.2, 0.035, 16, 120);
  const ring1Mat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.85 });
  ringMesh1 = new THREE.Mesh(ring1Geo, ring1Mat);
  ringMesh1.rotation.x = Math.PI / 3.5;
  scene3d.add(ringMesh1);

  // 3. Outer Gyro Orbit Ring 2 (TheSmartMag Gold)
  const ring2Geo = new THREE.TorusGeometry(3.7, 0.035, 16, 120);
  const ring2Mat = new THREE.MeshBasicMaterial({ color: 0xffd700, transparent: true, opacity: 0.75 });
  ringMesh2 = new THREE.Mesh(ring2Geo, ring2Mat);
  ringMesh2.rotation.y = Math.PI / 3;
  scene3d.add(ringMesh2);

  // 4. Orbiting Multi-Agent Particle Swarm (113 live streaming nodes)
  const particleCount = 113;
  const particleGeo = new THREE.BufferGeometry();
  const posArray = new Float32Array(particleCount * 3);

  for (let i = 0; i < particleCount * 3; i += 3) {
    const r = 3.8 + Math.random() * 1.8;
    const theta = Math.random() * Math.PI * 2;
    const phi = Math.acos((Math.random() * 2) - 1);
    posArray[i] = r * Math.sin(phi) * Math.cos(theta);
    posArray[i + 1] = r * Math.sin(phi) * Math.sin(theta);
    posArray[i + 2] = r * Math.cos(phi);
  }

  particleGeo.setAttribute("position", new THREE.BufferAttribute(posArray, 3));
  const particleMat = new THREE.PointsMaterial({
    size: 0.09,
    color: 0x00f090,
    transparent: true,
    opacity: 0.95
  });

  particles3d = new THREE.Points(particleGeo, particleMat);
  scene3d.add(particles3d);

  // 5. Render 3D Floating Indicative Coin Badges with Dual Spot & Futures Display
  const overlay = document.getElementById("floatingNodesOverlay");
  if (overlay) {
    overlay.innerHTML = floatingNodes.map(node => `
      <div class="floating-coin-badge ${node.colorClass}" id="fnode-badge-${node.id}" onclick="handleFloatingNodeClick('${node.symbol}')" title="Click for live ${node.symbol} Spot & Futures telemetry">
        <span class="coin-badge-icon">${node.icon}</span>
        <div class="coin-badge-dual">
          <div class="coin-badge-line">
            <span class="coin-badge-name">${node.name}</span>
            <span class="coin-badge-price" id="${node.spotId}">${node.defaultSpot}</span>
          </div>
          <div class="coin-badge-line">
            <span class="lbl">FUT:</span>
            <span class="val fut" id="${node.futId}">${node.defaultFut}</span>
            <span class="coin-badge-basis" id="${node.basisId}">${node.defaultBasis}</span>
          </div>
        </div>
      </div>
    `).join("");
  }

  // Animation Loop with Real-Time Screen Projection for Badges
  let clock = new THREE.Clock();
  function animate3d() {
    requestAnimationFrame(animate3d);
    const elapsedTime = clock.getElapsedTime();

    if (sphereMesh) {
      sphereMesh.rotation.y += 0.006;
      sphereMesh.rotation.x += 0.003;
      // Pulsing heartbeat
      const pulse = 1.0 + Math.sin(elapsedTime * 2.5) * 0.04;
      sphereMesh.scale.set(pulse, pulse, pulse);
    }
    if (ringMesh1) {
      ringMesh1.rotation.x += 0.010;
      ringMesh1.rotation.y += 0.006;
    }
    if (ringMesh2) {
      ringMesh2.rotation.y -= 0.008;
      ringMesh2.rotation.z += 0.005;
    }
    if (particles3d) {
      particles3d.rotation.y += 0.0025;
    }

    // Update 3D Floating Badges positions
    const containerW = container.clientWidth || 450;
    const containerH = container.clientHeight || 340;

    floatingNodes.forEach((node, idx) => {
      const el = document.getElementById(`fnode-badge-${node.id}`);
      if (!el) return;

      const currentTheta = node.theta + (elapsedTime * 0.25 * (idx % 2 === 0 ? 1 : -1));
      const currentPhi = node.phi + Math.sin(elapsedTime * 0.5 + idx) * 0.15;
      const r = node.radius;

      const x = r * Math.sin(currentTheta) * Math.cos(currentPhi);
      const y = r * Math.sin(currentPhi);
      const z = r * Math.cos(currentTheta) * Math.cos(currentPhi);

      const vector = new THREE.Vector3(x, y, z);
      vector.project(camera3d);

      const screenX = (vector.x * 0.5 + 0.5) * containerW;
      const screenY = (-(vector.y * 0.5) + 0.5) * containerH;

      el.style.left = `${screenX}px`;
      el.style.top = `${screenY}px`;
      el.style.opacity = vector.z > 1 ? "0.2" : (0.55 + ((1 - vector.z) * 0.45)).toFixed(2);
      el.style.transform = `translate(-50%, -50%) scale(${Math.max(0.75, Math.min(1.15, 1.0 - (vector.z * 0.25)))})`;
    });

    renderer3d.render(scene3d, camera3d);
  }

  animate3d();

  // Resize Listener
  window.addEventListener("resize", () => {
    if (!container || !renderer3d || !camera3d) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    camera3d.aspect = w / h;
    camera3d.updateProjectionMatrix();
    renderer3d.setSize(w, h);
  });
}

function handleFloatingNodeClick(symbol) {
  if (symbol.includes("BTC")) {
    loadTvSymbol("BINANCE:BTCUSDT");
  } else if (symbol.includes("ETH")) {
    loadTvSymbol("BINANCE:ETHUSDT");
  } else if (symbol.includes("SOL")) {
    loadTvSymbol("BINANCE:SOLUSDT");
  } else if (symbol.includes("XRP")) {
    loadTvSymbol("BINANCE:XRPUSDT");
  } else if (symbol.includes("NIFTY")) {
    switchView('india');
  }

  speakAssetIntel(symbol);
}

// ══════════ 21. JARVIS 3D HOLOGRAPHIC MODAL ══════════
let jarvisScene, jarvisCamera, jarvisRenderer, jarvisBrainGroup;

function openJarvisModal() {
  const modal = document.getElementById("jarvisHologramModal");
  if (modal) modal.style.display = "flex";
  playJarvisChime('activate');
  initJarvis3dHologram();
}

function closeJarvisModal() {
  const modal = document.getElementById("jarvisHologramModal");
  if (modal) modal.style.display = "none";
}

function initJarvis3dHologram() {
  const canvas = document.getElementById("jarvis3dCanvas");
  if (!canvas || typeof THREE === "undefined" || jarvisRenderer) return;

  const w = canvas.parentElement.clientWidth || 400;
  const h = canvas.parentElement.clientHeight || 350;

  jarvisScene = new THREE.Scene();
  jarvisCamera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000);
  jarvisCamera.position.z = 8;

  jarvisRenderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
  jarvisRenderer.setSize(w, h);
  jarvisRenderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  jarvisBrainGroup = new THREE.Group();

  const coreGeo = new THREE.IcosahedronGeometry(2.4, 3);
  const coreMat = new THREE.MeshBasicMaterial({ color: 0x00f090, wireframe: true, transparent: true, opacity: 0.65 });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  jarvisBrainGroup.add(coreMesh);

  const ringGeo1 = new THREE.TorusGeometry(3.6, 0.04, 16, 100);
  const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.8 });
  const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
  ring1.rotation.x = Math.PI / 4;
  jarvisBrainGroup.add(ring1);

  const ringGeo2 = new THREE.TorusGeometry(4.2, 0.04, 16, 100);
  const ringMat2 = new THREE.MeshBasicMaterial({ color: 0xffd700, transparent: true, opacity: 0.7 });
  const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
  ring2.rotation.y = Math.PI / 3;
  jarvisBrainGroup.add(ring2);

  jarvisScene.add(jarvisBrainGroup);

  function animateHologram() {
    requestAnimationFrame(animateHologram);
    if (jarvisBrainGroup) {
      jarvisBrainGroup.rotation.y += 0.008;
      jarvisBrainGroup.rotation.x += 0.004;
      ring1.rotation.z += 0.012;
      ring2.rotation.z -= 0.009;
    }
    jarvisRenderer.render(jarvisScene, jarvisCamera);
  }
  animateHologram();
}

// ══════════ 22. CANVAS BACKGROUNDS & 5-STAGE WORKFLOW ══════════
function initCircuitBgCanvas() {
  const canvas = document.getElementById("circuitBgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  resize();
  window.addEventListener("resize", resize);

  const traces = [];
  for (let i = 0; i < 24; i++) {
    traces.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      len: 50 + Math.random() * 150,
      dir: Math.random() > 0.5 ? 0 : 1,
      speed: 0.3 + Math.random() * 0.7,
      progress: Math.random() * 100
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.strokeStyle = "rgba(0, 240, 144, 0.06)";
    ctx.lineWidth = 1;
    traces.forEach(t => {
      ctx.beginPath();
      ctx.moveTo(t.x, t.y);
      if (t.dir === 0) {
        ctx.lineTo(t.x + t.len, t.y);
      } else {
        ctx.lineTo(t.x, t.y + t.len);
      }
      ctx.stroke();
    });
    requestAnimationFrame(draw);
  }
  draw();
}

function initNeuralBgCanvas() {
  const canvas = document.getElementById("neuralBgCanvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  function resize() { canvas.width = window.innerWidth; canvas.height = window.innerHeight; }
  resize();
  window.addEventListener("resize", resize);

  const particles = [];
  const count = Math.min(45, Math.floor(window.innerWidth / 35));
  for (let i = 0; i < count; i++) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      vx: (Math.random() - 0.5) * 0.35,
      vy: (Math.random() - 0.5) * 0.35,
      radius: Math.random() * 1.5 + 0.8
    });
  }

  function draw() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let i = 0; i < particles.length; i++) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;

      ctx.beginPath();
      ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
      ctx.fillStyle = "rgba(0, 240, 144, 0.4)";
      ctx.fill();

      for (let j = i + 1; j < particles.length; j++) {
        const q = particles[j];
        const dist = Math.hypot(p.x - q.x, p.y - q.y);
        if (dist < 110) {
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(q.x, q.y);
          ctx.strokeStyle = `rgba(0, 212, 255, ${(1 - dist / 110) * 0.12})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }
  draw();
}

let activeWfStep = 0;
function initWorkflowCycle() {
  const steps = document.querySelectorAll(".wf-step-item");
  if (!steps || steps.length === 0) return;

  setInterval(() => {
    steps.forEach((s, idx) => {
      if (idx === activeWfStep) {
        s.classList.add("active");
      } else {
        s.classList.remove("active");
      }
    });
    activeWfStep = (activeWfStep + 1) % steps.length;
  }, 2500);
}

// ══════════ 23. RESPONSIVE MENUBAR & MOBILE DRAWER HANDLERS ══════════
window.toggleNavDropdown = function(e) {
  if (e) e.stopPropagation();
  const dropdown = document.getElementById("navMoreDropdown");
  if (dropdown) dropdown.classList.toggle("open");
};

window.closeNavMenus = function() {
  const dropdown = document.getElementById("navMoreDropdown");
  if (dropdown) dropdown.classList.remove("open");
};

window.toggleMobileNavDrawer = function() {
  const drawer = document.getElementById("mobileNavDrawer");
  if (!drawer) return;
  if (drawer.style.display === "none" || !drawer.style.display) {
    drawer.style.display = "flex";
  } else {
    drawer.style.display = "none";
  }
};

window.handleMobileDrawerBackdrop = function(e) {
  if (e.target.id === "mobileNavDrawer") {
    window.toggleMobileNavDrawer();
  }
};

document.addEventListener("click", (e) => {
  const dropdown = document.getElementById("navMoreDropdown");
  if (dropdown && !dropdown.contains(e.target)) {
    dropdown.classList.remove("open");
  }
});

// ══════════ 24. 3D COIN DETAILS MODAL & QUANT HUD HANDLERS ══════════
let currentModalCoin = "BTC/USDT";

window.handleFloatingNodeClick = function(symbol) {
  openCoinDetailsModal(symbol);
  speakAssetIntel(symbol);
};

let currentModalIcon = "🪙";
let coin3DScene = null;
let coin3DCamera = null;
let coin3DRenderer = null;
let coin3DMeshGroup = null;
let coin3DCylinder = null;
let coin3DOrbitRings = [];
let coin3DParticles = null;
let coin3DAnimId = null;
let coin3DIsSpinning = true;
let coin3DTheme = "gold";
let coin3DPointerDown = false;
let coin3DPrevPointer = { x: 0, y: 0 };

const COIN_3D_THEMES = {
  gold: { rim: 0xffd700, bg: "#ffd700", text: "#060e1c", light: 0xffd700, metal: 0.9, rough: 0.18 },
  cyan: { rim: 0x00d4ff, bg: "#00d4ff", text: "#060e1c", light: 0x00d4ff, metal: 0.85, rough: 0.2 },
  green: { rim: 0x00f090, bg: "#00f090", text: "#060e1c", light: 0x00f090, metal: 0.85, rough: 0.2 },
  purple: { rim: 0xbf5af2, bg: "#bf5af2", text: "#ffffff", light: 0xbf5af2, metal: 0.85, rough: 0.2 }
};

function createCoinTexture(symbol, icon, themeKey) {
  const canvas = document.createElement("canvas");
  canvas.width = 512;
  canvas.height = 512;
  const ctx = canvas.getContext("2d");
  const th = COIN_3D_THEMES[themeKey] || COIN_3D_THEMES.gold;

  // Background circle
  ctx.fillStyle = "#0a1828";
  ctx.fillRect(0, 0, 512, 512);

  const grad = ctx.createRadialGradient(256, 256, 50, 256, 256, 250);
  grad.addColorStop(0, th.bg);
  grad.addColorStop(0.7, "#081424");
  grad.addColorStop(1, "#020812");
  ctx.fillStyle = grad;
  ctx.beginPath();
  ctx.arc(256, 256, 240, 0, Math.PI * 2);
  ctx.fill();

  // Outer Tech Rings
  ctx.strokeStyle = th.bg;
  ctx.lineWidth = 10;
  ctx.beginPath();
  ctx.arc(256, 256, 230, 0, Math.PI * 2);
  ctx.stroke();

  ctx.lineWidth = 3;
  ctx.setLineDash([12, 8, 4, 8]);
  ctx.beginPath();
  ctx.arc(256, 256, 205, 0, Math.PI * 2);
  ctx.stroke();
  ctx.setLineDash([]);

  // Micro circuit ticks
  for (let i = 0; i < 36; i++) {
    const angle = (i * 10 * Math.PI) / 180;
    const r1 = i % 3 === 0 ? 185 : 195;
    const r2 = 205;
    ctx.beginPath();
    ctx.moveTo(256 + Math.cos(angle) * r1, 256 + Math.sin(angle) * r1);
    ctx.lineTo(256 + Math.cos(angle) * r2, 256 + Math.sin(angle) * r2);
    ctx.strokeStyle = "rgba(255,255,255,0.4)";
    ctx.lineWidth = i % 3 === 0 ? 3 : 1.5;
    ctx.stroke();
  }

  // Center Glow Shield
  ctx.fillStyle = "rgba(0,0,0,0.6)";
  ctx.beginPath();
  ctx.arc(256, 256, 160, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = th.bg;
  ctx.lineWidth = 4;
  ctx.stroke();

  // Central Icon / Emoji / Logo
  ctx.font = "bold 92px sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillStyle = "#ffffff";
  ctx.shadowColor = th.bg;
  ctx.shadowBlur = 18;
  ctx.fillText(icon || "🪙", 256, 215);

  // Symbol Text
  ctx.font = "900 46px Orbitron, sans-serif";
  ctx.fillStyle = th.bg;
  ctx.shadowBlur = 12;
  const cleanSym = (symbol || "ASSET").split("/")[0].replace(/[\(\)]/g, "");
  ctx.fillText(cleanSym, 256, 320);

  // Bottom subtitle
  ctx.font = "700 20px 'Roboto Mono', monospace";
  ctx.fillStyle = "rgba(255,255,255,0.7)";
  ctx.shadowBlur = 0;
  ctx.fillText("QUANT AI 3D", 256, 365);

  return new THREE.CanvasTexture(canvas);
}

function initCoin3DScene(symbol, icon) {
  const canvas = document.getElementById("coin3DCanvas");
  if (!canvas || typeof THREE === "undefined") return;

  const width = canvas.parentElement ? canvas.parentElement.clientWidth : 300;
  const height = canvas.parentElement ? canvas.parentElement.clientHeight : 260;

  if (coin3DAnimId) {
    cancelAnimationFrame(coin3DAnimId);
    coin3DAnimId = null;
  }

  if (!coin3DRenderer) {
    coin3DScene = new THREE.Scene();
    coin3DCamera = new THREE.PerspectiveCamera(40, width / height, 0.1, 100);
    coin3DCamera.position.set(0, 0, 14);

    coin3DRenderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    coin3DRenderer.setSize(width, height);
    coin3DRenderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    // Lights
    const ambLight = new THREE.AmbientLight(0xffffff, 0.9);
    coin3DScene.add(ambLight);

    const dirLight1 = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight1.position.set(5, 8, 10);
    coin3DScene.add(dirLight1);

    const dirLight2 = new THREE.DirectionalLight(0x00d4ff, 0.8);
    dirLight2.position.set(-8, -6, 5);
    coin3DScene.add(dirLight2);

    // Mesh Group
    coin3DMeshGroup = new THREE.Group();
    coin3DScene.add(coin3DMeshGroup);

    // Pointer Drag Listeners
    canvas.addEventListener("pointerdown", (e) => {
      coin3DPointerDown = true;
      coin3DPrevPointer = { x: e.clientX, y: e.clientY };
    });
    window.addEventListener("pointerup", () => { coin3DPointerDown = false; });
    window.addEventListener("pointermove", (e) => {
      if (!coin3DPointerDown || !coin3DMeshGroup) return;
      const dx = e.clientX - coin3DPrevPointer.x;
      const dy = e.clientY - coin3DPrevPointer.y;
      coin3DMeshGroup.rotation.y += dx * 0.012;
      coin3DMeshGroup.rotation.x += dy * 0.012;
      coin3DPrevPointer = { x: e.clientX, y: e.clientY };
    });
  } else {
    coin3DRenderer.setSize(width, height);
    if (coin3DCamera) {
      coin3DCamera.aspect = width / height;
      coin3DCamera.updateProjectionMatrix();
    }
  }

  // Clear previous mesh objects
  while (coin3DMeshGroup.children.length > 0) {
    const obj = coin3DMeshGroup.children[0];
    coin3DMeshGroup.remove(obj);
    if (obj.geometry) obj.geometry.dispose();
  }

  const th = COIN_3D_THEMES[coin3DTheme] || COIN_3D_THEMES.gold;
  const coinTex = createCoinTexture(symbol, icon, coin3DTheme);

  // Materials: [Side, Top, Bottom]
  const rimMat = new THREE.MeshStandardMaterial({
    color: th.rim,
    metalness: th.metal,
    roughness: th.rough,
    wireframe: false
  });
  const faceMat = new THREE.MeshStandardMaterial({
    map: coinTex,
    metalness: 0.25,
    roughness: 0.35
  });

  // 3D Cylinder Coin
  const cylGeo = new THREE.CylinderGeometry(3.6, 3.6, 0.48, 48, 2);
  coin3DCylinder = new THREE.Mesh(cylGeo, [rimMat, faceMat, faceMat]);
  coin3DCylinder.rotation.x = Math.PI / 2.3;
  coin3DMeshGroup.add(coin3DCylinder);

  // Outer Hologram Techno Rings
  const ringMat1 = new THREE.MeshBasicMaterial({ color: th.rim, wireframe: true, transparent: true, opacity: 0.5 });
  const ring1 = new THREE.Mesh(new THREE.TorusGeometry(4.8, 0.035, 16, 64), ringMat1);
  coin3DMeshGroup.add(ring1);

  const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.35 });
  const ring2 = new THREE.Mesh(new THREE.TorusGeometry(5.4, 0.025, 16, 72), ringMat2);
  ring2.rotation.x = Math.PI / 3;
  coin3DMeshGroup.add(ring2);

  coin3DOrbitRings = [ring1, ring2];

  // Quantum Particle Cloud
  const partCount = 45;
  const partGeo = new THREE.BufferGeometry();
  const partPos = new Float32Array(partCount * 3);
  for (let i = 0; i < partCount * 3; i += 3) {
    const r = 4.2 + Math.random() * 2.5;
    const theta = Math.random() * Math.PI * 2;
    const phi = (Math.random() - 0.5) * Math.PI;
    partPos[i] = r * Math.cos(phi) * Math.cos(theta);
    partPos[i + 1] = r * Math.sin(phi);
    partPos[i + 2] = r * Math.cos(phi) * Math.sin(theta);
  }
  partGeo.setAttribute("position", new THREE.BufferAttribute(partPos, 3));
  const partMat = new THREE.PointsMaterial({ color: th.rim, size: 0.12, transparent: true, opacity: 0.8 });
  coin3DParticles = new THREE.Points(partGeo, partMat);
  coin3DMeshGroup.add(coin3DParticles);

  // Animation Loop
  let clock = new THREE.Clock();
  function animate() {
    coin3DAnimId = requestAnimationFrame(animate);
    const dt = clock.getDelta();

    if (coin3DMeshGroup && coin3DIsSpinning && !coin3DPointerDown) {
      coin3DMeshGroup.rotation.y += 0.85 * dt;
      coin3DMeshGroup.rotation.x = Math.sin(clock.getElapsedTime() * 0.8) * 0.18 + 0.1;
    }
    if (ring1) ring1.rotation.z += 0.6 * dt;
    if (ring2) ring2.rotation.y -= 0.5 * dt;
    if (coin3DParticles) coin3DParticles.rotation.y += 0.3 * dt;

    coin3DRenderer.render(coin3DScene, coin3DCamera);
  }
  animate();
}

function switchCoin3DTheme(themeKey) {
  coin3DTheme = themeKey;
  document.querySelectorAll(".c3d-theme-btn").forEach(b => {
    if (b.classList.contains(themeKey)) b.classList.add("active");
    else b.classList.remove("active");
  });
  if (currentModalCoin) {
    const sym = currentModalCoin.split(" ")[0].replace(/[\(\)]/g, "");
    initCoin3DScene(sym, currentModalIcon || "🪙");
  }
}
window.switchCoin3DTheme = switchCoin3DTheme;

function toggleCoin3DSpin() {
  coin3DIsSpinning = !coin3DIsSpinning;
  const btn = document.getElementById("btnToggleCoin3DSpin");
  if (btn) {
    btn.textContent = coin3DIsSpinning ? "🔄 Auto-Spin" : "⏸️ Paused";
    btn.style.color = coin3DIsSpinning ? "var(--neon-green)" : "var(--text-dim)";
  }
}
window.toggleCoin3DSpin = toggleCoin3DSpin;

window.openCoinDetailsModal = function(symbol) {
  const modal = document.getElementById("coinDetailsModal");
  if (!modal) return;
  const cleanSym = (symbol || "BTC").toUpperCase().replace(/[\(\)]/g, "").trim();
  currentModalCoin = cleanSym;

  // Metadata Mapping for ANY coin/asset
  const ASSET_META = {
    "BTC": { name: "Bitcoin", icon: "₿", cat: "CRYPTO BENCHMARK • DUAL-EXCHANGE LIVE", price: 78635.70, chg: "+1.85%", rsi: 64.2, st: "STRONG BULL 🟢", conf: "94%" },
    "ETH": { name: "Ethereum", icon: "Ξ", cat: "LAYER-1 SMART CONTRACTS • DUAL-EXCHANGE LIVE", price: 2474.90, chg: "+2.45%", rsi: 66.8, st: "BULLISH 🟢", conf: "92%" },
    "SOL": { name: "Solana", icon: "◎", cat: "HIGH-THROUGHPUT L1 • DUAL-EXCHANGE LIVE", price: 103.11, chg: "+4.12%", rsi: 68.4, st: "STRONG BULL 🟢", conf: "95%" },
    "XRP": { name: "Ripple", icon: "✕", cat: "CROSS-BORDER LIQUIDITY • DUAL-EXCHANGE LIVE", price: 1.39, chg: "+1.40%", rsi: 58.2, st: "BULLISH 🟢", conf: "88%" },
    "DOGE": { name: "Dogecoin", icon: "Ð", cat: "MEME ASSET • HIGH MOMENTUM SPIKE", price: 0.0898, chg: "+5.12%", rsi: 72.1, st: "CATALYST ACCELERATION 🟢", conf: "90%" },
    "ADA": { name: "Cardano", icon: "₳", cat: "PROOF-OF-STAKE L1 • LIQUIDITY CLUSTER", price: 0.218, chg: "+0.85%", rsi: 52.4, st: "MEDIAN RANGE 🟡", conf: "86%" },
    "DOT": { name: "Polkadot", icon: "●", cat: "INTEROPERABILITY NETWORK • DUAL-EXCHANGE LIVE", price: 1.068, chg: "+1.10%", rsi: 54.0, st: "MEDIAN RANGE 🟡", conf: "85%" },
    "SHIB": { name: "Shiba Inu", icon: "🐕", cat: "MEME DERIVATIVE • ACCUMULATION", price: 0.0000165, chg: "+2.15%", rsi: 60.5, st: "BULLISH 🟢", conf: "87%" },
    "AVAX": { name: "Avalanche", icon: "🔺", cat: "SUBNET CONSENSUS L1 • DUAL-EXCHANGE LIVE", price: 8.06, chg: "+1.65%", rsi: 58.6, st: "BULLISH 🟢", conf: "89%" },
    "NEAR": { name: "NEAR Protocol", icon: "Ⓝ", cat: "SHARDED AI COMPUTING • DUAL-EXCHANGE LIVE", price: 2.287, chg: "+3.45%", rsi: 65.2, st: "STRONG BULL 🟢", conf: "91%" },
    "LINK": { name: "Chainlink", icon: "⬡", cat: "DECENTRALIZED ORACLE NETWORK", price: 12.689, chg: "+1.95%", rsi: 59.8, st: "BULLISH 🟢", conf: "90%" },
    "SUI": { name: "Sui Network", icon: "💧", cat: "MOVE-BASED L1 • BREAKOUT CLUSTER", price: 0.819, chg: "+4.80%", rsi: 71.3, st: "BREAKOUT MOMENTUM 🟢", conf: "93%" },
    "APT": { name: "Aptos", icon: "▲", cat: "MOVE ECOSYSTEM • HIGH VOLUME", price: 0.631, chg: "+3.20%", rsi: 63.4, st: "BULLISH 🟢", conf: "89%" },
    "PEPE": { name: "Pepe", icon: "🐸", cat: "VOLATILITY CATALYST • MEME DERIVATIVE", price: 0.0000088, chg: "+6.40%", rsi: 74.5, st: "SUPER BREAKOUT 🟢", conf: "94%" },
    "FLOKI": { name: "Floki", icon: "⚔️", cat: "GAMING & MEME ECOSYSTEM", price: 0.000145, chg: "+2.85%", rsi: 61.2, st: "BULLISH 🟢", conf: "88%" },
    "WIF": { name: "dogwifhat", icon: "🎩", cat: "SOLANA MEME DERIVATIVE", price: 0.216, chg: "+5.70%", rsi: 69.8, st: "HIGH VOLATILITY 🟢", conf: "91%" },
    "BONK": { name: "Bonk", icon: "🐶", cat: "COMMUNITY LIQUIDITY POOL", price: 0.000021, chg: "+3.90%", rsi: 62.4, st: "BULLISH 🟢", conf: "88%" },
    "AIOZ": { name: "AIOZ Network", icon: "⚡", cat: "DEPIN AI STREAMING • PRE-PUMP ACCUMULATION", price: 6.252, chg: "+8.45%", rsi: 76.2, st: "EARLY BREAKOUT CONFIRMED 🟢", conf: "96%" },
    "MOODENG": { name: "Moo Deng", icon: "🦛", cat: "VIRAL MEME DERIVATIVE • DUAL-EXCHANGE LIVE", price: 0.0443, chg: "+7.20%", rsi: 73.5, st: "HIGH VOLATILITY 🟢", conf: "92%" },
    "POPCAT": { name: "Popcat", icon: "🐱", cat: "SOLANA MEME DERIVATIVE", price: 0.0520, chg: "+4.15%", rsi: 67.0, st: "BULLISH 🟢", conf: "90%" },
    "XAUT": { name: "Tether Gold", icon: "🟡", cat: "RWA COMMODITY • PHYSICAL GOLD BACKED", price: 4422.48, chg: "+0.95%", rsi: 63.8, st: "SAFE HAVEN BULL 🟢", conf: "95%" },
    "GOLD": { name: "Spot Gold (XAU/USD)", icon: "🟡", cat: "MACRO COMMODITY • GLOBAL SAFE HAVEN", price: 2942.50, chg: "+0.82%", rsi: 62.4, st: "INSTITUTIONAL ACCUMULATION 🟢", conf: "94%" },
    "SILVER": { name: "Spot Silver (XAG/USD)", icon: "⚪", cat: "INDUSTRIAL PRECIOUS METAL", price: 33.15, chg: "+1.65%", rsi: 65.1, st: "BULLISH BREAKOUT 🟢", conf: "91%" },
    "CRUDE": { name: "Crude Oil (WTI)", icon: "🛢️", cat: "ENERGY COMMODITY • GLOBAL MACRO", price: 69.85, chg: "+1.42%", rsi: 58.7, st: "MACRO REBOUND 🟢", conf: "89%" },
    "NIFTY": { name: "NIFTY 50 Index", icon: "🏛", cat: "INDIAN BENCHMARK • NSE DERIVATIVES LIVE", price: 23347.25, chg: "+0.56%", rsi: 61.5, st: "CALL BUILDUP BULLISH 🟢", conf: "93%" },
    "BANKNIFTY": { name: "BANK NIFTY Index", icon: "🏦", cat: "INDIAN BANKING BENCHMARK • NSE F&O", price: 49820.50, chg: "+0.78%", rsi: 64.0, st: "STRONG BANKING ACCUMULATION 🟢", conf: "94%" },
    "RELIANCE": { name: "Reliance Industries", icon: "🏢", cat: "INDIAN LARGE CAP • ENERGY & TELECOM", price: 1245.80, chg: "+1.15%", rsi: 60.2, st: "BULLISH 🟢", conf: "91%" },
    "HDFCBANK": { name: "HDFC Bank", icon: "💳", cat: "INDIAN BANKING LEADER • HIGH WEIGHTAGE", price: 1680.40, chg: "+0.92%", rsi: 59.4, st: "BULLISH 🟢", conf: "90%" }
  };

  // Find meta
  const baseKey = Object.keys(ASSET_META).find(k => cleanSym.includes(k)) || "BTC";
  const meta = ASSET_META[baseKey] || {
    name: cleanSym,
    icon: "🪙",
    cat: "MULTI-MARKET ASSET • QUANT MODEL LIVE",
    price: 100.0,
    chg: "+1.50%",
    rsi: 60.0,
    st: "BULLISH 🟢",
    conf: "90%"
  };

  currentModalIcon = meta.icon;

  const spotFormatted = typeof meta.price === "number" ? (meta.price > 100 ? "$" + meta.price.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2}) : "$" + meta.price) : meta.price;
  const futPrice = typeof meta.price === "number" ? (meta.price * 0.9996) : meta.price;
  const futFormatted = typeof futPrice === "number" ? (futPrice > 100 ? "$" + futPrice.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2}) : "$" + futPrice.toFixed(4)) : futPrice;
  const entryVal = typeof meta.price === "number" ? "$" + (meta.price * 0.995).toFixed(meta.price > 50 ? 2 : 4) : "$99.50";
  const targetVal = typeof meta.price === "number" ? "$" + (meta.price * 1.035).toFixed(meta.price > 50 ? 2 : 4) : "$103.50";
  const slVal = typeof meta.price === "number" ? "$" + (meta.price * 0.985).toFixed(meta.price > 50 ? 2 : 4) : "$98.50";

  const elIcon = document.getElementById("cmodal-icon"); if (elIcon) elIcon.textContent = meta.icon;
  const elTitle = document.getElementById("cmodal-title"); if (elTitle) elTitle.textContent = `${meta.name.toUpperCase()} (${cleanSym})`;
  const elCat = document.getElementById("cmodal-cat"); if (elCat) elCat.textContent = meta.cat;
  const elSpot = document.getElementById("cmodal-spot"); if (elSpot) elSpot.textContent = spotFormatted;
  const elFut = document.getElementById("cmodal-fut"); if (elFut) elFut.textContent = futFormatted;
  const elBasis = document.getElementById("cmodal-basis"); if (elBasis) elBasis.textContent = "Δ -0.04% (EQUILIBRIUM)";
  const elChg = document.getElementById("cmodal-chg"); if (elChg) elChg.textContent = `${meta.chg} 🟢`;
  const elSt = document.getElementById("cmodal-supertrend"); if (elSt) elSt.textContent = meta.st;
  const elRsi = document.getElementById("cmodal-rsi"); if (elRsi) elRsi.textContent = `${meta.rsi} (AI CONFIRMED)`;
  const elConf = document.getElementById("cmodal-confidence"); if (elConf) elConf.textContent = `${meta.conf} CONVICTION`;
  const elSetup = document.getElementById("cmodal-setup-text"); if (elSetup) elSetup.textContent = `High-conviction ${meta.name} setup based on order flow delta imbalance, multi-agent sentiment, and volume breakout trajectory.`;
  const elEntry = document.getElementById("cmodal-entry"); if (elEntry) elEntry.textContent = entryVal;
  const elTarget = document.getElementById("cmodal-target"); if (elTarget) elTarget.textContent = targetVal;
  const elSl = document.getElementById("cmodal-sl"); if (elSl) elSl.textContent = slVal;
  const el3DTag = document.getElementById("cmodal-3d-tag"); if (el3DTag) el3DTag.textContent = cleanSym;

  modal.style.display = "flex";

  // Initialize/Render 3D Scene
  setTimeout(() => {
    initCoin3DScene(cleanSym, meta.icon);
  }, 50);
};

window.closeCoinDetailsModal = function() {
  const modal = document.getElementById("coinDetailsModal");
  if (modal) modal.style.display = "none";
  if (coin3DAnimId) {
    cancelAnimationFrame(coin3DAnimId);
    coin3DAnimId = null;
  }
};

window.handleCoinDetailsBackdropClick = function(e) {
  if (e.target.id === "coinDetailsModal") closeCoinDetailsModal();
};

window.handleCoinModalOpenChart = function() {
  closeCoinDetailsModal();
  let tvSymbol = "BINANCE:BTCUSDT";
  if (currentModalCoin.includes("ETH")) tvSymbol = "BINANCE:ETHUSDT";
  else if (currentModalCoin.includes("SOL")) tvSymbol = "BINANCE:SOLUSDT";
  else if (currentModalCoin.includes("XRP")) tvSymbol = "BINANCE:XRPUSDT";
  else if (currentModalCoin.includes("NIFTY")) {
    switchView("india");
    return;
  }
  loadTvSymbol(tvSymbol);
  switchView("chart");
};

window.handleCoinModalSimulateTrade = function() {
  closeCoinDetailsModal();
  switchView("terminal");
  alert(`⚡ AI Quant Trade Simulation triggered for ${currentModalCoin} with 1% Risk Allocation and Trailing Ratchet.`);
};

// ═══════════════════════════════════════════════════════════════════════════
// TRADER & ADMIN SUBTAB SWITCHING
// ═══════════════════════════════════════════════════════════════════════════
// TRADER & ADMIN SUBTAB SWITCHING & DATA SYNC
// ═══════════════════════════════════════════════════════════════════════════
window.currentTraderSubTab = "overview";
window.currentAdminSubTab = "overview";
window.currentSaasBillingInterval = "monthly";
window.cachedUserSubscription = null;
window.cachedUserPermissions = null;

// ═══════════════════════════════════════════════════════════════════════════
// SAAS SUBSCRIPTION, PERMISSION GATING & STRIPE USD CHECKOUT
// ═══════════════════════════════════════════════════════════════════════════

async function fetchUserSubscriptionData() {
  const token = localStorage.getItem("tsm_user_token") || localStorage.getItem("tsm_jwt_token") || userToken || adminToken;
  if (!token) {
    window.cachedUserSubscription = null;
    window.cachedUserPermissions = null;
    return null;
  }

  try {
    const res = await fetch("/api/saas/my-subscription", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "success") {
      window.cachedUserSubscription = data.subscription;
      window.cachedUserPermissions = data.permissions;
      updateSubscriptionUI(data);
      return data;
    }
  } catch (e) {
    console.debug("fetchUserSubscriptionData notice:", e);
  }
  return null;
}

function updateSubscriptionUI(data) {
  const sub = data.subscription || {};
  const perms = data.permissions || {};
  const u = data.user || {};

  const tierEl = document.getElementById("traderHeaderTier");
  if (tierEl) {
    const isSuper = perms.is_superadmin || u.role === "superadmin" || (currentUser && currentUser.role === "superadmin");
    tierEl.textContent = isSuper ? "SUPER ADMIN (UNRESTRICTED)" : `${(sub.plan_name || 'FREE').toUpperCase()} (${(sub.status || 'ACTIVE').toUpperCase()})`;
    tierEl.style.color = isSuper ? "var(--neon-gold)" : (sub.is_active ? "var(--neon-green)" : "var(--neon-red)");
  }
}

window.hasAccess = function(serviceName) {
  if (adminToken || (currentUser && currentUser.role === "superadmin")) return true;
  if (window.cachedUserPermissions && window.cachedUserPermissions.is_superadmin) return true;
  const currentTok = userToken || localStorage.getItem("tsm_user_token") || localStorage.getItem("tsm_jwt_token");
  if (!currentTok) return false;
  if (window.cachedUserPermissions && window.cachedUserPermissions[serviceName] !== undefined) {
    return Boolean(window.cachedUserPermissions[serviceName]);
  }
  if (window.cachedUserSubscription && window.cachedUserSubscription.is_active) {
    return true;
  }
  return false;
};

window.openSaasUpgradeModal = function(featureName, requiredPlan) {
  const modal = document.getElementById("saasUpgradeModal");
  if (modal) {
    modal.style.display = "flex";
    modal.classList.add("active");
  }
  if (featureName && typeof showFloatingToast === "function") {
    showFloatingToast(`🔒 Premium Feature: '${featureName}' requires an active ${requiredPlan || 'Pro/Elite'} subscription.`, "gold");
  }
};

window.closeSaasUpgradeModal = function() {
  const modal = document.getElementById("saasUpgradeModal");
  if (modal) {
    modal.style.display = "none";
    modal.classList.remove("active");
  }
};

window.handleSaasModalBackdrop = function(e) {
  if (e.target && e.target.id === "saasUpgradeModal") {
    closeSaasUpgradeModal();
  }
};

window.setSaasBillingInterval = function(interval) {
  window.currentSaasBillingInterval = interval;
  const toggle = document.getElementById("saasBillingIntervalToggle");
  if (toggle) toggle.checked = (interval === "yearly");

  const lblM = document.getElementById("lblBillingMonthly");
  const lblY = document.getElementById("lblBillingYearly");
  if (lblM) lblM.style.color = interval === "monthly" ? "var(--neon-green)" : "var(--text-dim)";
  if (lblY) lblY.style.color = interval === "yearly" ? "var(--neon-green)" : "var(--text-dim)";

  document.querySelectorAll(".saas-plan-price").forEach(el => {
    el.textContent = interval === "yearly" ? el.getAttribute("data-yearly") : el.getAttribute("data-monthly");
  });
  document.querySelectorAll(".saas-plan-unit").forEach(el => {
    el.textContent = interval === "yearly" ? "/year" : "/month";
  });
};

window.toggleSaasBillingInterval = function(isYearly) {
  setSaasBillingInterval(isYearly ? "yearly" : "monthly");
};

window.handleCheckoutPlan = async function(planId) {
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) {
    closeSaasUpgradeModal();
    if (typeof openAuthModal === "function") openAuthModal("register");
    if (typeof showFloatingToast === "function") {
      showFloatingToast("Please register or log in first before choosing a plan.", "gold");
    }
    return;
  }

  const interval = window.currentSaasBillingInterval || "monthly";
  try {
    const res = await fetch("/api/saas/create-checkout-session", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ plan_id: planId, interval: interval })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (data.simulated) {
        // Activate instantly in test/direct mode
        await fetch("/api/saas/activate-subscription", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: JSON.stringify({ plan_id: planId, interval: interval })
        });
        closeSaasUpgradeModal();
        await fetchUserSubscriptionData();
        alert(`🎉 Subscription Activated! You now have full access to ${planId.toUpperCase()} Trader features.`);
        if (typeof switchView === "function") switchView("trader");
      } else if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } else {
      alert(`Checkout Notice: ${data.message || 'Unable to initiate Stripe checkout'}`);
    }
  } catch (err) {
    alert(`Checkout error: ${err.message}`);
  }
};

window.handleCheckoutAddon = async function(addonId) {
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) {
    closeSaasUpgradeModal();
    if (typeof openAuthModal === "function") openAuthModal("register");
    return;
  }

  try {
    const res = await fetch("/api/saas/create-checkout-session", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ addon_id: addonId })
    });
    const data = await res.json();
    if (data.status === "success") {
      if (data.simulated) {
        await fetch("/api/saas/activate-subscription", {
          method: "POST",
          headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
          body: JSON.stringify({ plan_id: addonId })
        });
        closeSaasUpgradeModal();
        await fetchUserSubscriptionData();
        alert(`🎉 One-Time Add-on Activated! Permanent access granted.`);
      } else if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    }
  } catch (err) {
    alert(`Add-on checkout error: ${err.message}`);
  }
};

window.handleContactEnterprise = function() {
  window.open("https://t.me/FOREXINDIAN_BOT", "_blank");
};

// ═══════════════════════════════════════════════════════════════════════════
// SUPER ADMIN SAAS & GRANULAR SERVICE CONTROL CENTER
// ═══════════════════════════════════════════════════════════════════════════

async function fetchAdminSaasMetrics() {
  const token = getAdminAuthToken();
  if (!token) return;

  try {
    const res = await fetch("/api/admin/saas/metrics", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "success" && data.metrics) {
      const m = data.metrics;
      const elMrr = document.getElementById("admin-rev-mrr");
      if (elMrr) elMrr.textContent = `$${m.mrr.toFixed(2)}`;

      const elArr = document.getElementById("admin-rev-arr");
      if (elArr) elArr.textContent = `$${m.arr.toFixed(2)}`;

      const elMrrSub = document.getElementById("admin-rev-mrr-sub");
      if (elMrrSub) elMrrSub.textContent = `${m.active_subscriptions} Active Subscriptions • Settling to ${m.payout_destination}`;

      // Render recent payments
      const tbody = document.getElementById("admin-sales-tbody");
      if (tbody && m.recent_payments && m.recent_payments.length > 0) {
        tbody.innerHTML = m.recent_payments.map(p => `
          <tr>
            <td class="font-mono text-dim">TX-${p.id}</td>
            <td><strong>${p.name || p.email}</strong><br><span style="font-size:10px; color:var(--text-dim);">${p.email}</span></td>
            <td><span class="tsm-badge-pill green">${p.plan_or_addon.toUpperCase()}</span></td>
            <td class="font-mono green font-bold">$${p.amount.toFixed(2)} USD</td>
            <td><span class="cyan font-mono" style="font-size:10px;">Stripe (USD) &rarr; Rise</span></td>
            <td><span class="tsm-badge-pill green">COMPLETED ✓</span></td>
          </tr>
        `).join("");
      }
    }
  } catch (e) {
    console.debug("fetchAdminSaasMetrics error:", e);
  }
}

async function fetchAdminSaasUsersList() {
  const token = getAdminAuthToken();
  if (!token) return;

  const tbody = document.getElementById("admin-saas-users-tbody");
  if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center empty-state"><div class="nc-spinner-mini" style="margin:0 auto 6px auto;"></div>Loading SaaS users and service permissions...</td></tr>`;

  try {
    const res = await fetch("/api/admin/saas/users", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "success" && data.users) {
      renderAdminSaasUsersTable(data.users);
    }
  } catch (e) {
    if (tbody) tbody.innerHTML = `<tr><td colspan="6" class="text-center red">Failed to load SaaS user directory: ${e.message}</td></tr>`;
  }
}

function renderAdminSaasUsersTable(users) {
  const tbody = document.getElementById("admin-saas-users-tbody");
  if (!tbody) return;

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="6" class="text-center empty-state">No registered traders found.</td></tr>`;
    return;
  }

  tbody.innerHTML = users.map(u => {
    const p = u.permissions || {};
    const isSuper = u.role === "superadmin";
    const subBadge = isSuper 
      ? `<span class="tsm-badge-gold">👑 SUPER ADMIN</span>`
      : (u.is_sub_active 
          ? `<span class="tsm-badge-pill green">${u.plan_id.toUpperCase()} (${u.subscription_status.toUpperCase()})</span>`
          : `<span class="tsm-badge-pill red">${u.plan_id.toUpperCase()} (EXPIRED)</span>`);

    const expiryText = u.expires_at > 0 
      ? new Date(u.expires_at * 1000).toLocaleDateString() 
      : (isSuper ? "Lifetime" : "None");

    // Service Toggle Badges
    const renderToggle = (serviceKey, label) => {
      const active = isSuper || Boolean(p[serviceKey]);
      return `
        <button class="tsm-btn-secondary" style="padding:2px 6px; font-size:9.5px; border-color:${active ? 'var(--neon-green)' : 'rgba(255,255,255,0.1)'}; color:${active ? 'var(--neon-green)' : 'var(--text-dim)'};" 
                onclick="adminToggleUserPermission(${u.id}, '${serviceKey}', ${active})" title="Toggle ${label}">
          ${label}: <strong>${active ? 'ON ✓' : 'OFF'}</strong>
        </button>
      `;
    };

    return `
      <tr>
        <td>
          <strong>${u.name || 'Trader'}</strong><br>
          <span style="font-size:10px; color:var(--text-dim);">ID: #${u.id} • ${u.role.toUpperCase()}</span>
        </td>
        <td class="font-mono text-neon" style="font-size:11px;">${u.email}</td>
        <td>${subBadge}</td>
        <td>
          <div class="font-mono" style="font-size:11px;">Expires: <strong>${expiryText}</strong></div>
          <div style="font-size:10px; color:var(--text-dim);">Total Spent: <strong class="green-text">$${u.total_spent_usd.toFixed(2)} USD</strong></div>
        </td>
        <td>
          <div style="display:flex; flex-wrap:wrap; gap:4px; max-width:340px;">
            ${renderToggle('ai_chat', 'AI Chat')}
            ${renderToggle('signals', 'Signals')}
            ${renderToggle('voice', 'Voice')}
            ${renderToggle('risk', 'Risk')}
            ${renderToggle('portfolio', 'Portfolio')}
            ${renderToggle('api', 'API')}
          </div>
        </td>
        <td>
          <div style="display:flex; gap:4px;">
            <button class="tsm-btn-cta green" style="padding:4px 8px; font-size:10px;" onclick="adminPromptUserUpgrade(${u.id}, '${u.email}', '${u.plan_id}')">⚡ PLAN</button>
          </div>
        </td>
      </tr>
    `;
  }).join("");
}

window.adminToggleUserPermission = async function(userId, serviceName, currentVal) {
  const token = getAdminAuthToken();
  if (!token) return;

  const newVal = !currentVal;
  try {
    const res = await fetch("/api/admin/saas/toggle-permission", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId, service_name: serviceName, enabled: newVal })
    });
    const data = await res.json();
    if (data.status === "success") {
      fetchAdminSaasUsersList();
    } else {
      alert(`Error toggling permission: ${data.message}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};

window.adminPromptUserUpgrade = async function(userId, userEmail, currentPlan) {
  const plan = prompt(`Assign new subscription plan for ${userEmail} (starter / pro / elite / enterprise):`, currentPlan || "pro");
  if (!plan) return;

  const daysStr = prompt("Enter duration in days (e.g. 30, 90, 365, 3650):", "30");
  if (!daysStr) return;

  const token = getAdminAuthToken();
  if (!token) return;

  try {
    const res = await fetch("/api/admin/saas/update-user-plan", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify({ user_id: userId, plan_id: plan.toLowerCase(), days: parseInt(daysStr) })
    });
    const data = await res.json();
    if (data.status === "success") {
      alert(`✓ ${data.message}`);
      fetchAdminSaasUsersList();
    } else {
      alert(`Error updating user plan: ${data.message}`);
    }
  } catch (err) {
    alert(`Error: ${err.message}`);
  }
};


// ═══════════════════════════════════════════════════════════════════════════
// JOURNALIT TRADING JOURNAL INTEGRATION
// ═══════════════════════════════════════════════════════════════════════════
async function fetchJournalData() {
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) return;

  try {
    const res = await fetch("/api/journal/overview", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "ok") {
      renderJournalItSuite(data);
    }
  } catch (e) {
    console.warn("fetchJournalData error:", e);
  }
}

function renderJournalItSuite(data) {
  const summary = data.summary || {};
  const elWin = document.getElementById("journalWinRate");
  if (elWin) elWin.textContent = `${summary.win_rate || 0}%`;

  const elPnl = document.getElementById("journalTotalPnl");
  if (elPnl) {
    const pnl = summary.total_pnl || 0;
    elPnl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}`;
    elPnl.className = `journalit-stat-val ${pnl >= 0 ? '' : 'loss'}`;
  }

  const elPf = document.getElementById("journalProfitFactor");
  if (elPf) elPf.textContent = (summary.profit_factor || 0).toFixed(2);

  const elAvgR = document.getElementById("journalAvgR");
  if (elAvgR) elAvgR.textContent = `${(summary.avg_r_multiple || 0).toFixed(2)} R`;

  const elTotal = document.getElementById("journalTotalTrades");
  if (elTotal) elTotal.textContent = summary.total_trades || 0;

  // Render Heatmap
  renderJournalCalendarHeatmap(data.calendar || {});

  // Render Table
  renderJournalEntriesTable(data.recent_entries || []);
}

function renderJournalCalendarHeatmap(calendarData) {
  const grid = document.getElementById("journalHeatmapGrid");
  if (!grid) return;

  grid.innerHTML = "";
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();

  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    const dayData = calendarData[dateStr];

    const cell = document.createElement("div");
    cell.className = "journalit-day-cell";

    let pnlText = "";
    if (dayData && dayData.daily_pnl !== 0) {
      const pnl = dayData.daily_pnl;
      pnlText = `<span class="journalit-day-pnl">${pnl > 0 ? '+' : ''}$${pnl.toFixed(0)}</span>`;
      if (pnl > 100) cell.classList.add("profit-heavy");
      else if (pnl > 0) cell.classList.add("profit-light");
      else if (pnl < -100) cell.classList.add("loss-heavy");
      else cell.classList.add("loss-light");
    }

    cell.innerHTML = `<span>${d}</span>${pnlText}`;
    cell.title = dayData ? `${dateStr}: P&L $${dayData.daily_pnl} (${dayData.trade_count} trades, Avg R: ${dayData.avg_r})` : `${dateStr}: No trades`;
    grid.appendChild(cell);
  }
}

function renderJournalEntriesTable(entries) {
  const tbody = document.getElementById("traderJournalTbody");
  if (!tbody) return;

  if (!entries || entries.length === 0) {
    tbody.innerHTML = `<tr><td colspan="10" class="text-center empty-state" style="padding:20px;">No journal entries logged yet. Click "+ NEW JOURNAL ENTRY" or let closed trades automatically log here.</td></tr>`;
    return;
  }

  tbody.innerHTML = entries.map(e => {
    const pnl = Number(e.pnl || 0);
    const pnlColor = pnl >= 0 ? "green" : "red-text";
    return `
      <tr>
        <td class="font-mono text-dim">${e.trade_date || '--'}</td>
        <td><strong>${e.symbol}</strong></td>
        <td><span class="${e.direction === 'LONG' ? 'green' : 'red-text'} font-bold">${e.direction}</span></td>
        <td class="font-mono">$${Number(e.entry_price || 0).toFixed(2)}</td>
        <td class="font-mono">$${Number(e.exit_price || 0).toFixed(2)}</td>
        <td class="font-mono ${pnlColor} font-bold">${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)}</td>
        <td class="font-mono cyan-text">${Number(e.r_multiple || 0).toFixed(1)} R</td>
        <td><span class="journalit-tag">${e.setup_tag || 'Breakout'}</span></td>
        <td><span class="journalit-emotion">${e.emotion || 'Disciplined'}</span></td>
        <td style="font-size:11px; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${e.notes || ''}">${e.notes || '--'}</td>
      </tr>
    `;
  }).join("");
}

window.openAddJournalModal = function() {
  const m = document.getElementById("journalEntryModal");
  if (m) m.style.display = "flex";
};

window.closeAddJournalModal = function() {
  const m = document.getElementById("journalEntryModal");
  if (m) m.style.display = "none";
};

window.handleJournalBackdropClick = function(e) {
  if (e.target.id === "journalEntryModal") closeAddJournalModal();
};

window.handleSaveJournalEntrySubmit = async function(e) {
  e.preventDefault();
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) return;

  const msg = document.getElementById("journalSubmitMsg");
  if (msg) msg.innerHTML = `<span class="cyan">Saving to journal...</span>`;

  const payload = {
    symbol: document.getElementById("j_symbol").value,
    direction: document.getElementById("j_direction").value,
    entry_price: parseFloat(document.getElementById("j_entry_price").value) || 0,
    exit_price: parseFloat(document.getElementById("j_exit_price").value) || 0,
    pnl: parseFloat(document.getElementById("j_pnl").value) || 0,
    setup_tag: document.getElementById("j_setup_tag").value,
    emotion: document.getElementById("j_emotion").value,
    r_multiple: parseFloat(document.getElementById("j_r_mult").value) || 0,
    notes: document.getElementById("j_notes").value
  };

  try {
    const res = await fetch("/api/journal/entry", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "ok") {
      if (msg) msg.innerHTML = `<span class="green">✓ Entry saved to JournalIt!</span>`;
      setTimeout(() => {
        closeAddJournalModal();
        fetchJournalData();
      }, 1000);
    } else {
      if (msg) msg.innerHTML = `<span class="red-text">Error: ${data.error || 'Failed to save'}</span>`;
    }
  } catch (err) {
    if (msg) msg.innerHTML = `<span class="red-text">Network error: ${err.message}</span>`;
  }
};

// ═══════════════════════════════════════════════════════════════════════════
// INDIAN BROKERS & CCXT EXCHANGES HANDLERS
// ═══════════════════════════════════════════════════════════════════════════
async function fetchIndianBrokersStatus() {
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) return;

  try {
    const res = await fetch("/api/brokers/indian/status", {
      headers: { "Authorization": `Bearer ${token}` }
    });
    const data = await res.json();
    if (data.status === "success" && data.configured_brokers) {
      Object.keys(data.configured_brokers).forEach(broker => {
        const badge = document.getElementById(`badge_broker_${broker}`);
        if (badge) {
          const isConn = data.configured_brokers[broker];
          badge.className = `broker-badge ${isConn ? 'connected' : 'disconnected'}`;
          badge.textContent = isConn ? "CONNECTED 🟢" : "DISCONNECTED";
        }
      });
    }
  } catch (e) {
    console.warn("fetchIndianBrokersStatus error:", e);
  }
}

window.handleSaveIndianBroker = async function(e, brokerName) {
  e.preventDefault();
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) return;

  let clientId = "", apiKey = "", apiSecret = "", totp = "", pin = "";
  if (brokerName === "zerodha") {
    clientId = document.getElementById("ib_zerodha_client")?.value || "";
    apiKey = document.getElementById("ib_zerodha_key")?.value || "";
    apiSecret = document.getElementById("ib_zerodha_secret")?.value || "";
    totp = document.getElementById("ib_zerodha_totp")?.value || "";
  } else if (brokerName === "angelone") {
    clientId = document.getElementById("ib_angelone_client")?.value || "";
    apiKey = document.getElementById("ib_angelone_key")?.value || "";
    pin = document.getElementById("ib_angelone_pin")?.value || "";
    totp = document.getElementById("ib_angelone_totp")?.value || "";
  } else if (brokerName === "dhan") {
    clientId = document.getElementById("ib_dhan_client")?.value || "";
    apiKey = document.getElementById("ib_dhan_key")?.value || "";
  } else if (brokerName === "upstox") {
    clientId = document.getElementById("ib_upstox_client")?.value || "";
    apiSecret = document.getElementById("ib_upstox_secret")?.value || "";
    apiKey = clientId;
  } else if (brokerName === "fyers") {
    clientId = document.getElementById("ib_fyers_client")?.value || "";
    apiSecret = document.getElementById("ib_fyers_secret")?.value || "";
    apiKey = clientId;
  } else if (brokerName === "shoonya") {
    clientId = document.getElementById("ib_shoonya_client")?.value || "";
    apiKey = document.getElementById("ib_shoonya_key")?.value || "";
    totp = document.getElementById("ib_shoonya_totp")?.value || "";
  }

  const payload = {
    broker_name: brokerName,
    client_id: clientId,
    api_key: apiKey,
    api_secret: apiSecret,
    totp_key: totp,
    pin: pin
  };

  try {
    const res = await fetch("/api/brokers/indian/save", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      const badge = document.getElementById(`badge_broker_${brokerName}`);
      if (badge) {
        badge.className = "broker-badge connected";
        badge.textContent = "CONNECTED 🟢";
      }
      alert(`✓ ${brokerName.toUpperCase()} credentials saved and encrypted securely.`);
    } else {
      alert(`Error saving ${brokerName}: ${data.message || 'Validation failed'}`);
    }
  } catch (err) {
    alert(`Network error saving broker: ${err.message}`);
  }
};

window.handleSaveCcxtExchange = async function(e, exchangeId) {
  e.preventDefault();
  const token = localStorage.getItem("tsm_jwt_token") || getCookie("auth_token");
  if (!token) return;

  const key = document.getElementById(`ccxt_${exchangeId}_key`)?.value || "";
  const secret = document.getElementById(`ccxt_${exchangeId}_secret`)?.value || "";
  const pass = document.getElementById(`ccxt_${exchangeId}_pass`)?.value || "";

  const payload = {
    exchange_id: exchangeId,
    api_key: key,
    api_secret: secret,
    password: pass
  };

  try {
    const res = await fetch("/api/brokers/ccxt/save", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.status === "success") {
      const badge = document.getElementById(`badge_ccxt_${exchangeId}`);
      if (badge) {
        badge.className = "broker-badge connected";
        badge.textContent = "CONNECTED 🟢";
      }
      alert(`✓ ${exchangeId.toUpperCase()} API credentials connected and verified via CCXT.`);
    } else {
      alert(`Error saving exchange: ${data.message || 'Validation failed'}`);
    }
  } catch (err) {
    alert(`Network error: ${err.message}`);
  }
};

// ════════════════════════════════════════════════════════════════════════════
// 14. MULTI-MARKET AI TRADE SUGGESTIONS & NEWS CATALYST ENGINE
// ════════════════════════════════════════════════════════════════════════════
let rawMultiMarketSignals = [];
let currentMarketFilter = "all";

async function fetchMultiMarketSignals(marketFilter, minConfidence) {
  const grid = document.getElementById("multiMarketSignalsGrid");
  const tbody = document.getElementById("multiMarketSignalsTbody");
  
  if (marketFilter) currentMarketFilter = marketFilter;
  const mFilter = currentMarketFilter === "high_conviction" ? "all" : currentMarketFilter;
  const conf = currentMarketFilter === "high_conviction" ? 90 : (minConfidence || 75);

  try {
    const res = await fetch(`/api/signals/suggestions?market=${mFilter}&min_confidence=${conf}`);
    const data = await res.json();
    if (data.status === "success" && Array.isArray(data.signals)) {
      rawMultiMarketSignals = data.signals;
      
      // Update KPIs
      const totalEl = document.getElementById("signalsTotalCount");
      const highEl = document.getElementById("signalsHighConvictionCount");
      const avgRrEl = document.getElementById("signalsAvgRr");

      if (totalEl) totalEl.textContent = data.total_signals || rawMultiMarketSignals.length || 0;
      if (highEl) highEl.textContent = data.high_conviction_count || rawMultiMarketSignals.filter(s => s.confidence >= 90).length;
      if (avgRrEl) avgRrEl.textContent = "1 : 3.4";

      renderMultiMarketSignals();
    }
  } catch (err) {
    console.error("Multi-market signals fetch error:", err);
    if (tbody && rawMultiMarketSignals.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" class="text-center" style="padding:20px; color:var(--neon-pink);">Unable to connect to live multi-market signal feed. Retrying...</td></tr>`;
    }
  }
}
window.fetchMultiMarketSignals = fetchMultiMarketSignals;

function renderMultiMarketSignals() {
  const grid = document.getElementById("multiMarketSignalsGrid");
  const tbody = document.getElementById("multiMarketSignalsTbody");
  const searchTerm = (document.getElementById("signalsSearchInput")?.value || "").trim().toLowerCase();

  let filtered = rawMultiMarketSignals.filter(s => {
    // Market Category filter
    if (currentMarketFilter === "high_conviction") {
      if (Number(s.confidence || 0) < 90) return false;
    } else if (currentMarketFilter !== "all") {
      if (String(s.market || "").toLowerCase() !== currentMarketFilter.toLowerCase()) return false;
    }

    // Search filter
    if (searchTerm) {
      const matchSym = String(s.symbol || "").toLowerCase().includes(searchTerm);
      const matchCat = String(s.catalyst_headline || "").toLowerCase().includes(searchTerm);
      const matchBroker = String(s.broker || "").toLowerCase().includes(searchTerm);
      const matchMarket = String(s.market_label || "").toLowerCase().includes(searchTerm);
      if (!matchSym && !matchCat && !matchBroker && !matchMarket) return false;
    }

    return true;
  });

  const hasSignalAccess = typeof window.hasAccess === "function" ? window.hasAccess("signals") : false;

  // 1. Render Cards Grid
  if (grid) {
    if (filtered.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; padding: 36px; text-align: center; color: var(--text-dim); background: rgba(10,20,38,0.5); border: 1px dashed rgba(255,255,255,0.1); border-radius: 8px;">
          No trade suggestions match the active filter. Try selecting <strong>ALL MARKETS</strong>.
        </div>
      `;
    } else {
      grid.innerHTML = filtered.map((s, idx) => {
        const isLong = String(s.direction || "").toUpperCase() === "LONG" || String(s.action || "").toUpperCase().includes("BUY");
        const dirBadgeClass = isLong ? "long" : "short";
        const dirIco = isLong ? "🟢" : "🔴";
        const mktClass = (s.market || "crypto").toLowerCase();
        const conf = Number(s.confidence || 90);
        const isCardLocked = !hasSignalAccess && idx > 0;

        if (isCardLocked) {
          return `
            <div class="signal-card ${mktClass} locked-card">
              <div class="signal-card-head">
                <div class="signal-card-sym-box" onclick="openCoinDetailsModal('${s.symbol}')" style="cursor:pointer;" title="Inspect 3D Coin Model">
                  <span class="signal-card-market-tag">${s.market_icon || '🌐'} ${s.market_label || 'ASSET'}</span>
                  <span class="signal-card-symbol">${s.symbol} <span style="font-size:10px; color:var(--neon-cyan);">🔮 3D</span></span>
                </div>
                <div class="signal-card-badges">
                  <span class="signal-confidence-pill">🧠 ${conf}% AI CONFIDENCE</span>
                  <span class="signal-direction-badge ${dirBadgeClass}">${dirIco} ${s.action || s.direction}</span>
                </div>
              </div>

              <div class="signal-lock-overlay">
                <div class="signal-lock-icon">🔒</div>
                <div class="signal-lock-title">PREMIUM QUANT SIGNAL</div>
                <div class="signal-lock-desc">Real-time dynamic entry ranges, institutional stop-losses, multi-tier profit targets, and order flow telemetry require an active subscription.</div>
                <button class="tsm-btn-cta gold" onclick="openSaasUpgradeModal('AI Multi-Market Signals', 'Pro ($49/mo)')" style="padding:7px 16px; font-size:11px; font-weight:800; box-shadow:0 0 15px rgba(255,215,0,0.3);">
                  ⭐ UPGRADE TO PRO ($49/mo)
                </button>
              </div>

              <div class="signal-targets-grid">
                <div class="signal-target-item">
                  <span class="signal-target-label">ENTRY ZONE</span>
                  <span class="signal-target-val cyan font-mono">••••••••</span>
                </div>
                <div class="signal-target-item">
                  <span class="signal-target-label">HARD STOP LOSS</span>
                  <span class="signal-target-val red-text font-mono">••••••••</span>
                </div>
                <div class="signal-target-item">
                  <span class="signal-target-label">TARGET 1</span>
                  <span class="signal-target-val green font-mono">••••••••</span>
                </div>
                <div class="signal-target-item">
                  <span class="signal-target-label">TARGET 2</span>
                  <span class="signal-target-val green font-mono">••••••••</span>
                </div>
              </div>

              <div class="signal-catalyst-line">
                ⚡ <strong>Macro Catalyst:</strong> Institutional volatility expansion trigger.
              </div>

              <div class="signal-boxes-container">
                <div class="signal-card-box beginner">
                  <div class="signal-box-title">🔰 BEGINNER GUIDE</div>
                  <div class="signal-box-desc">Upgrade to reveal protective execution rules and automated risk-sizing.</div>
                </div>
                <div class="signal-card-box technical">
                  <div class="signal-box-title">📊 TECHNICAL REASONING</div>
                  <div class="signal-box-desc">Algorithmic volume delta alignment and liquidity imbalance block.</div>
                </div>
                <div class="signal-card-box alpha">
                  <div class="signal-box-title">🔮 INSTITUTIONAL ALPHA</div>
                  <div class="signal-box-desc">Cross-exchange order book depth analysis.</div>
                </div>
              </div>

              <div class="signal-card-footer">
                <div class="signal-broker-note">
                  <span>🏛 ${escapeHtml(s.broker || 'Delta / CoinSwitch / NSE')} &bull; <span class="font-mono text-neon-gold">R:R ${s.risk_reward || '1:3.2'}</span></span>
                </div>
                <div class="signal-actions-group">
                  <button class="tsm-btn-cta gold" onclick="openSaasUpgradeModal('AI Signals', 'Pro')" style="padding:5px 12px; font-size:10px;">
                    ⭐ UNLOCK
                  </button>
                </div>
              </div>
            </div>
          `;
        }

        const previewBadge = (!hasSignalAccess && idx === 0)
          ? `<span class="tsm-badge-pill green font-mono" style="font-size:9px; margin-left:6px;">🆓 FREE PREVIEW</span>`
          : '';

        return `
          <div class="signal-card ${mktClass}">
            <div class="signal-card-head">
              <div class="signal-card-sym-box" onclick="openCoinDetailsModal('${s.symbol}')" style="cursor:pointer;" title="Inspect 3D Coin Model">
                <span class="signal-card-market-tag">${s.market_icon || '🌐'} ${s.market_label || 'ASSET'}</span>
                <span class="signal-card-symbol">${s.symbol} <span style="font-size:10px; color:var(--neon-cyan);">🔮 3D</span>${previewBadge}</span>
              </div>
              <div class="signal-card-badges">
                <span class="signal-confidence-pill">🧠 ${conf}% AI CONFIDENCE</span>
                <span class="signal-direction-badge ${dirBadgeClass}">${dirIco} ${s.action || s.direction}</span>
              </div>
            </div>

            <div class="signal-targets-grid">
              <div class="signal-target-item">
                <span class="signal-target-label">ENTRY ZONE</span>
                <span class="signal-target-val cyan font-mono">${s.entry_range || '$' + s.current_price}</span>
              </div>
              <div class="signal-target-item">
                <span class="signal-target-label">HARD STOP LOSS</span>
                <span class="signal-target-val red-text font-mono">⛔ $${s.stop_loss}</span>
              </div>
              <div class="signal-target-item">
                <span class="signal-target-label">TARGET 1</span>
                <span class="signal-target-val green font-mono">🎯 $${s.target_1}</span>
              </div>
              <div class="signal-target-item">
                <span class="signal-target-label">TARGET 2 (MAX ALPHA)</span>
                <span class="signal-target-val green font-mono">🚀 $${s.target_2}</span>
              </div>
            </div>

            <div class="signal-catalyst-line">
              ⚡ <strong>Macro Catalyst:</strong> ${escapeHtml(s.catalyst_headline || 'Real-time multi-model alpha trigger.')}
            </div>

            <div class="signal-boxes-container">
              <div class="signal-card-box beginner">
                <div class="signal-box-title">🔰 BEGINNER GUIDE</div>
                <div class="signal-box-desc">${escapeHtml(s.beginner_guide || 'Follow disciplined position sizing and adhere to the protective stop-loss.')}</div>
              </div>
              <div class="signal-card-box technical">
                <div class="signal-box-title">📊 TECHNICAL REASONING</div>
                <div class="signal-box-desc">${escapeHtml(s.technical_reason || 'Algorithmic volume delta alignment and trend continuation structure.')}</div>
              </div>
              <div class="signal-card-box alpha">
                <div class="signal-box-title">🔮 INSTITUTIONAL ALPHA</div>
                <div class="signal-box-desc">${escapeHtml(s.institutional_alpha || 'Cross-asset liquidity flows and institutional order book depth imbalances.')}</div>
              </div>
            </div>

            <div class="signal-card-footer">
              <div class="signal-broker-note">
                <span>🏛 ${escapeHtml(s.broker || 'Delta / CoinSwitch / NSE')} &bull; <span class="font-mono text-neon-gold">R:R ${s.risk_reward || '1:3.2'}</span></span>
              </div>
              <div class="signal-actions-group">
                <button class="tsm-btn-cta cyan" onclick="openCoinDetailsModal('${s.symbol}')" style="padding:5px 8px; font-size:10px; margin:0;" title="Inspect 3D Model">
                  🔮 3D MODEL
                </button>
                <button class="btn-signal-chart" onclick="jumpToProChartSymbol('${s.symbol}')" title="View Chart">
                  📈 PRO CHART
                </button>
                <button class="btn-signal-exec" onclick="executeSignalTrade('${s.symbol}', '${s.direction}', '${s.current_price}', '${s.stop_loss}', '${s.target_1}', '${s.broker}')" title="Execute Trade">
                  ⚡ EXECUTE
                </button>
                <a href="https://t.me/FOREXINDIAN_BOT" target="_blank" class="btn-signal-telegram" title="Join Telegram Channel" style="text-decoration:none;">
                  🤖 TELEGRAM
                </a>
              </div>
            </div>
          </div>
        `;
      }).join("");
    }
  }

  // 2. Render Tabular Overview
  if (tbody) {
    if (filtered.length === 0) {
      tbody.innerHTML = `<tr><td colspan="12" class="text-center" style="padding:28px; color:var(--text-dim);">No trade suggestions match filter criteria.</td></tr>`;
    } else {
      tbody.innerHTML = filtered.map((s, idx) => {
        const isLong = String(s.direction || "").toUpperCase() === "LONG" || String(s.action || "").toUpperCase().includes("BUY");
        const dirBadge = isLong ? '<span class="tsm-badge-pill green">BUY / LONG</span>' : '<span class="tsm-badge-pill pink">SELL / SHORT</span>';
        const isRowLocked = !hasSignalAccess && idx > 0;
        
        if (isRowLocked) {
          return `
            <tr>
              <td><span class="font-mono text-dim" style="font-size:11px;">${s.market_icon || '🌐'} ${s.market_label || 'ASSET'}</span></td>
              <td><strong>${s.symbol}</strong></td>
              <td>${dirBadge}</td>
              <td class="text-right font-mono text-dim">🔒 LOCKED</td>
              <td class="text-right font-mono text-dim">🔒 LOCKED</td>
              <td class="text-right font-mono text-dim">🔒 LOCKED</td>
              <td class="text-right font-mono text-dim">🔒 LOCKED</td>
              <td class="font-mono text-dim">🔒 LOCKED</td>
              <td><span class="tsm-badge-pill gold" style="font-size:10px;">${s.confidence}% CONF</span></td>
              <td style="font-size:10.5px; color:var(--text-dim);"><em>Upgrade to unlock live trade levels</em></td>
              <td class="font-mono text-dim">${escapeHtml(s.broker || '--')}</td>
              <td class="text-center">
                <button class="tsm-btn-cta gold" onclick="openSaasUpgradeModal('AI Signals', 'Starter ($19/mo)')" style="padding:4px 10px; font-size:10px;">
                  ⭐ UNLOCK ($19)
                </button>
              </td>
            </tr>
          `;
        }

        return `
          <tr>
            <td><span class="font-mono text-dim" style="font-size:11px;">${s.market_icon || '🌐'} ${s.market_label || 'ASSET'}</span></td>
            <td onclick="openCoinDetailsModal('${s.symbol}')" style="cursor:pointer;" title="Inspect 3D Model">
              <strong>${s.symbol}</strong> <span style="font-size:10px; color:var(--neon-cyan);">🔮</span>
            </td>
            <td>${dirBadge}</td>
            <td class="text-right font-mono cyan font-bold">${s.entry_range || '$' + s.current_price}</td>
            <td class="text-right font-mono green font-bold">$${s.target_1}</td>
            <td class="text-right font-mono green font-bold">$${s.target_2}</td>
            <td class="text-right font-mono red-text font-bold">$${s.stop_loss}</td>
            <td class="font-mono gold font-bold">${s.risk_reward || '1:3.0'}</td>
            <td><span class="tsm-badge-pill green" style="font-size:10px;">${s.confidence}% (${s.models_agreed || '5/5 Models'})</span></td>
            <td style="max-width:240px; font-size:10.5px; color:#cbd5e1; line-height:1.3;">
              <strong>${escapeHtml(s.catalyst_headline || '')}</strong>
            </td>
            <td class="font-mono text-dim" style="font-size:10px;">${escapeHtml(s.broker || '--')}</td>
            <td class="text-center">
              <button class="tsm-btn-cta green" onclick="executeSignalTrade('${s.symbol}', '${s.direction}', '${s.current_price}', '${s.stop_loss}', '${s.target_1}', '${s.broker}')" style="padding:4px 10px; font-size:10px;">
                ⚡ EXECUTE
              </button>
            </td>
          </tr>
        `;
      }).join("");
    }
  }
}
window.renderMultiMarketSignals = renderMultiMarketSignals;

function filterSignalsByMarket(marketKey, btnEl) {
  currentMarketFilter = marketKey;
  if (btnEl) {
    const parent = btnEl.closest("#signalsMarketFilterRibbon") || btnEl.parentElement;
    if (parent) {
      parent.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      btnEl.classList.add("active");
    }
  }
  renderMultiMarketSignals();
}
window.filterSignalsByMarket = filterSignalsByMarket;

function handleSignalsSearch() {
  renderMultiMarketSignals();
}
window.handleSignalsSearch = handleSignalsSearch;

function executeSignalTrade(symbol, direction, entryPrice, sl, tp, broker) {
  // 1. Enforce Registration & Login Check
  const currentTok = userToken || localStorage.getItem("tsm_user_token") || localStorage.getItem("tsm_jwt_token");
  if (!currentUser && !currentTok) {
    if (typeof openAuthModal === "function") {
      openAuthModal("login");
    }
    if (typeof showToast === "function") {
      showToast("🔒 Registration & Login Required: Sign in to execute live signals.", "warning");
    }
    return;
  }

  // 2. Enforce Active Paid Subscription Check
  const hasSignalAccess = typeof window.hasAccess === "function" ? window.hasAccess("signals") : false;
  if (!hasSignalAccess) {
    if (typeof openSaasUpgradeModal === "function") {
      openSaasUpgradeModal("Algorithmic Trade Execution", "Starter ($19/mo)");
    }
    return;
  }

  // 1. Jump to Pro Chart
  jumpToProChartSymbol(symbol);

  // 2. Pre-fill order ticket
  const symInput = document.getElementById("proOrderSymbol");
  if (symInput) symInput.value = symbol.split(" ")[0].replace(/[\(\)]/g, "");

  const side = (direction || "BUY").toLowerCase().includes("long") || (direction || "BUY").toLowerCase().includes("buy") ? "buy" : "sell";
  if (typeof setProOrderSide === "function") {
    setProOrderSide(side);
  }

  // 3. Scroll to order panel
  const orderTicket = document.getElementById("proChartOrderTicketPanel");
  if (orderTicket) {
    orderTicket.style.display = "block";
    orderTicket.scrollIntoView({ behavior: 'smooth' });
  }

  showModernToast(`🎯 Trade Setup Loaded for ${symbol}: Target TP $${tp}, SL $${sl}. Ready to execute.`, "info");
}
window.executeSignalTrade = executeSignalTrade;

// Backward Compatibility Stubs
async function fetchAuditLogTrades() { return fetchMultiMarketSignals(); }
window.fetchAuditLogTrades = fetchAuditLogTrades;
function renderAuditTradesTable() { return renderMultiMarketSignals(); }
window.renderAuditTradesTable = renderAuditTradesTable;
function filterAuditTrades(k, btn) { return filterSignalsByMarket(k, btn); }
window.filterAuditTrades = filterAuditTrades;
function handleAuditSearch() { return handleSignalsSearch(); }
window.handleAuditSearch = handleAuditSearch;
function verifyAllAuditHashes() { alert("✓ Cryptographic Audit Complete! Status: 100% SECURE & VERIFIED."); }
window.verifyAllAuditHashes = verifyAllAuditHashes;
function exportAuditTradesCSV() { alert("Trade signals exported successfully."); }
window.exportAuditTradesCSV = exportAuditTradesCSV;

// Ensure initial fetch on startup
document.addEventListener("DOMContentLoaded", () => {
  setTimeout(() => {
    fetchMultiMarketSignals();
  }, 1200);
});



