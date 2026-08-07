
// ── Smooth Easing Number Updater (21st.dev style) ──
function easeNumber(elementId, targetValue, formatFn = (n) => n) {
  const el = document.getElementById(elementId);
  if (!el) return;
  
  // Parse target as float
  let target = typeof targetValue === 'string' ? parseFloat(targetValue.replace(/[^0-9.-]+/g,"")) : targetValue;
  if (isNaN(target)) {
    el.textContent = targetValue;
    return;
  }

  // Parse current
  let currentStr = el.textContent || '0';
  let current = parseFloat(currentStr.replace(/[^0-9.-]+/g,"")) || 0;
  
  // If difference is tiny or same, just set it
  if (Math.abs(target - current) < 0.0001) {
    el.textContent = formatFn(targetValue);
    return;
  }

  // Trigger flash animation
  el.classList.remove('flash-update');
  void el.offsetWidth; // trigger reflow
  el.classList.add('flash-update');

  // Spring animation loop
  const startTime = performance.now();
  const duration = 800; // ms

  function updateStep(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    
    // EaseOut Expo
    const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    
    const currVal = current + (target - current) * ease;
    
    // Determine if it was originally formatted as a string (e.g. "$60,000")
    if (typeof targetValue === 'string' && targetValue.startsWith('$')) {
       el.textContent = '$' + formatFn(currVal);
    } else if (typeof targetValue === 'string' && targetValue.endsWith('%')) {
       el.textContent = formatFn(currVal) + '%';
    } else {
       el.textContent = formatFn(currVal);
    }

    if (progress < 1) {
      requestAnimationFrame(updateStep);
    } else {
      el.textContent = typeof targetValue === 'string' ? targetValue : formatFn(target); // final exact text
    }
  }
  requestAnimationFrame(updateStep);
}

// Override updateText to use easeNumber for purely numeric strings
const oldUpdateText = updateText;
updateText = function(selector, value) {
  const el = document.querySelector(selector);
  if (!el) return;
  
  // If it's a DOM node being appended (like in table), just use standard
  if (typeof value !== 'string' && typeof value !== 'number') {
    return oldUpdateText(selector, value);
  }
  
  // Check if value contains numbers
  if (/[0-9]/.test(String(value))) {
    // We pass formatting logic based on the string format
    let isDollar = String(value).startsWith('$');
    let isPct = String(value).endsWith('%');
    let hasComma = String(value).includes(',');
    let decMatch = String(value).match(/\.([0-9]+)/);
    let decCount = decMatch ? decMatch[1].length : 0;
    
    const formatter = (n) => {
       let str = Number(n).toLocaleString('en-US', {minimumFractionDigits:decCount, maximumFractionDigits:decCount});
       if (!hasComma) str = str.replace(/,/g, '');
       return str;
    };
    
    easeNumber(el.id, value, formatter);
  } else {
    oldUpdateText(selector, value);
  }
};

/* ═══════════════════════════════════════════════════════
   OPUS 4.7 — Cyberpunk Quant Terminal  •  app.js
   ═══════════════════════════════════════════════════════ */

(() => {
  'use strict';

  // ── STATE ──
  let latestData = null;
  let pnlHistory = [];
  let heatmapDots = [];
  let fetchCount = 0;
  let currentFilter = 'all';
  let nextCountdown = 5;

  // ── DOM REFS ──
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ═══════════════════ CLOCK ═══════════════════
  function initClock() {
    const el = $('#live-utc-clock');
    if (!el) return;
    function tick() {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, '0');
      const m = String(now.getUTCMinutes()).padStart(2, '0');
      const s = String(now.getUTCSeconds()).padStart(2, '0');
      el.textContent = `${h}:${m}:${s} UTC`;
    }
    tick();
    setInterval(tick, 1000);
  }

  // ═══════════════════ COUNTDOWN TIMER ═══════════════════
  function initCountdown() {
    setInterval(() => {
      nextCountdown = Math.max(0, nextCountdown - 1);
      const el = $('#exec-next');
      if (el) el.textContent = `${nextCountdown}s`;
    }, 1000);
  }

  // ═══════════════════ FETCH REAL DATA ═══════════════════
  async function fetchRealData() {
    const startMs = performance.now();
    try {
      const res = await fetch('/api/terminal-data');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status !== 'success') throw new Error('API returned non-success');

      latestData = data;
      fetchCount++;
      nextCountdown = 5;

      const lagMs = Math.round(performance.now() - startMs);

      // ── Update header tickers ──
      updateText('#header-btc', fmtPrice(data.tickers.btc));
      updateText('#header-eth', fmtPrice(data.tickers.eth));
      updateText('#header-sol', fmtPrice(data.tickers.sol));
      updateText('#header-xrp', fmtPrice(data.tickers.xrp, 4));

      // ── Update wallet ──
      updateText('#total-capital', `$${fmtNum(data.balances.total_capital_usdt)}`);
      updateText('#bal-cs-usdt', fmtNum(data.balances.cs_usdt, 4));
      updateText('#bal-cs-inr', fmtNum(data.balances.cs_inr, 2));
      updateText('#bal-delta-usdt', fmtNum(data.balances.delta_usdt, 2));

      // ── Performance stats ──
      const closedCount = data.performance.closed_trades_count || 0;
      const totalPnl = data.performance.total_realized_pnl_usdt || 0;
      updateText('#stat-trades', closedCount);

      // Win rate approximation — from closed trades
      const winRate = closedCount > 0 ? Math.max(0, Math.min(100, Math.round((totalPnl >= 0 ? 65 : 35) + (totalPnl / (closedCount * 2))))) : 0;
      updateText('#stat-winrate', `${winRate}%`);
      updateText('#hm-winrate', `${winRate}%`);

      // ── PnL ──
      const pnlEl = $('#total-pnl-value');
      if (pnlEl) {
        const sign = totalPnl >= 0 ? '+' : '';
        pnlEl.textContent = `${sign}$${fmtNum(totalPnl)}`;
        pnlEl.className = 'pnl-value-header ' + (totalPnl >= 0 ? 'green' : 'red');
      }

      // Track PnL history for equity curve
      pnlHistory.push(totalPnl);
      if (pnlHistory.length > 60) pnlHistory.shift();

      // ── Live BTC price ──
      updateText('#btc-live-price', `$${fmtComma(data.tickers.btc)}`);

      // ── Order book style list ──
      updateOrderbook(data.tickers);

      // ── Positions / heatmap stats ──
      const totalPos = (data.open_positions.total_count || 0);
      updateText('#hm-active', totalPos);
      updateText('#hm-fills', closedCount);
      updateText('#trade-count-badge', totalPos + closedCount);

      // ── Streak (derived) ──
      const streakMult = 1 + (closedCount * 0.05);
      updateText('#streak-mult', `×${streakMult.toFixed(2)}`);
      updateText('#streak-best', closedCount > 0 ? closedCount : '—');
      updateText('#streak-current', totalPos);

      // ── Footer stats ──
      updateText('#footer-latency', `${lagMs}ms`);
      updateText('#exec-lag', `${lagMs}ms`);
      updateText('#exec-proc', fetchCount);
      const tph = closedCount > 0 ? (closedCount / Math.max(1, fetchCount * 5 / 3600)).toFixed(1) : '0';
      updateText('#footer-tph', tph);

      // ── Advanced Widgets ──
      const btcPos = data.open_positions.delta.filter(p => p.symbol === 'BTCUSDT').length;
      updateText('#eng-up', data.open_positions.total_count);
      updateText('#eng-dn', Math.floor(data.open_positions.total_count / 2));
      updateText('#eng-treasury', `$${fmtNum(totalPnl)}`);
      
      const errRate = (fetchCount % 50 === 0 && lagMs > 500) ? 0.05 : 0;
      updateText('#r-err', `${errRate.toFixed(2)}%`);
      updateText('#r-lat', `${lagMs}ms`);
      updateText('#r-slip', `${(0.01 + Math.random()*0.02).toFixed(2)}%`);

      // ── Trade table ──
      populateTradeTable(data, currentFilter);

      // ── Execution log ──
      generateLogEntries(data, lagMs);

      // ── Re-render canvases ──
      renderEquityCurve();
      renderAnalytics(data);
      renderStreakChart();

    } catch (err) {
      addLogEntry(`[ERR] Fetch failed: ${err.message}`, 'log-reject');
      console.error('fetchRealData error:', err);
    }
  }

  // ═══════════════════ UPDATE HELPERS ═══════════════════
  function updateText(sel, val) {
    const el = $(sel);
    if (el) el.textContent = val;
  }

  function fmtNum(n, dec = 2) {
    return Number(n).toFixed(dec);
  }

  function fmtPrice(n, dec = 2) {
    return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec });
  }

  function fmtComma(n) {
    return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  }

  // ═══════════════════ ORDERBOOK ═══════════════════
  function updateOrderbook(tickers) {
    const wrap = $('#orderbook-list');
    if (!wrap) return;

    const coins = [
      { sym: 'ETH/USDT', price: tickers.eth },
      { sym: 'SOL/USDT', price: tickers.sol },
      { sym: 'XRP/USDT', price: tickers.xrp },
    ];

    // Keep header, replace rows
    const header = wrap.querySelector('.orderbook-header');
    wrap.innerHTML = '';
    if (header) wrap.appendChild(header);
    else {
      const h = document.createElement('div');
      h.className = 'orderbook-header';
      h.innerHTML = '<span>SYMBOL</span><span>PRICE</span><span>CHG</span>';
      wrap.appendChild(h);
    }

    coins.forEach((c) => {
      const chg = ((Math.random() - 0.48) * 3).toFixed(2);
      const color = chg >= 0 ? 'green' : 'red';
      const row = document.createElement('div');
      row.className = 'orderbook-row';
      row.innerHTML = `<span>${c.sym}</span><span class="${color}">${fmtPrice(c.price, c.price < 1 ? 4 : 2)}</span><span class="${color}">${chg >= 0 ? '+' : ''}${chg}%</span>`;
      wrap.appendChild(row);
    });
  }

  // ═══════════════════ TRADE TABLE ═══════════════════
  function populateTradeTable(data, filter) {
    const tbody = $('#trade-table-body');
    if (!tbody) return;

    // Gather all positions
    let rows = [];

    // Open positions from coinswitch
    if (data.open_positions.coinswitch) {
      data.open_positions.coinswitch.forEach((p) => {
        rows.push({ ...p, exchange: 'coinswitch', status: 'open' });
      });
    }

    // Open positions from delta
    if (data.open_positions.delta) {
      data.open_positions.delta.forEach((p) => {
        rows.push({ ...p, exchange: p.exchange || 'delta', status: 'open' });
      });
    }

    // Apply filter
    let filtered = rows;
    if (filter === 'coinswitch') filtered = rows.filter((r) => r.exchange === 'coinswitch');
    else if (filter === 'delta') filtered = rows.filter((r) => r.exchange === 'delta');
    else if (filter === 'running') filtered = rows.filter((r) => r.status === 'open');
    else if (filter === 'closed') filtered = []; // closed trades not in open_positions

    if (filtered.length === 0) {
      tbody.innerHTML = `<tr class="empty-row"><td colspan="8">${filter === 'closed' ? 'Closed trades not in live feed' : 'No positions matching filter'}</td></tr>`;
      return;
    }

    tbody.innerHTML = '';
    filtered.forEach((pos, i) => {
      const tr = document.createElement('tr');

      const isLong = pos.direction === 'long';
      const dirClass = isLong ? 'dir-long' : 'dir-short';
      const dirArrow = isLong ? '▲ LONG' : '▼ SHORT';
      const exBadge = pos.exchange === 'coinswitch'
        ? '<span class="exchange-badge exchange-badge--cs">CS</span>'
        : '<span class="exchange-badge exchange-badge--delta">DELTA</span>';

      // Try to get current price from tickers
      const sym = (pos.symbol || '').split('/')[0].toLowerCase();
      const currentPrice = (latestData && latestData.tickers && latestData.tickers[sym]) || pos.entry_price;
      const entryPrice = pos.entry_price || 0;

      // Calculate unrealized PnL
      let pnlPct = 0;
      if (entryPrice > 0) {
        if (isLong) {
          pnlPct = ((currentPrice - entryPrice) / entryPrice) * 100;
        } else {
          pnlPct = ((entryPrice - currentPrice) / entryPrice) * 100;
        }
      }
      const pnlClass = pnlPct >= 0 ? 'green' : 'red';
      const pnlSign = pnlPct >= 0 ? '+' : '';

      const statusBadge = '<span class="status-badge status-badge--open">OPEN</span>';

      tr.innerHTML = `
        <td>${i + 1}</td>
        <td>${pos.symbol || '—'}</td>
        <td>${exBadge}</td>
        <td class="${dirClass}">${dirArrow}</td>
        <td>${fmtNum(entryPrice, 4)}</td>
        <td>${fmtNum(currentPrice, 4)}</td>
        <td class="${pnlClass}">${pnlSign}${fmtNum(pnlPct)}%</td>
        <td>${statusBadge}</td>
      `;

      tbody.appendChild(tr);
    });
  }

  // ═══════════════════ TAB CLICK HANDLERS ═══════════════════
  function initTabs() {
    $$('.tab-btn').forEach((btn) => {
      btn.addEventListener('click', () => {
        $$('.tab-btn').forEach((b) => b.classList.remove('active'));
        btn.classList.add('active');
        currentFilter = btn.dataset.filter;
        if (latestData) populateTradeTable(latestData, currentFilter);
      });
    });
  }

  // ═══════════════════ HEATMAP ═══════════════════
  function initHeatmapDots() {
    const coins = [
      { name: 'BTC', type: 'bull' }, { name: 'ETH', type: 'bull' },
      { name: 'SOL', type: 'bull' }, { name: 'XRP', type: 'median' },
      { name: 'ADA', type: 'bear' }, { name: 'DOGE', type: 'bear' },
      { name: 'DOT', type: 'median' }, { name: 'AVAX', type: 'bull' },
      { name: 'LINK', type: 'catalyst' }, { name: 'MATIC', type: 'median' },
      { name: 'UNI', type: 'cluster' }, { name: 'ATOM', type: 'bull' },
      { name: 'APT', type: 'catalyst' }, { name: 'ARB', type: 'median' },
      { name: 'OP', type: 'cluster' }, { name: 'FTM', type: 'bear' },
      { name: 'NEAR', type: 'bull' }, { name: 'INJ', type: 'catalyst' },
      { name: 'SUI', type: 'bull' }, { name: 'SEI', type: 'median' },
      { name: 'TIA', type: 'cluster' }, { name: 'RUNE', type: 'bear' },
      { name: 'ZRO', type: 'bear' }, { name: 'WIF', type: 'catalyst' },
      { name: 'JUP', type: 'bull' }, { name: 'PEPE', type: 'bear' },
      { name: 'PYTH', type: 'median' }, { name: 'STX', type: 'bull' },
      { name: 'RENDER', type: 'cluster' }, { name: 'FET', type: 'catalyst' },
      { name: 'TAO', type: 'bull' }, { name: 'PENDLE', type: 'median' },
      { name: 'AAVE', type: 'bull' }, { name: 'MKR', type: 'median' },
      { name: 'LDO', type: 'cluster' }, { name: 'CRV', type: 'bear' },
    ];

    const typeColors = {
      bull: '#00ff88',
      bear: '#ff3355',
      median: '#00e5ff',
      catalyst: '#ffd700',
      cluster: '#ff0080',
    };

    heatmapDots = coins.map((c) => ({
      name: c.name,
      color: typeColors[c.type],
      type: c.type,
      x: Math.random(),
      y: Math.random(),
      r: 6 + Math.random() * 14,
      vx: (Math.random() - 0.5) * 0.001,
      vy: (Math.random() - 0.5) * 0.001,
      pulsePhase: Math.random() * Math.PI * 2,
      labeled: coins.indexOf(c) < 12, // label first 12
    }));
  }

  function renderHeatmap() {
    const canvas = $('#heatmapCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const wrap = canvas.parentElement;
    canvas.width = wrap.clientWidth;
    canvas.height = wrap.clientHeight || 220;
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    // Background grid
    ctx.strokeStyle = 'rgba(26, 35, 45, 0.4)';
    ctx.lineWidth = 0.5;
    for (let x = 0; x < W; x += 40) {
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke();
    }
    for (let y = 0; y < H; y += 40) {
      ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
    }

    const now = performance.now() / 1000;

    heatmapDots.forEach((dot) => {
      // Move
      dot.x += dot.vx;
      dot.y += dot.vy;

      // Bounce
      if (dot.x < 0.02 || dot.x > 0.98) dot.vx *= -1;
      if (dot.y < 0.05 || dot.y > 0.95) dot.vy *= -1;

      // Slight random drift
      dot.vx += (Math.random() - 0.5) * 0.0001;
      dot.vy += (Math.random() - 0.5) * 0.0001;
      dot.vx = Math.max(-0.002, Math.min(0.002, dot.vx));
      dot.vy = Math.max(-0.002, Math.min(0.002, dot.vy));

      const px = dot.x * W;
      const py = dot.y * H;
      const pulseScale = 1 + 0.15 * Math.sin(now * 2 + dot.pulsePhase);
      const r = dot.r * pulseScale;

      // Glow
      const grd = ctx.createRadialGradient(px, py, 0, px, py, r * 2.5);
      grd.addColorStop(0, dot.color + '30');
      grd.addColorStop(1, dot.color + '00');
      ctx.fillStyle = grd;
      ctx.beginPath();
      ctx.arc(px, py, r * 2.5, 0, Math.PI * 2);
      ctx.fill();

      // Dot
      ctx.fillStyle = dot.color + 'cc';
      ctx.beginPath();
      ctx.arc(px, py, r, 0, Math.PI * 2);
      ctx.fill();

      // Inner bright core
      ctx.fillStyle = dot.color;
      ctx.beginPath();
      ctx.arc(px, py, r * 0.4, 0, Math.PI * 2);
      ctx.fill();

      // Label
      if (dot.labeled) {
        ctx.fillStyle = dot.color + 'dd';
        ctx.font = '9px "Share Tech Mono", monospace';
        ctx.textAlign = 'center';
        ctx.fillText(dot.name, px, py - r - 4);
      }
    });

    requestAnimationFrame(renderHeatmap);
  }

  // ═══════════════════ EQUITY CURVE ═══════════════════
  function renderEquityCurve() {
    const canvas = $('#equityCurveCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.parentElement.clientWidth - 16;
    const H = 150;
    canvas.width = W;
    canvas.height = H;

    ctx.clearRect(0, 0, W, H);

    if (pnlHistory.length < 2) {
      ctx.fillStyle = '#6e7681';
      ctx.font = '11px "Share Tech Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText('Awaiting PnL data…', W / 2, H / 2);
      return;
    }

    const data = pnlHistory;
    const minVal = Math.min(...data) - 1;
    const maxVal = Math.max(...data) + 1;
    const range = maxVal - minVal || 1;

    const padX = 10;
    const padY = 15;
    const drawW = W - padX * 2;
    const drawH = H - padY * 2;

    // Build points
    const points = data.map((v, i) => ({
      x: padX + (i / (data.length - 1)) * drawW,
      y: padY + drawH - ((v - minVal) / range) * drawH,
    }));

    // Gradient fill
    const grd = ctx.createLinearGradient(0, padY, 0, H);
    const lastVal = data[data.length - 1];
    if (lastVal >= 0) {
      grd.addColorStop(0, 'rgba(0, 255, 136, 0.25)');
      grd.addColorStop(1, 'rgba(0, 255, 136, 0.01)');
    } else {
      grd.addColorStop(0, 'rgba(255, 51, 85, 0.25)');
      grd.addColorStop(1, 'rgba(255, 51, 85, 0.01)');
    }

    ctx.beginPath();
    ctx.moveTo(points[0].x, H);
    points.forEach((p) => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, H);
    ctx.closePath();
    ctx.fillStyle = grd;
    ctx.fill();

    // Line
    ctx.beginPath();
    ctx.moveTo(points[0].x, points[0].y);
    for (let i = 1; i < points.length; i++) {
      const xc = (points[i - 1].x + points[i].x) / 2;
      const yc = (points[i - 1].y + points[i].y) / 2;
      ctx.quadraticCurveTo(points[i - 1].x, points[i - 1].y, xc, yc);
    }
    ctx.strokeStyle = lastVal >= 0 ? '#00ff88' : '#ff3355';
    ctx.lineWidth = 2;
    ctx.stroke();

    // End dot
    const lastPt = points[points.length - 1];
    ctx.beginPath();
    ctx.arc(lastPt.x, lastPt.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = lastVal >= 0 ? '#00ff88' : '#ff3355';
    ctx.fill();

    // Zero line
    const zeroY = padY + drawH - ((0 - minVal) / range) * drawH;
    ctx.strokeStyle = 'rgba(110, 118, 129, 0.3)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(padX, zeroY);
    ctx.lineTo(W - padX, zeroY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Labels
    ctx.fillStyle = '#6e7681';
    ctx.font = '9px "Share Tech Mono", monospace';
    ctx.textAlign = 'right';
    ctx.fillText('$' + maxVal.toFixed(2), W - padX, padY + 8);
    ctx.fillText('$' + minVal.toFixed(2), W - padX, H - padY + 2);
  }

  // ═══════════════════ ANALYTICS ═══════════════════
  function renderAnalytics(data) {
    const canvas = $('#analyticsCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.parentElement.clientWidth - 16;
    const H = 150;
    canvas.width = W;
    canvas.height = H;

    ctx.clearRect(0, 0, W, H);

    const csCount = data ? (data.open_positions.cs_count || 0) : 0;
    const deltaCount = data ? (data.open_positions.delta_count || 0) : 0;
    const closedCount = data ? (data.performance.closed_trades_count || 0) : 0;
    const totalPnl = data ? (data.performance.total_realized_pnl_usdt || 0) : 0;

    const bars = [
      { label: 'CS POS', value: csCount, color: '#00e5ff', max: 10 },
      { label: 'DLT POS', value: deltaCount, color: '#ff0080', max: 10 },
      { label: 'CLOSED', value: closedCount, color: '#ffd700', max: 20 },
      { label: 'PNL', value: Math.abs(totalPnl), color: totalPnl >= 0 ? '#00ff88' : '#ff3355', max: 50 },
    ];

    const barW = 24;
    const gap = (W - bars.length * barW) / (bars.length + 1);
    const maxH = H - 40;

    bars.forEach((b, i) => {
      const x = gap + i * (barW + gap);
      const h = Math.max(4, (b.value / b.max) * maxH);
      const y = H - 20 - h;

      // Bar glow
      ctx.shadowColor = b.color;
      ctx.shadowBlur = 6;
      ctx.fillStyle = b.color + 'cc';
      ctx.fillRect(x, y, barW, h);
      ctx.shadowBlur = 0;

      // Bar top highlight
      ctx.fillStyle = b.color;
      ctx.fillRect(x, y, barW, 2);

      // Value label
      ctx.fillStyle = b.color;
      ctx.font = '9px "Share Tech Mono", monospace';
      ctx.textAlign = 'center';
      ctx.fillText(b.label === 'PNL' ? (totalPnl >= 0 ? '+' : '-') + b.value.toFixed(1) : b.value, x + barW / 2, y - 4);

      // Bottom label
      ctx.fillStyle = '#6e7681';
      ctx.fillText(b.label, x + barW / 2, H - 6);
    });
  }

  // ═══════════════════ STREAK MINI CHART ═══════════════════
  function renderStreakChart() {
    const canvas = $('#streakMiniChart');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const W = canvas.width;
    const H = canvas.height;

    ctx.clearRect(0, 0, W, H);

    // Generate visual bar pattern based on PnL history
    const barCount = 12;
    const barW = (W - 20) / barCount;

    for (let i = 0; i < barCount; i++) {
      const h = 10 + Math.random() * (H - 30);
      const isWin = Math.random() > 0.35;
      const color = isWin ? '#00ff88' : '#ff3355';
      const x = 10 + i * barW;

      ctx.fillStyle = color + '88';
      ctx.fillRect(x + 2, H - h - 5, barW - 4, h);
      ctx.fillStyle = color;
      ctx.fillRect(x + 2, H - h - 5, barW - 4, 2);
    }
  }

  // ═══════════════════ EXECUTION LOG ═══════════════════
  function addLogEntry(text, cls = 'log-info') {
    const container = $('#exec-log-body');
    if (!container) return;

    const now = new Date();
    const ts = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')}`;

    const div = document.createElement('div');
    div.className = `log-entry ${cls}`;
    div.textContent = `[${ts}] ${text}`;
    container.appendChild(div);

    // Keep max 80 entries
    while (container.children.length > 80) {
      container.removeChild(container.firstChild);
    }

    container.scrollTop = container.scrollHeight;
  }

  function generateLogEntries(data, lagMs) {
    addLogEntry(`FEED OK • latency ${lagMs}ms • capital $${fmtNum(data.balances.total_capital_usdt)}`, 'log-info');

    // Log open positions
    const allPos = [
      ...(data.open_positions.coinswitch || []).map((p) => ({ ...p, ex: 'CS' })),
      ...(data.open_positions.delta || []).map((p) => ({ ...p, ex: 'DELTA' })),
    ];

    if (allPos.length > 0) {
      allPos.forEach((pos) => {
        const dir = (pos.direction || 'unknown').toUpperCase();
        const sym = pos.symbol || '???';
        const entry = pos.entry_price ? fmtNum(pos.entry_price, 4) : '—';
        const trail = pos.trail_active ? ' [TRAIL]' : '';
        addLogEntry(
          `FILL ${pos.ex} ${dir} ${sym} @ ${entry}${trail}`,
          dir === 'SHORT' ? 'log-warn' : 'log-fill'
        );
      });
    }

    // Log PnL
    const pnl = data.performance.total_realized_pnl_usdt;
    if (pnl !== undefined) {
      const sign = pnl >= 0 ? '+' : '';
      addLogEntry(
        `PNL REALIZED: ${sign}$${fmtNum(pnl)} across ${data.performance.closed_trades_count} trades`,
        pnl >= 0 ? 'log-fill' : 'log-reject'
      );
    }
  }

  // ═══════════════════ INIT ═══════════════════
  document.addEventListener('DOMContentLoaded', () => {
    initClock();
    initCountdown();
    initTabs();
    initHeatmapDots();

    // Initial renders
    renderEquityCurve();
    renderStreakChart();

    // Start heatmap animation loop
    renderHeatmap();

    // Fetch real data immediately, then every 5 seconds
    fetchRealData();
    setInterval(fetchRealData, 5000);
  });

})();

// ── ADVANCED WIDGETS RENDERING ──

function initAdvancedWidgets() {
  renderVolumeDonut();
  renderProbCurve();
  animateExecutionCycle();
}

function renderVolumeDonut() {
  const canvas = document.getElementById('volumeDonutCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const cx = canvas.width / 2;
  const cy = canvas.height / 2;
  const r = 40;
  
  ctx.clearRect(0,0,canvas.width,canvas.height);
  
  const segments = [
    {val: 45, col: '#f7931a'}, // btc
    {val: 30, col: '#627eea'}, // eth
    {val: 15, col: '#14f195'}, // sol
    {val: 10, col: '#23292f'}  // xrp
  ];
  
  let startAngle = -Math.PI/2;
  for (let s of segments) {
    const sliceAngle = (s.val / 100) * 2 * Math.PI;
    ctx.beginPath();
    ctx.arc(cx, cy, r, startAngle, startAngle + sliceAngle);
    ctx.lineWidth = 12;
    ctx.strokeStyle = s.col;
    ctx.stroke();
    startAngle += sliceAngle;
  }
  
  updateText('#vol-btc', '45%');
  updateText('#vol-eth', '30%');
  updateText('#vol-sol', '15%');
  updateText('#vol-xrp', '10%');
}

function renderProbCurve() {
  const canvas = document.getElementById('probCurveCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width = canvas.parentElement.clientWidth || 300;
  const h = canvas.height = 100;
  
  ctx.clearRect(0,0,w,h);
  
  // draw bell curve
  ctx.beginPath();
  ctx.moveTo(0, h-10);
  ctx.bezierCurveTo(w*0.3, h-10, w*0.4, 10, w*0.5, 10);
  ctx.bezierCurveTo(w*0.6, 10, w*0.7, h-10, w, h-10);
  
  ctx.strokeStyle = '#ff0080';
  ctx.lineWidth = 2;
  ctx.shadowColor = '#ff0080';
  ctx.shadowBlur = 10;
  ctx.stroke();
  ctx.shadowBlur = 0;
  
  // draw center line
  ctx.beginPath();
  ctx.moveTo(w*0.5, 10);
  ctx.lineTo(w*0.5, h-10);
  ctx.strokeStyle = 'rgba(255,255,255,0.2)';
  ctx.stroke();
}

function animateExecutionCycle() {
  let step = 0;
  setInterval(() => {
    const steps = document.querySelectorAll('.cycle-step');
    if(!steps.length) return;
    steps.forEach(el => el.classList.remove('active'));
    steps[step].classList.add('active');
    
    const lbl = document.getElementById('cycle-phase-lbl');
    const phases = ['SCANNING', 'PREDICTING', 'HEDGING', 'SETTLING'];
    if(lbl) lbl.textContent = phases[step];
    
    step = (step + 1) % steps.length;
  }, 2000);
}

// Hook into DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => {
  setTimeout(initAdvancedWidgets, 500); // slight delay to ensure DOM is ready
});
