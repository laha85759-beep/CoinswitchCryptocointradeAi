/**
 * superadmin.js — Sovereign Super Admin Command Center Controller
 * TheSmartMag Quant AI Multi-Tenant Architecture
 */

let allUsers = [];
let allBannedIps = [];
let selectedUserIdForServices = null;

document.addEventListener("DOMContentLoaded", () => {
  initClock();
  setupTabNavigation();
  const token = getAuthToken();
  if (!token) {
    showLoginModal();
  } else {
    loadOverviewData();
    loadUsersTable();
    loadPaymentsTable();
    loadBannedIpsTable();
  }
  setInterval(loadOverviewData, 30000); // 30s auto-refresh
});

// ── 1. CLOCK & TELEMETRY ──────────────────────────────────────────────────
function initClock() {
  function updateTime() {
    const now = new Date();
    const utcStr = now.toUTCString().split(" ")[4] + " UTC";
    const istStr = now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour12: false }) + " IST";
    const el = document.getElementById("saLiveTime");
    if (el) el.textContent = `${utcStr} | ${istStr}`;
  }
  updateTime();
  setInterval(updateTime, 1000);
}

// ── 2. AUTH & REQUEST HELPER ──────────────────────────────────────────────
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

function showLoginModal() {
  const modal = document.getElementById("saLoginModal");
  if (modal) modal.style.display = "flex";
}

function hideLoginModal() {
  const modal = document.getElementById("saLoginModal");
  if (modal) modal.style.display = "none";
}

async function handleSaLogin(e) {
  e.preventDefault();
  const user = document.getElementById("saLoginUser").value.trim();
  const pass = document.getElementById("saLoginPass").value.trim();
  const errBox = document.getElementById("saLoginErrorMsg");
  const submitBtn = document.getElementById("saLoginSubmitBtn");

  if (submitBtn) { submitBtn.textContent = "VERIFYING SECURITY TOKENS..."; submitBtn.disabled = true; }
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
          const emailEl = document.getElementById("saAdminEmail");
          if (emailEl) emailEl.textContent = data.user.email;
        }
      }
      hideLoginModal();
      loadOverviewData();
      loadUsersTable();
      loadPaymentsTable();
      loadBannedIpsTable();
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
    if (submitBtn) { submitBtn.textContent = "AUTHENTICATE SUPER ADMIN"; submitBtn.disabled = false; }
  }
}

async function saFetch(url, options = {}) {
  const token = getAuthToken();
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  options.headers = headers;
  options.credentials = "include";

  const res = await fetch(url, options);
  if (res.status === 401 || res.status === 403) {
    showLoginModal();
  }
  return res;
}

function handleLogout() {
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

// ── 3. TAB NAVIGATION ─────────────────────────────────────────────────────
function setupTabNavigation() {
  const navItems = document.querySelectorAll(".sa-nav-item");
  navItems.forEach(item => {
    item.addEventListener("click", () => {
      const tabId = item.getAttribute("data-tab");
      navItems.forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      document.querySelectorAll(".sa-tab-content").forEach(content => {
        content.classList.remove("active");
      });
      const activeContent = document.getElementById(`tab-${tabId}`);
      if (activeContent) activeContent.classList.add("active");
    });
  });
}

// ── 4. OVERVIEW DATA & KPIS ───────────────────────────────────────────────
async function loadOverviewData() {
  try {
    // 1. Health & Memory
    const healthRes = await saFetch("/healthz");
    if (healthRes.ok) {
      const hData = await healthRes.json();
      if (hData.ram_usage_mb) {
        document.getElementById("saRamText").textContent = 
          `${hData.ram_usage_mb} MB / ${hData.ram_limit_mb || 512} MB (${hData.ram_pct || 35}%)`;
      }
    }

    // 2. Metrics & Revenue
    const metricsRes = await saFetch("/api/admin/saas/metrics");
    if (metricsRes.ok) {
      const mData = await metricsRes.json();
      const m = mData.metrics || {};
      document.getElementById("kpiTotalUsers").textContent = m.total_users || 0;
      document.getElementById("kpiActiveUsers").textContent = m.active_subscribers || 0;
      document.getElementById("kpiTotalRevenue").textContent = `$${(m.total_volume_usd || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    }

    // 3. Bot Status
    const botRes = await saFetch("/api/admin/status");
    if (botRes.ok) {
      const bData = await botRes.json();
      const botActive = bData.bot_active !== false;
      document.getElementById("kpiBotStatus").textContent = botActive ? "ACTIVE" : "PAUSED";
      document.getElementById("kpiBotStatus").style.color = botActive ? "var(--sa-success)" : "var(--sa-danger)";
      document.getElementById("masterBotStatusHeader").textContent = `Master Trading Bot: ${botActive ? 'ACTIVE' : 'PAUSED'}`;
      document.getElementById("masterBotToggleBtn").textContent = botActive ? "PAUSE MASTER BOT" : "RESUME MASTER BOT";
      document.getElementById("masterBotToggleBtn").className = botActive ? "sa-btn-danger" : "sa-btn-success";
    }

    // 4. Banned count
    const bannedRes = await saFetch("/api/admin/security/banned-ips");
    if (bannedRes.ok) {
      const bData = await bannedRes.json();
      const count = bData.count || 0;
      document.getElementById("kpiBannedIps").textContent = count;
      document.getElementById("saBannedCountBadge").textContent = count;
    }
  } catch (err) {
    console.error("Overview data load error:", err);
  }
}

// ── 5. USER DIRECTORY & CRM ───────────────────────────────────────────────
async function loadUsersTable() {
  try {
    const res = await saFetch("/api/admin/saas/users");
    if (!res.ok) return;
    const data = await res.json();
    allUsers = data.users || [];

    document.getElementById("saUserCountBadge").textContent = allUsers.length;
    populateUserSelects();
    renderUsersTable(allUsers);
  } catch (err) {
    console.error("Users load error:", err);
  }
}

function renderUsersTable(users) {
  const tbody = document.getElementById("usersTableBody");
  if (!tbody) return;
  tbody.innerHTML = "";

  if (users.length === 0) {
    tbody.innerHTML = `<tr><td colspan="8" class="sa-text-center">No registered users found.</td></tr>`;
    return;
  }

  users.forEach(u => {
    const tr = document.createElement("tr");
    const roleBadge = u.role === "superadmin" 
      ? `<span class="sa-badge sa-badge-danger">SUPER ADMIN</span>` 
      : (u.role === "admin" ? `<span class="sa-badge sa-badge-warning">ADMIN</span>` : `<span class="sa-badge sa-badge-role">TRADER</span>`);
    
    const statusBadge = u.is_active 
      ? `<span class="sa-badge sa-badge-success">ACTIVE</span>` 
      : `<span class="sa-badge sa-badge-danger">SUSPENDED</span>`;

    const subBadge = u.is_sub_active 
      ? `<span class="sa-badge sa-badge-success">${u.subscription_status.toUpperCase()}</span>` 
      : `<span class="sa-badge sa-badge-warning">${u.subscription_status.toUpperCase()}</span>`;

    tr.innerHTML = `
      <td><strong>#${u.id}</strong></td>
      <td>
        <div style="font-weight: 600; color: #fff;">${escapeHtml(u.name || '')}</div>
        <div style="font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--sa-text-muted);">${escapeHtml(u.email)}</div>
      </td>
      <td>${roleBadge}</td>
      <td><span class="sa-badge sa-badge-role">${(u.plan_id || 'free').toUpperCase()}</span></td>
      <td>${subBadge}</td>
      <td><strong style="color: var(--sa-accent);">$${(u.total_spent_usd || 0).toFixed(2)}</strong></td>
      <td>
        <label class="sa-switch">
          <input type="checkbox" ${u.is_active ? 'checked' : ''} onchange="toggleUserActiveState(${u.id}, this.checked)">
          <span class="sa-slider"></span>
        </label>
      </td>
      <td>
        <div style="display: flex; gap: 6px;">
          <button class="sa-btn-sm sa-btn-secondary" onclick="openUserCrmDrawer(${u.id})" title="View Full CRM Details">👤 CRM</button>
          <button class="sa-btn-sm sa-btn-primary" onclick="quickSelectUserForServices(${u.id})" title="Configure Services">🔐 Services</button>
        </div>
      </td>
    `;
    tbody.appendChild(tr);
  });
}

function filterUsersTable() {
  const query = (document.getElementById("userSearchInput").value || "").toLowerCase().trim();
  const roleFilter = document.getElementById("userRoleFilter").value;
  const planFilter = document.getElementById("userPlanFilter").value;
  const statusFilter = document.getElementById("userStatusFilter").value;

  const filtered = allUsers.filter(u => {
    const matchesQuery = !query || 
      (u.name && u.name.toLowerCase().includes(query)) || 
      (u.email && u.email.toLowerCase().includes(query)) || 
      String(u.id).includes(query);

    const matchesRole = roleFilter === "all" || u.role === roleFilter;
    const matchesPlan = planFilter === "all" || (u.plan_id || "free") === planFilter;
    const matchesStatus = statusFilter === "all" || 
      (statusFilter === "active" && u.is_active) || 
      (statusFilter === "suspended" && !u.is_active);

    return matchesQuery && matchesRole && matchesPlan && matchesStatus;
  });

  renderUsersTable(filtered);
}

async function toggleUserActiveState(userId, active) {
  try {
    const res = await saFetch("/api/admin/users/toggle-status", {
      method: "POST",
      body: JSON.stringify({ user_id: userId })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(data.message || "Failed to toggle user status");
      loadUsersTable();
    }
  } catch (err) {
    console.error("Toggle user error:", err);
  }
}

function populateUserSelects() {
  const provSelect = document.getElementById("provisionUserSelect");
  const subSelect = document.getElementById("quickSubUser");
  
  if (provSelect) {
    const currentVal = provSelect.value;
    provSelect.innerHTML = `<option value="">-- Choose User (${allUsers.length} total) --</option>`;
    allUsers.forEach(u => {
      provSelect.innerHTML += `<option value="${u.id}">#${u.id} - ${escapeHtml(u.email)} (${u.name || 'Trader'})</option>`;
    });
    if (currentVal) provSelect.value = currentVal;
  }

  if (subSelect) {
    const currentVal = subSelect.value;
    subSelect.innerHTML = `<option value="">-- Choose User --</option>`;
    allUsers.forEach(u => {
      subSelect.innerHTML += `<option value="${u.id}">#${u.id} - ${escapeHtml(u.email)}</option>`;
    });
    if (currentVal) subSelect.value = currentVal;
  }
}

// ── 6. CREATE NEW USER MODAL ──────────────────────────────────────────────
function openCreateUserModal() {
  document.getElementById("createUserModal").classList.add("active");
}

function closeCreateUserModal() {
  document.getElementById("createUserModal").classList.remove("active");
}

async function handleCreateUserSubmit(e) {
  e.preventDefault();
  const name = document.getElementById("newUserName").value.trim();
  const email = document.getElementById("newUserEmail").value.trim();
  const password = document.getElementById("newUserPassword").value;
  const role = document.getElementById("newUserRole").value;
  const plan_name = document.getElementById("newUserPlan").value;

  const services = {
    ai_signals: document.getElementById("nu_ai_signals").checked,
    india_fo: document.getElementById("nu_india_fo").checked,
    forex_macro: document.getElementById("nu_forex_macro").checked,
    autobot_trading: document.getElementById("nu_autobot_trading").checked,
    prop_firms: document.getElementById("nu_prop_firms").checked,
    journal_it: document.getElementById("nu_journal_it").checked,
    strategy_builder: document.getElementById("nu_strategy_builder").checked,
    nvidia_super_brain: document.getElementById("nu_nvidia_super_brain").checked,
  };

  try {
    const res = await saFetch("/api/admin/users/create", {
      method: "POST",
      body: JSON.stringify({ name, email, password, role, plan_name, services })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ User ${email} successfully created!`);
      closeCreateUserModal();
      document.getElementById("createUserForm").reset();
      loadUsersTable();
      loadOverviewData();
    } else {
      alert(`Error: ${data.message || 'Failed to create user'}`);
    }
  } catch (err) {
    alert("Network error creating user");
  }
}

// ── 7. SERVICE PROVISIONING MATRIX ─────────────────────────────────────────
function quickSelectUserForServices(userId) {
  // Switch to services tab
  const btn = document.querySelector('.sa-nav-item[data-tab="services"]');
  if (btn) btn.click();

  const provSelect = document.getElementById("provisionUserSelect");
  if (provSelect) {
    provSelect.value = String(userId);
    loadUserServicesMatrix();
  }
}

function loadUserServicesMatrix() {
  const provSelect = document.getElementById("provisionUserSelect");
  const userId = provSelect.value;
  selectedUserIdForServices = userId ? parseInt(userId) : null;

  const banner = document.getElementById("selectedUserBanner");
  if (!selectedUserIdForServices) {
    banner.style.display = "none";
    resetServiceSwitches(false);
    return;
  }

  const user = allUsers.find(u => u.id === selectedUserIdForServices);
  if (!user) return;

  banner.style.display = "flex";
  document.getElementById("provisionUserEmail").textContent = user.email;
  document.getElementById("provisionUserPlan").textContent = (user.plan_id || "free").toUpperCase();
  document.getElementById("provisionUserRole").textContent = user.role.toUpperCase();

  const perms = user.permissions || {};
  // If user has enterprise or superadmin, default to true unless override says otherwise
  const isSuper = user.role === "superadmin";

  const servicesList = [
    "ai_signals", "india_fo", "forex_macro", "autobot_trading",
    "prop_firms", "journal_it", "strategy_builder", "nvidia_super_brain"
  ];

  servicesList.forEach(s => {
    const el = document.getElementById(`svc_${s}`);
    if (el) {
      if (s in perms) {
        el.checked = Boolean(perms[s]);
      } else {
        // default enabled for paid plans or superadmin
        el.checked = isSuper || (user.plan_id && user.plan_id !== "free");
      }
    }
  });
}

function resetServiceSwitches(val) {
  const servicesList = [
    "ai_signals", "india_fo", "forex_macro", "autobot_trading",
    "prop_firms", "journal_it", "strategy_builder", "nvidia_super_brain"
  ];
  servicesList.forEach(s => {
    const el = document.getElementById(`svc_${s}`);
    if (el) el.checked = val;
  });
}

async function toggleUserService(serviceName) {
  if (!selectedUserIdForServices) {
    alert("Please select a user first.");
    return;
  }
  const el = document.getElementById(`svc_${serviceName}`);
  const enabled = el ? el.checked : true;

  try {
    const res = await saFetch("/api/admin/saas/toggle-permission", {
      method: "POST",
      body: JSON.stringify({
        user_id: selectedUserIdForServices,
        service_name: serviceName,
        enabled: enabled
      })
    });
    const data = await res.json();
    if (!res.ok) {
      alert(`Error: ${data.message || 'Failed to update service'}`);
      if (el) el.checked = !enabled; // revert
    } else {
      // update cached user object
      const user = allUsers.find(u => u.id === selectedUserIdForServices);
      if (user) {
        if (!user.permissions) user.permissions = {};
        user.permissions[serviceName] = enabled;
      }
    }
  } catch (err) {
    alert("Network error updating service toggle");
  }
}

async function bulkToggleServices(enabled) {
  if (!selectedUserIdForServices) {
    alert("Please select a user first.");
    return;
  }
  const servicesList = [
    "ai_signals", "india_fo", "forex_macro", "autobot_trading",
    "prop_firms", "journal_it", "strategy_builder", "nvidia_super_brain"
  ];
  for (const s of servicesList) {
    const el = document.getElementById(`svc_${s}`);
    if (el) el.checked = enabled;
    await saFetch("/api/admin/saas/toggle-permission", {
      method: "POST",
      body: JSON.stringify({ user_id: selectedUserIdForServices, service_name: s, enabled })
    });
  }
  alert(`✅ All 8 services set to ${enabled ? 'ENABLED' : 'DISABLED'} for User #${selectedUserIdForServices}`);
}

// ── 8. SUBSCRIPTION & PAYMENTS ─────────────────────────────────────────────
async function handleQuickSubGrant(e) {
  e.preventDefault();
  const userId = document.getElementById("quickSubUser").value;
  const plan_id = document.getElementById("quickSubPlan").value;
  const billing_interval = document.getElementById("quickSubInterval").value;
  const amount = parseFloat(document.getElementById("quickSubAmount").value || 0);
  const payment_method = document.getElementById("quickSubMethod").value;

  if (!userId) {
    alert("Please choose a user.");
    return;
  }

  let duration_days = 30;
  if (billing_interval === "quarterly") duration_days = 90;
  if (billing_interval === "yearly") duration_days = 365;
  if (billing_interval === "lifetime") duration_days = 3650;

  try {
    const res = await saFetch(`/api/admin/user/${userId}/subscription`, {
      method: "POST",
      body: JSON.stringify({
        plan_id,
        billing_interval,
        status: "active",
        duration_days,
        amount,
        payment_method
      })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ Subscription ${plan_id.toUpperCase()} granted to User #${userId}!`);
      loadUsersTable();
      loadPaymentsTable();
      loadOverviewData();
    } else {
      alert(`Error: ${data.message || 'Failed to grant subscription'}`);
    }
  } catch (err) {
    alert("Network error updating subscription");
  }
}

async function loadPaymentsTable() {
  try {
    const res = await saFetch("/api/admin/saas/payments");
    if (!res.ok) return;
    const data = await res.json();
    const payments = data.payments || [];

    const tbody = document.getElementById("paymentsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (payments.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" class="sa-text-center">No payment transactions recorded yet.</td></tr>`;
      return;
    }

    payments.forEach(p => {
      const tr = document.createElement("tr");
      const dateStr = p.created_at ? new Date(p.created_at * 1000).toLocaleString() : '--';
      tr.innerHTML = `
        <td><strong style="font-family: 'JetBrains Mono', monospace;">#${p.id}</strong></td>
        <td>
          <div style="font-weight: 600;">${escapeHtml(p.name || '')}</div>
          <div style="font-size: 11px; color: var(--sa-text-muted);">${escapeHtml(p.email || 'User #' + p.user_id)}</div>
        </td>
        <td><strong style="color: var(--sa-success); font-family: 'JetBrains Mono', monospace;">$${(p.amount || 0).toFixed(2)}</strong></td>
        <td><span class="sa-badge sa-badge-role">${(p.plan_id || 'pro').toUpperCase()}</span></td>
        <td><span style="font-size: 11px; color: #a5b4fc;">${escapeHtml(p.payout_account || 'Rise USD')}</span></td>
        <td><span class="sa-badge sa-badge-success">${(p.status || 'succeeded').toUpperCase()}</span></td>
        <td style="font-size: 11px; color: var(--sa-text-muted);">${dateStr}</td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Payments load error:", err);
  }
}

// ── 9. MASTER BOT & RISK ACTIONS ──────────────────────────────────────────
async function toggleMasterBot() {
  if (!confirm("Are you sure you want to toggle the Master Autonomous Trading Bot state?")) return;
  try {
    const res = await saFetch("/api/admin/bot-toggle", { method: "POST" });
    const data = await res.json();
    alert(`Bot state toggled: ${data.message || 'Done'}`);
    loadOverviewData();
  } catch (err) {
    alert("Network error toggling bot");
  }
}

async function panicFlattenAll() {
  const confirmed = prompt("⚠️ CRITICAL ACTION: Type 'FLATTEN' to instantly close ALL open positions across CoinSwitch and Delta:");
  if (confirmed !== "FLATTEN") {
    alert("Action cancelled.");
    return;
  }
  try {
    const res = await saFetch("/api/admin/panic-flatten-all", { method: "POST" });
    const data = await res.json();
    alert(`🚨 Flatten signal dispatched: ${data.message || 'Positions closed'}`);
    loadOverviewData();
  } catch (err) {
    alert("Network error executing panic flatten");
  }
}

async function triggerImmediateTradeCycle() {
  try {
    const res = await saFetch("/api/admin/trigger-cycle", { method: "POST" });
    const data = await res.json();
    alert(`⚡ Scan triggered: ${data.message || 'Ensemble scan cycle running in background.'}`);
  } catch (err) {
    alert("Network error triggering scan cycle");
  }
}

// ── 10. EDGE WAF & BANNED IPS ─────────────────────────────────────────────
async function loadBannedIpsTable() {
  try {
    const res = await saFetch("/api/admin/security/banned-ips");
    if (!res.ok) return;
    const data = await res.json();
    allBannedIps = data.banned_ips || [];

    const tbody = document.getElementById("bannedIpsTableBody");
    if (!tbody) return;
    tbody.innerHTML = "";

    if (allBannedIps.length === 0) {
      tbody.innerHTML = `<tr><td colspan="5" class="sa-text-center">No banned IPs on record. Edge firewall perimeter secure.</td></tr>`;
      return;
    }

    allBannedIps.forEach(b => {
      const tr = document.createElement("tr");
      const dateStr = b.banned_at ? new Date(b.banned_at * 1000).toLocaleString() : '--';
      tr.innerHTML = `
        <td><strong style="font-family: 'JetBrains Mono', monospace; color: var(--sa-danger);">${escapeHtml(b.ip)}</strong></td>
        <td>${escapeHtml(b.reason || 'Exploit probe')}</td>
        <td><span class="sa-badge sa-badge-danger">${b.strikes || 1} STRIKES</span></td>
        <td style="font-size: 11px; color: var(--sa-text-muted);">${dateStr}</td>
        <td>
          <button class="sa-btn-sm sa-btn-success" onclick="unbanIpAddress('${escapeHtml(b.ip)}')">UNBAN / PARDON</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  } catch (err) {
    console.error("Banned IPs error:", err);
  }
}

function openManualBanModal() {
  document.getElementById("manualBanModal").classList.add("active");
}

function closeManualBanModal() {
  document.getElementById("manualBanModal").classList.remove("active");
}

async function handleManualBanSubmit(e) {
  e.preventDefault();
  const ip = document.getElementById("banIpInput").value.trim();
  const reason = document.getElementById("banReasonInput").value.trim();
  if (!ip) return;

  try {
    const res = await saFetch("/api/admin/security/ban-ip", {
      method: "POST",
      body: JSON.stringify({ ip, reason })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`🛡️ IP ${ip} permanently blacklisted.`);
      closeManualBanModal();
      document.getElementById("manualBanForm").reset();
      loadBannedIpsTable();
      loadOverviewData();
    } else {
      alert(`Error: ${data.message || 'Failed to ban IP'}`);
    }
  } catch (err) {
    alert("Network error banning IP");
  }
}

async function unbanIpAddress(ip) {
  if (!confirm(`Are you sure you want to unban IP ${ip}?`)) return;
  try {
    const res = await saFetch("/api/admin/security/unban-ip", {
      method: "POST",
      body: JSON.stringify({ ip })
    });
    const data = await res.json();
    if (res.ok) {
      alert(`✅ IP ${ip} unbanned.`);
      loadBannedIpsTable();
      loadOverviewData();
    } else {
      alert(`Error: ${data.message || 'Failed to unban IP'}`);
    }
  } catch (err) {
    alert("Network error unbanning IP");
  }
}

// ── 11. USER CRM PROFILE DRAWER ───────────────────────────────────────────
async function openUserCrmDrawer(userId) {
  const drawer = document.getElementById("userCrmDrawer");
  const body = document.getElementById("crmDrawerBody");
  document.getElementById("crmUserTitle").textContent = `User CRM Profile #${userId}`;
  body.innerHTML = "Loading full CRM profile...";
  drawer.classList.add("active");

  try {
    const res = await saFetch(`/api/admin/user/${userId}/details`);
    if (!res.ok) {
      body.innerHTML = "<p>Failed to load profile.</p>";
      return;
    }
    const data = await res.json();
    const u = data.user || {};
    const keys = data.api_keys || {};

    const regDate = u.created_at ? new Date(u.created_at * 1000).toLocaleString() : '--';
    body.innerHTML = `
      <div style="display: flex; flex-direction: column; gap: 16px;">
        <div class="sa-card" style="padding: 16px;">
          <h4 style="color: #fff; margin-bottom: 8px;">Identity & Account Details</h4>
          <p><strong>Name:</strong> ${escapeHtml(u.name || '--')}</p>
          <p><strong>Email:</strong> ${escapeHtml(u.email || '--')}</p>
          <p><strong>Role:</strong> ${escapeHtml(u.role || 'trader')}</p>
          <p><strong>Account Active:</strong> ${u.is_active ? 'YES' : 'NO'}</p>
          <p><strong>Registered:</strong> ${regDate}</p>
          <p><strong>Country:</strong> ${escapeHtml(u.country || 'US')}</p>
          <p><strong>Phone:</strong> ${escapeHtml(u.phone || '--')}</p>
          <p><strong>Referred By:</strong> ${escapeHtml(u.referred_by_code || 'Direct')}</p>
        </div>

        <div class="sa-card" style="padding: 16px;">
          <h4 style="color: #fff; margin-bottom: 8px;">Exchange API Status</h4>
          <p><strong>CoinSwitch Pro:</strong> ${keys.has_coinswitch ? `<span style="color: var(--sa-success);">CONNECTED (${keys.cs_key_masked})</span>` : '<span style="color: var(--sa-danger);">NOT CONFIGURED</span>'}</p>
          <p><strong>Delta Exchange India:</strong> ${keys.has_delta ? `<span style="color: var(--sa-success);">CONNECTED (${keys.delta_key_masked})</span>` : '<span style="color: var(--sa-danger);">NOT CONFIGURED</span>'}</p>
        </div>

        <div class="sa-card" style="padding: 16px;">
          <h4 style="color: #fff; margin-bottom: 8px;">Subscription & Spending</h4>
          <p><strong>Current Plan:</strong> ${(u.plan_name || 'free').toUpperCase()}</p>
          <p><strong>Total Platform Spend:</strong> $${(u.total_spent || 0).toFixed(2)}</p>
        </div>
      </div>
    `;
  } catch (err) {
    body.innerHTML = "<p>Error loading CRM details.</p>";
  }
}

function closeUserCrmDrawer() {
  document.getElementById("userCrmDrawer").classList.remove("active");
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
