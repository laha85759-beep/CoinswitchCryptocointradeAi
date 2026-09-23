/**
 * admin.js — Operations Admin Cockpit Controller
 * TheSmartMag Quant Trading Platform
 */

let tradersList = [];

document.addEventListener("DOMContentLoaded", () => {
  initAdminClock();
  setupAdminTabNavigation();
  const token = getAuthToken();
  if (!token) {
    showAdmLoginModal();
  } else {
    loadAdminTraders();
    checkAdminRole();
  }
});

function initAdminClock() {
  function update() {
    const now = new Date();
    const utcStr = now.toUTCString().split(" ")[4] + " UTC";
    const istStr = now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false }) + " IST";
    const el = document.getElementById("admClock");
    if (el) el.textContent = `${utcStr} | ${istStr}`;
  }
  update();
  setInterval(update, 1000);
}

function getAuthToken() {
  let token = localStorage.getItem("tsm_admin_token") || 
              sessionStorage.getItem("tsm_admin_token") || 
              localStorage.getItem("tsm_user_token") || 
              localStorage.getItem("tsm_jwt_token") || 
              localStorage.getItem("token") || 
              localStorage.getItem("auth_token") || 
              localStorage.getItem("access_token") || "";
  if (!token) {
    const match = document.cookie.match(new RegExp('(^| )(auth_token|tsm_token|access_token)=([^;]+)'));
    if (match) token = match[3];
  }
  return token;
}

function showAdmLoginModal() {
  const modal = document.getElementById("admLoginModal");
  if (modal) modal.style.display = "flex";
}

function hideAdmLoginModal() {
  const modal = document.getElementById("admLoginModal");
  if (modal) modal.style.display = "none";
}

async function handleAdmLogin(e) {
  e.preventDefault();
  const user = document.getElementById("admLoginUser").value.trim();
  const pass = document.getElementById("admLoginPass").value.trim();
  const errBox = document.getElementById("admLoginErrorMsg");
  const submitBtn = document.getElementById("admLoginSubmitBtn");

  if (submitBtn) { submitBtn.textContent = "VERIFYING OPERATIONS ACCESS..."; submitBtn.disabled = true; }
  if (errBox) errBox.style.display = "none";

  try {
    const res = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: user, password: pass })
    });
    const data = await res.json();
    if (res.ok && data.status === "success" && (data.token || data.legacy_token)) {
      const tok = data.token || data.legacy_token;
      localStorage.setItem("tsm_admin_token", tok);
      sessionStorage.setItem("tsm_admin_token", tok);
      localStorage.setItem("auth_token", tok);
      if (data.user) {
        localStorage.setItem("user", JSON.stringify(data.user));
        if (data.user.email) {
          const emailEl = document.getElementById("admUserEmail");
          if (emailEl) emailEl.textContent = data.user.email;
        }
      }
      hideAdmLoginModal();
      loadAdminTraders();
      checkAdminRole();
    } else {
      if (errBox) {
        errBox.textContent = data.message || "Invalid administrative credentials.";
        errBox.style.display = "block";
      }
    }
  } catch (err) {
    if (errBox) {
      errBox.textContent = "Network error communicating with auth server.";
      errBox.style.display = "block";
    }
  } finally {
    if (submitBtn) { submitBtn.textContent = "AUTHENTICATE OPERATIONS COCKPIT"; submitBtn.disabled = false; }
  }
}

async function admFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  options.headers = headers;
  options.credentials = "include";
  const res = await fetch(url, options);
  if (res.status === 401 || res.status === 403) {
    showAdmLoginModal();
  }
  return res;
}

function handleAdminLogout() {
  localStorage.removeItem("tsm_admin_token");
  sessionStorage.removeItem("tsm_admin_token");
  localStorage.removeItem("tsm_user_token");
  localStorage.removeItem("token");
  localStorage.removeItem("auth_token");
  localStorage.removeItem("user");
  document.cookie = "auth_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  document.cookie = "tsm_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT";
  window.location.href = "/";
}

async function checkAdminRole() {
  try {
    const res = await admFetch("/api/auth/me");
    if (res.ok) {
      const data = await res.json();
      const user = data.user || {};
      if (user.email) {
        document.getElementById("admUserEmail").textContent = user.email;
      }
      if (user.role === "superadmin") {
        document.getElementById("admRoleBadge").textContent = "SUPER ADMIN";
        document.getElementById("admSuperAdminBtn").style.display = "inline-flex";
      } else {
        document.getElementById("admRoleBadge").textContent = "OPERATIONS ADMIN";
      }
    }
  } catch (e) {}
}

function setupAdminTabNavigation() {
  const navItems = document.querySelectorAll(".adm-nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      navItems.forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      document.querySelectorAll(".adm-tab-content").forEach(c => c.classList.remove("active"));
      const target = document.getElementById(`tab-${tabId}`);
      if (target) target.classList.add("active");
    });
  });
}

async function loadAdminTraders() {
  try {
    const res = await admFetch("/api/admin/saas/users");
    if (!res.ok) return;
    const data = await res.json();
    tradersList = data.users || [];

    const selects = ["keysUserSelect", "profitUserSelect", "viewerUserSelect", "journalUserSelect"];
    selects.forEach(sId => {
      const el = document.getElementById(sId);
      if (el) {
        const cur = el.value;
        el.innerHTML = `<option value="">-- Choose Trader (${tradersList.length}) --</option>`;
        tradersList.forEach(t => {
          el.innerHTML += `<option value="${t.id}">#${t.id} - ${escapeHtml(t.email)} (${t.name || 'Trader'})</option>`;
        });
        if (cur) el.value = cur;
      }
    });
  } catch (err) {
    console.error("Failed to load traders:", err);
  }
}

// ── TAB 1: ASSIGN API KEYS ────────────────────────────────────────────────
async function handleKeysUserSelect() {
  const userId = document.getElementById("keysUserSelect").value;
  if (!userId) return;

  try {
    const res = await admFetch(`/api/admin/user/${userId}/details`);
    if (res.ok) {
      const data = await res.json();
      const keys = data.api_keys || {};
      if (keys.has_coinswitch) {
        document.getElementById("csApiKey").placeholder = `Current: ${keys.cs_key_masked}`;
      } else {
        document.getElementById("csApiKey").placeholder = "e.g. cs_key_...";
      }
      if (keys.has_delta) {
        document.getElementById("deltaApiKey").placeholder = `Current: ${keys.delta_key_masked}`;
      } else {
        document.getElementById("deltaApiKey").placeholder = "e.g. delta_key_...";
      }
    }
  } catch (e) {}
}

async function handleAssignKeys(e) {
  e.preventDefault();
  const userId = document.getElementById("keysUserSelect").value;
  if (!userId) {
    alert("Please select a target trader.");
    return;
  }
  const cs_api_key = document.getElementById("csApiKey").value.trim();
  const cs_api_secret = document.getElementById("csApiSecret").value.trim();
  const delta_api_key = document.getElementById("deltaApiKey").value.trim();
  const delta_api_secret = document.getElementById("deltaApiSecret").value.trim();

  try {
    const res = await admFetch(`/api/admin/user/${userId}/api-keys`, {
      method: "POST",
      body: JSON.stringify({ cs_api_key, cs_api_secret, delta_api_key, delta_api_secret })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ Exchange API keys saved for Trader #${userId}!`);
      document.getElementById("assignKeysForm").reset();
    } else {
      alert(`Error: ${data.message || 'Failed to save keys'}`);
    }
  } catch (err) {
    alert("Network error saving keys");
  }
}

// ── TAB 2: USER PROFIT UPDATE ─────────────────────────────────────────────
async function handleProfitUpdate(e) {
  e.preventDefault();
  const userId = document.getElementById("profitUserSelect").value;
  const symbol = document.getElementById("profitSymbol").value.trim();
  const realized_pnl = parseFloat(document.getElementById("profitAmount").value);
  const exchange = document.getElementById("profitExchange").value;
  const direction = document.getElementById("profitDirection").value;
  const notes = document.getElementById("profitNotes").value.trim();

  if (!userId) {
    alert("Please choose a trader.");
    return;
  }

  try {
    const res = await admFetch(`/api/admin/user/${userId}/update-profit`, {
      method: "POST",
      body: JSON.stringify({ symbol, realized_pnl, exchange, direction, notes })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ Profit of $${realized_pnl.toFixed(2)} recorded for Trader #${userId}!`);
      document.getElementById("profitUpdateForm").reset();
    } else {
      alert(`Error: ${data.message || 'Failed to record profit'}`);
    }
  } catch (err) {
    alert("Network error updating profit");
  }
}

// ── TAB 3: TRADER DASHBOARD VIEWER ────────────────────────────────────────
async function loadTraderDashboardView() {
  const userId = document.getElementById("viewerUserSelect").value;
  const container = document.getElementById("traderDashboardContainer");
  if (!userId) {
    container.innerHTML = `<p class="adm-placeholder-text">Please select a trader from the dropdown above to view their live dashboard.</p>`;
    return;
  }

  container.innerHTML = `<p class="adm-placeholder-text">Loading trader portfolio and performance...</p>`;

  try {
    const res = await admFetch(`/api/admin/user/${userId}/details`);
    if (!res.ok) {
      container.innerHTML = `<p class="adm-placeholder-text">Failed to load trader data.</p>`;
      return;
    }
    const data = await res.json();
    const u = data.user || {};
    const keys = data.api_keys || {};
    const trades = u.open_trades || [];

    let tradesHtml = "";
    if (trades.length === 0) {
      tradesHtml = `<p style="font-size: 12px; color: var(--adm-text-muted);">No open trades currently active for this account.</p>`;
    } else {
      tradesHtml = `
        <table style="width: 100%; font-size: 12px; border-collapse: collapse; margin-top: 10px;">
          <thead>
            <tr style="text-align: left; color: var(--adm-text-muted); border-bottom: 1px solid var(--adm-border);">
              <th style="padding: 6px;">Symbol</th>
              <th style="padding: 6px;">Side</th>
              <th style="padding: 6px;">Entry</th>
              <th style="padding: 6px;">SL</th>
              <th style="padding: 6px;">TP</th>
            </tr>
          </thead>
          <tbody>
            ${trades.map(t => `
              <tr style="border-bottom: 1px solid rgba(255,255,255,0.05);">
                <td style="padding: 6px;"><strong>${escapeHtml(t.symbol)}</strong></td>
                <td style="padding: 6px; color: ${t.direction === 'long' ? 'var(--adm-success)' : 'var(--adm-danger)'};">${(t.direction || 'LONG').toUpperCase()}</td>
                <td style="padding: 6px;">$${t.entry_price || '--'}</td>
                <td style="padding: 6px; color: var(--adm-danger);">$${t.sl_price || '--'}</td>
                <td style="padding: 6px; color: var(--adm-success);">$${t.tp_price || '--'}</td>
              </tr>
            `).join('')}
          </tbody>
        </table>
      `;
    }

    container.innerHTML = `
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin-bottom: 20px;">
        <div class="adm-box">
          <div style="font-size: 11px; color: var(--adm-text-muted);">TRADER EMAIL</div>
          <div style="font-size: 14px; font-weight: 700; color: #fff; margin-top: 4px;">${escapeHtml(u.email || '--')}</div>
        </div>
        <div class="adm-box">
          <div style="font-size: 11px; color: var(--adm-text-muted);">CURRENT PLAN</div>
          <div style="font-size: 14px; font-weight: 700; color: #93c5fd; margin-top: 4px;">${(u.plan_name || 'free').toUpperCase()}</div>
        </div>
        <div class="adm-box">
          <div style="font-size: 11px; color: var(--adm-text-muted);">TOTAL SPENT</div>
          <div style="font-size: 14px; font-weight: 700; color: var(--adm-success); margin-top: 4px;">$${(u.total_spent || 0).toFixed(2)}</div>
        </div>
        <div class="adm-box">
          <div style="font-size: 11px; color: var(--adm-text-muted);">EXCHANGES CONNECTED</div>
          <div style="font-size: 13px; font-weight: 600; margin-top: 4px;">
            CoinSwitch: ${keys.has_coinswitch ? '✅' : '❌'} | Delta: ${keys.has_delta ? '✅' : '❌'}
          </div>
        </div>
      </div>

      <div class="adm-card">
        <div class="adm-card-header">
          <h3>Active Positions</h3>
        </div>
        <div class="adm-card-body">
          ${tradesHtml}
        </div>
      </div>
    `;
  } catch (err) {
    container.innerHTML = `<p class="adm-placeholder-text">Error fetching trader details.</p>`;
  }
}

// ── TAB 4: TRADING JOURNAL ────────────────────────────────────────────────
async function handleJournalSubmit(e) {
  e.preventDefault();
  const userId = document.getElementById("journalUserSelect").value;
  const symbol = document.getElementById("journalSymbol").value.trim().toUpperCase();
  const direction = document.getElementById("journalDirection").value;
  const entry_price = parseFloat(document.getElementById("journalEntryPrice").value);
  const exit_price = parseFloat(document.getElementById("journalExitPrice").value);
  const pnl = parseFloat(document.getElementById("journalPnl").value);
  const setup_tag = document.getElementById("journalSetupTag").value;
  const emotion = document.getElementById("journalEmotion").value;
  const notes = document.getElementById("journalNotes").value.trim();

  if (!userId) {
    alert("Please choose a trader.");
    return;
  }

  try {
    const res = await admFetch("/api/journal/entry", {
      method: "POST",
      body: JSON.stringify({
        user_id: parseInt(userId),
        symbol,
        direction,
        entry_price,
        exit_price,
        pnl,
        setup_tag,
        emotion,
        notes,
        trade_date: new Date().toISOString().split("T")[0]
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ JournalIt entry logged successfully!`);
      document.getElementById("journalForm").reset();
    } else {
      alert(`Error: ${data.message || 'Failed to record entry'}`);
    }
  } catch (err) {
    alert("Network error submitting journal entry");
  }
}

// ── TAB 6: MANUAL TRADE ORDER ─────────────────────────────────────────────
async function handleManualTradeOrder(e) {
  e.preventDefault();
  const exchange = document.getElementById("tradeExchange").value;
  const symbol = document.getElementById("tradeSymbol").value.trim().toUpperCase();
  const side = document.getElementById("tradeSide").value;
  const order_type = document.getElementById("tradeType").value;
  const amount_usd = parseFloat(document.getElementById("tradeAmount").value);
  const sl_pct = parseFloat(document.getElementById("tradeSl").value);

  if (!confirm(`Confirm manual ${side.toUpperCase()} order on ${exchange.toUpperCase()} for $${amount_usd} of ${symbol}?`)) return;

  try {
    const res = await admFetch("/api/admin/manual-trade", {
      method: "POST",
      body: JSON.stringify({ exchange, symbol, side, order_type, amount_usd, sl_pct })
    });
    const data = await res.json();
    alert(`Order dispatched: ${data.message || 'Order placed successfully'}`);
  } catch (err) {
    alert("Network error submitting manual trade");
  }
}

// ── TAB 7: AUTOBOT SCAN CYCLE ─────────────────────────────────────────────
async function triggerAdminScanCycle() {
  try {
    const res = await admFetch("/api/admin/trigger-cycle", { method: "POST" });
    const data = await res.json();
    alert(`⚡ Scan triggered: ${data.message || 'Cycle executed in background'}`);
  } catch (err) {
    alert("Network error triggering scan cycle");
  }
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
