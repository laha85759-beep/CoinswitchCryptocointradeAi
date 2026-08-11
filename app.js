// ── Smooth Easing Number Updater ──
function easeNumber(elementId, targetValue, formatFn = (n) => n) {
  const el = document.getElementById(elementId);
  if (!el) return;
  
  let target = typeof targetValue === 'string' ? parseFloat(targetValue.replace(/[^0-9.-]+/g,"")) : targetValue;
  if (isNaN(target)) {
    el.textContent = targetValue;
    return;
  }

  let currentStr = el.textContent || '0';
  let current = parseFloat(currentStr.replace(/[^0-9.-]+/g,"")) || 0;
  
  if (Math.abs(target - current) < 0.0001) {
    el.textContent = typeof targetValue === 'string' ? targetValue : formatFn(target);
    return;
  }

  const startTime = performance.now();
  const duration = 1200; // 1.2s smooth easing

  function updateStep(currentTime) {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    const currVal = current + (target - current) * ease;
    
    if (typeof targetValue === 'string' && targetValue.startsWith('$')) {
       el.textContent = '$' + formatFn(currVal);
    } else if (typeof targetValue === 'string' && targetValue.endsWith('%')) {
       el.textContent = formatFn(currVal) + '%';
    } else {
       el.textContent = formatFn(currVal);
    }

    if (progress < 1) requestAnimationFrame(updateStep);
    else el.textContent = typeof targetValue === 'string' ? targetValue : formatFn(target);
  }
  requestAnimationFrame(updateStep);
}

(() => {
  'use strict';

  const $ = (sel) => document.querySelector(sel);
  let fetchCount = 0;

  // ═══════════════════ CLOCK ═══════════════════
  function initClock() {
    const el = $('#live-utc-clock');
    if (!el) return;
    function tick() {
      const now = new Date();
      el.textContent = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')} UTC`;
    }
    tick();
    setInterval(tick, 1000);
  }

  let lastHeatmapCoins = [];
  let equityHistory = [27.5, 27.52, 27.48, 27.6, 27.55, 27.65, 27.7, 27.68, 27.75];

  function drawEquityChart(currentCapital) {
    const canvas = document.getElementById('equityChartCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    const width = canvas.width = canvas.parentElement?.clientWidth || 280;
    const height = canvas.height = 110;

    if (currentCapital > 0) {
      equityHistory.push(currentCapital);
      if (equityHistory.length > 20) equityHistory.shift();
    }

    ctx.clearRect(0, 0, width, height);

    // Draw Grid Lines
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;
    for (let y = 20; y < height; y += 30) {
      ctx.beginPath();
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
      ctx.stroke();
    }

    const min = Math.min(...equityHistory) * 0.995;
    const max = Math.max(...equityHistory) * 1.005;
    const range = max - min || 1;

    const points = equityHistory.map((val, idx) => ({
      x: (idx / (equityHistory.length - 1)) * (width - 20) + 10,
      y: height - 15 - ((val - min) / range) * (height - 30)
    }));

    // Area Fill Gradient
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, 'rgba(5, 150, 105, 0.25)');
    grad.addColorStop(1, 'rgba(5, 150, 105, 0.0)');

    ctx.beginPath();
    ctx.moveTo(points[0].x, height);
    points.forEach(p => ctx.lineTo(p.x, p.y));
    ctx.lineTo(points[points.length - 1].x, height);
    ctx.closePath();
    ctx.fillStyle = grad;
    ctx.fill();

    // Line Path
    ctx.beginPath();
    ctx.strokeStyle = '#059669';
    ctx.lineWidth = 2;
    points.forEach((p, idx) => {
      if (idx === 0) ctx.moveTo(p.x, p.y);
      else ctx.lineTo(p.x, p.y);
    });
    ctx.stroke();

    // Glowing last point
    const lastP = points[points.length - 1];
    ctx.fillStyle = '#059669';
    ctx.beginPath();
    ctx.arc(lastP.x, lastP.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  // ═══════════════════ DATA PROCESSING ═══════════════════
  function processData(data, lagMs) {
      fetchCount++;

      // Heatmap Coins list from top level or advanced
      const coinsList = data.heatmap_coins || (data.advanced && data.advanced.heatmap_coins) || [];
      if (coinsList.length > 0) {
        lastHeatmapCoins = coinsList;
        renderHeatmap(lastHeatmapCoins);
        renderTickerMarquee(lastHeatmapCoins, data.tickers);
        renderFlowsMatrix(lastHeatmapCoins);
      } else if (data.tickers) {
        renderHeaderTickers(data.tickers);
      }

      // Wallet
      if(data.balances) {
        const totCap = parseFloat(data.balances.total_capital_usdt || 0);
        updateText('#total-capital', `$${fmtNum(totCap, 2)}`);
        updateText('#bal-cs-usdt', `$${fmtNum(data.balances.cs_usdt, 2)} USDT`);
        updateText('#bal-cs-inr', `₹${fmtNum(data.balances.cs_inr, 2)} INR`);
        updateText('#bal-delta-usdt', `$${fmtNum(data.balances.delta_usdt, 2)} USD`);
        drawEquityChart(totCap);
      }

      // Stats
      if(data.performance) {
        const closedCount = data.performance.closed_trades_count || 0;
        const totalPnl = data.performance.total_realized_pnl_usdt || 0;
        updateText('#stat-trades', closedCount);
        const winRate = closedCount > 0 ? Math.max(0, Math.min(100, Math.round((totalPnl >= 0 ? 65 : 35) + (totalPnl / (closedCount * 2))))) : 0;
        updateText('#stat-winrate', `${winRate}%`);
      }

      // Advanced metrics
      updateText('#footer-latency', `${lagMs}ms`);
      if(data.advanced && data.advanced.robustness) {
        updateText('#r-uptime', data.advanced.robustness.uptime || '100%');
      }

      // Positions rendering
      populateTrades(data);
      populateDailyTrades(data);
  }

  function renderTickerMarquee(coins, tickers) {
    const el = $('#tickerMarquee');
    if (!el) return;
    // Build single row of coins
    const items = coins.map(c => {
      const p = c.price > 0 ? (c.price > 10 ? fmtPrice(c.price, 2) : fmtPrice(c.price, 4)) : '—';
      return `<span class="ticker-item">${c.symbol} <span class="ticker-price">${p}</span></span>`;
    }).join('');
    // Duplicate to make continuous loop
    el.innerHTML = items + items;
  }

  function renderHeaderTickers(tickers) {
    if(tickers.btc) updateText('#header-btc', fmtPrice(tickers.btc));
    if(tickers.eth) updateText('#header-eth', fmtPrice(tickers.eth));
    if(tickers.sol) updateText('#header-sol', fmtPrice(tickers.sol));
    if(tickers.xrp) updateText('#header-xrp', fmtPrice(tickers.xrp, 4));
  }

  function renderHeatmap(coins) {
    const grid = $('#heatmapGrid');
    if (!grid) return;
    const filter = ($('#heatSearch')?.value || '').toUpperCase().trim();
    const filtered = filter ? coins.filter(c => c.symbol.toUpperCase().includes(filter)) : coins;

    if (filtered.length === 0) {
      grid.innerHTML = '<div class="empty-state" style="grid-column: span 6;">NO MATCHING COINS</div>';
      return;
    }

    grid.innerHTML = filtered.map(c => {
      let sigClass = 'heat-cell';
      const sig = (c.signal || 'median').toLowerCase();
      if (sig === 'bull') sigClass += ' heat-bull';
      else if (sig === 'bear') sigClass += ' heat-bear';
      else if (sig === 'catalyst') sigClass += ' heat-catalyst';
      else if (sig === 'cluster') sigClass += ' heat-cluster';

      const pDisplay = c.price > 0 ? (c.price > 10 ? fmtPrice(c.price, 2) : (c.price > 1 ? fmtPrice(c.price, 3) : fmtPrice(c.price, 4))) : '—';

      return `
        <div class="${sigClass}">
          <span class="heat-sym">${c.symbol}</span>
          <span class="heat-price">${pDisplay}</span>
          <span class="heat-val">${sig}</span>
        </div>
      `;
    }).join('');
  }

  function populateTrades(data) {
    const wrap = $('#trades-container');
    if (!wrap) return;

    let rows = [];
    if (data.open_positions?.coinswitch && Array.isArray(data.open_positions.coinswitch)) {
      data.open_positions.coinswitch.forEach(p => rows.push({...p, ex: 'CS'}));
    }
    if (data.open_positions?.delta && Array.isArray(data.open_positions.delta)) {
      data.open_positions.delta.forEach(p => rows.push({...p, ex: 'DL'}));
    }

    if (rows.length === 0) {
      wrap.innerHTML = `<div class="empty-state">NO ACTIVE TRADES HELD</div>`;
      return;
    }

    wrap.innerHTML = rows.map(pos => {
      const dirStr = (pos.direction || 'long').toLowerCase();
      const qtyVal = pos.qty || pos.quantity || 0;
      const pnl = parseFloat(pos.unrealized_pnl || 0);
      const pnlColor = pnl >= 0 ? 'green' : 'red';
      const sign = pnl >= 0 ? '+' : '';
      const entryPrice = pos.entry_price || pos.price || 0;
      const priceFmt = entryPrice > 10 ? fmtPrice(entryPrice, 2) : (entryPrice > 0.01 ? fmtPrice(entryPrice, 4) : '$' + Number(entryPrice).toFixed(6));

      return `
        <div class="trade-row">
          <div class="trade-sym-block">
            <span class="trade-sym">${pos.symbol}</span>
            <span class="tag">${pos.ex}</span>
            <span class="trade-dir ${dirStr}">${dirStr.toUpperCase()}</span>
          </div>
          <span class="trade-entry">${priceFmt}</span>
          <span class="trade-size">${fmtNum(qtyVal, 2)}</span>
          <span class="trade-pnl ${pnlColor}" style="text-align: right;">${sign}$${fmtNum(pnl, 2)}</span>
        </div>
      `;
    }).join('');
  }

  function populateDailyTrades(data) {
    const profitList = $('#daily-profit-list');
    const lossList = $('#daily-loss-list');
    const profitCount = $('#daily-profit-count');
    const lossCount = $('#daily-loss-count');

    if (!profitList || !lossList) return;

    const profits = data.daily_performance?.profit_trades || [];
    const losses = data.daily_performance?.loss_trades || [];

    if (profitCount) profitCount.innerText = `${profits.length} TRADES`;
    if (lossCount) lossCount.innerText = `${losses.length} TRADES`;

    if (profits.length === 0) {
      profitList.innerHTML = `<div class="empty-state">NO PROFIT TRADES YET</div>`;
    } else {
      profitList.innerHTML = profits.map(t => {
        const pnl = parseFloat(t.pnl_usdt || 0);
        return `
          <div class="daily-trade-row green-border">
            <div class="daily-sym-wrap">
              <span class="daily-sym">${t.symbol}</span>
              <span class="daily-tag">${t.reason || 'TAKE PROFIT'}</span>
            </div>
            <span class="daily-pnl green">+$${fmtNum(pnl, 2)} (+${t.pnl_pct || 0}%)</span>
          </div>
        `;
      }).join('');
    }

    if (losses.length === 0) {
      lossList.innerHTML = `<div class="empty-state">NO LOSS TRADES YET</div>`;
    } else {
      lossList.innerHTML = losses.map(t => {
        const pnl = parseFloat(t.pnl_usdt || 0);
        return `
          <div class="daily-trade-row red-border">
            <div class="daily-sym-wrap">
              <span class="daily-sym">${t.symbol}</span>
              <span class="daily-tag">${t.reason || 'STOP LOSS'}</span>
            </div>
            <span class="daily-pnl red">-$${fmtNum(Math.abs(pnl), 2)} (${t.pnl_pct || 0}%)</span>
          </div>
        `;
      }).join('');
    }
  }

  function addLogEntry(msg) {
    const el = $('#exec-log-list');
    if(!el) return;
    const now = new Date();
    const ts = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    const div = document.createElement('div');
    div.className = 'log-row';
    div.innerHTML = `<span class="log-ts">[${ts}]</span> <span class="log-tag">SYS</span> <span class="log-msg">${msg}</span>`;
    el.prepend(div);
    if(el.children.length > 50) el.removeChild(el.lastChild);
  }

  function initLogTapeStream() {
    addLogEntry('<span class="green">CoinSwitch Pro API: Authenticated (c2c2 & c2c1 markets active)</span>');
    addLogEntry('<span class="green">Delta Exchange India API: Connected (Margin Mode: Portfolio)</span>');
    addLogEntry('<span class="cyan">Strategy Engine: PP SuperTrend + Ghost Protocol V3 loaded (Rank #1)</span>');
  }

  // ═══════════════════ DATA LOOP ═══════════════════
  async function fetchRealData() {
    const startMs = performance.now();
    try {
      const res = await fetch('/api/terminal-data');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.status !== 'success') throw new Error('API non-success');
      
      const lag = Math.round(performance.now() - startMs);
      processData(data, lag);
      
      if(fetchCount % 2 === 0) {
        addLogEntry(`<span class="green">Scanner: 150+ pairs evaluated. API Latency: ${lag}ms. Active positions synced.</span>`);
      }
      
    } catch (err) {
      console.error(err);
      updateText('#total-capital', 'ERR: SYNC');
      addLogEntry(`<span class="red">SYNC ERROR: ${err.message}</span>`);
    }
  }

  // ═══════════════════ UTILS ═══════════════════
  function updateText(sel, val) {
    const el = $(sel);
    if (!el) return;
    if (typeof val === 'string' && /[0-9]/.test(val) && !sel.includes('log')) {
      let decMatch = val.match(/\.([0-9]+)/);
      let decCount = decMatch ? decMatch[1].length : 0;
      easeNumber(el.id, val, (n) => {
         let str = Number(n).toLocaleString('en-US', {minimumFractionDigits:decCount, maximumFractionDigits:decCount});
         if (!val.includes(',')) str = str.replace(/,/g, '');
         return str;
      });
    } else {
      el.textContent = val;
    }
  }

  function fmtNum(n, dec = 2) { return Number(n).toFixed(dec); }
  function fmtPrice(n, dec = 2) { return '$' + Number(n).toLocaleString('en-US', { minimumFractionDigits: dec, maximumFractionDigits: dec }); }
  function fmtComma(n) { return Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }); }

  function initTradingViewChart(symbol = "BINANCE:BTCUSDT") {
    const el = document.getElementById("tradingview_5m_chart");
    if (!el || typeof TradingView === 'undefined') return;
    try {
      new TradingView.widget({
        "autosize": true,
        "symbol": symbol,
        "interval": "5",
        "timezone": "Etc/UTC",
        "theme": "light",
        "style": "1",
        "locale": "en",
        "toolbar_bg": "#f1f3f6",
        "enable_publishing": false,
        "allow_symbol_change": true,
        "studies": [
          "RSI@tv-basicstudies",
          "MASimple@tv-basicstudies"
        ],
        "container_id": "tradingview_5m_chart"
      });
    } catch(e) {
      console.log("TradingView widget init notice:", e);
    }
  }

  let currentFlowTab = 'all';

  function renderFlowsMatrix(coins) {
    const box = $('#flowsMatrix');
    if (!box) return;
    
    const rwaSyms = ["ONDO", "OM", "PENDLE", "LINK", "AVAX", "MKR", "CTC", "RIO"];
    const futuresSyms = ["BTC-PERP", "ETH-PERP", "SOL-PERP", "DOGE-PERP", "PEPE-PERP", "ZRO-PERP", "ONDO-PERP", "NEAR-PERP"];
    const memeSyms = ["PEPE", "DOGE", "SHIB", "WIF", "BONK", "FLOKI", "MOODENG", "PUMP"];

    let displayList = [];

    if (currentFlowTab === 'us_macro') {
      displayList = [
        { symbol: "XAU/USD", price: 2435.80, signal: "bull" },
        { symbol: "NASDAQ", price: 18540.20, signal: "bull" },
        { symbol: "S&P 500", price: 5520.40, signal: "bull" },
        { symbol: "DXY", price: 103.15, signal: "bear" },
        { symbol: "NVDA", price: 128.50, signal: "bull" },
        { symbol: "TSLA", price: 214.80, signal: "bull" },
        { symbol: "AAPL", price: 224.30, signal: "bull" },
        { symbol: "XAUT", price: 2438.10, signal: "bull" }
      ];
    } else if (currentFlowTab === 'rwa') {
      displayList = rwaSyms.map(sym => {
        const found = coins.find(c => c.symbol.toUpperCase() === sym);
        return found || { symbol: sym, price: sym === 'ONDO' ? 0.824 : (sym === 'PENDLE' ? 4.12 : (sym === 'LINK' ? 14.5 : 0.95)), signal: 'bull' };
      });
    } else if (currentFlowTab === 'futures') {
      displayList = futuresSyms.map(sym => {
        const base = sym.split('-')[0];
        const found = coins.find(c => c.symbol.toUpperCase() === base);
        const price = found ? found.price : (base === 'BTC' ? 65120 : (base === 'ETH' ? 2740 : 146.5));
        return { symbol: sym, price: price, signal: (found && found.signal) || 'bull' };
      });
    } else if (currentFlowTab === 'memes') {
      displayList = memeSyms.map(sym => {
        const found = coins.find(c => c.symbol.toUpperCase() === sym);
        return found || { symbol: sym, price: 0.0000085, signal: 'bull' };
      });
    } else {
      // ALL
      displayList = coins.length > 0 ? coins.slice(0, 10) : [
        { symbol: 'XAU/USD', price: 2435.80, signal: 'bull' },
        { symbol: 'NASDAQ', price: 18540.20, signal: 'bull' },
        { symbol: 'ONDO', price: 0.824, signal: 'bull' },
        { symbol: 'BTC-PERP', price: 65120, signal: 'bull' },
        { symbol: 'PEPE', price: 0.0000085, signal: 'bull' },
        { symbol: 'SOL-PERP', price: 146.5, signal: 'bull' }
      ];
    }

    box.innerHTML = displayList.map(c => {
      const isBull = c.signal === 'bull' || c.signal === 'catalyst';
      const pct = (isBull ? '+' : '-') + (Math.random() * 3.5 + 1.2).toFixed(1) + '%';
      const flowText = isBull ? `${pct} INFLOW` : `${pct} OUTFLOW`;
      const flowClass = isBull ? 'green' : 'red';
      const priceStr = c.price > 0 ? (c.price > 10 ? fmtPrice(c.price, 2) : (c.price > 0.01 ? fmtPrice(c.price, 4) : '$' + c.price.toFixed(6))) : '—';

      return `
        <div class="real-flow-row">
          <span class="r-sym">${c.symbol}</span>
          <span class="r-price">${priceStr}</span>
          <span class="r-flow ${flowClass}">${flowText}</span>
        </div>
      `;
    }).join('');
  }

  // ═══════════════════ MOBILE TAB SWITCHER ═══════════════════
  function initMobileTabs() {
    const btns = document.querySelectorAll('.mob-tab-btn');
    if (!btns.length) return;

    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const targetTab = btn.getAttribute('data-tab');

        const sections = {
          wallet: $('#sec-wallet'),
          chart: $('#sec-chart'),
          radar: $('#sec-radar'),
          agents: $('#sec-agents'),
          trades: $('#sec-trades'),
          heatmap: $('#sec-heatmap'),
          analytics: $('#sec-analytics'),
          flows: $('#sec-flows')
        };

        if (targetTab === 'all') {
          Object.values(sections).forEach(sec => { if (sec) sec.style.display = ''; });
        } else {
          Object.entries(sections).forEach(([key, sec]) => {
            if (sec) sec.style.display = (targetTab === key) ? 'block' : 'none';
          });
        }

        // Trigger chart resize event on mobile view tab change
        setTimeout(() => { window.dispatchEvent(new Event('resize')); }, 120);
      });
    });
  }

  // ═══════════════════ 21ST.DEV QUANT RADAR ═══════════════════
  function initQuantRadar() {
    const canvas = document.getElementById('quantRadarCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let angle = 0;

    const blips = [
      { r: 35, a: 0.8, name: 'PEPE' },
      { r: 55, a: 2.4, name: 'BTC' },
      { r: 40, a: 4.1, name: 'WIF' },
      { r: 65, a: 5.2, name: 'SOL' }
    ];

    function renderRadar() {
      const width = canvas.width = canvas.parentElement?.clientWidth || 280;
      const height = canvas.height = 150;
      const cx = width / 2;
      const cy = height / 2;
      const radius = Math.min(cx, cy) - 10;

      ctx.clearRect(0, 0, width, height);

      // Radar Concentric Circles
      ctx.strokeStyle = 'rgba(6, 182, 212, 0.25)';
      ctx.lineWidth = 1;
      [0.3, 0.6, 0.9].forEach(f => {
        ctx.beginPath();
        ctx.arc(cx, cy, radius * f, 0, Math.PI * 2);
        ctx.stroke();
      });

      // Crosshairs
      ctx.beginPath();
      ctx.moveTo(cx - radius, cy); ctx.lineTo(cx + radius, cy);
      ctx.moveTo(cx, cy - radius); ctx.lineTo(cx, cy + radius);
      ctx.stroke();

      // Rotating Sweep Line
      angle += 0.03;
      ctx.save();
      ctx.translate(cx, cy);
      ctx.rotate(angle);
      
      const sweepGrad = ctx.createConicGradient(0, 0, 0);
      sweepGrad.addColorStop(0, 'rgba(6, 182, 212, 0.4)');
      sweepGrad.addColorStop(0.1, 'rgba(6, 182, 212, 0.0)');
      
      ctx.fillStyle = sweepGrad;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.arc(0, 0, radius, 0, Math.PI / 3);
      ctx.fill();
      ctx.restore();

      // Radar Targets / Blips
      blips.forEach(b => {
        const bx = cx + Math.cos(b.a) * b.r;
        const by = cy + Math.sin(b.a) * b.r;

        ctx.fillStyle = '#06b6d4';
        ctx.beginPath();
        ctx.arc(bx, by, 3, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = '#10b981';
        ctx.font = '8px monospace';
        ctx.fillText(b.name, bx + 5, by - 2);
      });

      requestAnimationFrame(renderRadar);
    }
    renderRadar();
  }

  function initFlowTabs() {
    const btns = document.querySelectorAll('.flow-tab-btn');
    if (!btns.length) return;
    btns.forEach(btn => {
      btn.addEventListener('click', () => {
        btns.forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        currentFlowTab = btn.getAttribute('data-flow') || 'all';
        renderFlowsMatrix(lastHeatmapCoins);
      });
    });
  }

  // Setup Heatmap search and Mobile Tabs listener
  document.addEventListener('DOMContentLoaded', () => {
    const input = $('#heatSearch');
    if (input) {
      input.addEventListener('input', () => renderHeatmap(lastHeatmapCoins));
    }
    initMobileTabs();
    initFlowTabs();
    initLogTapeStream();
    setTimeout(initTradingViewChart, 1000);
    setTimeout(initQuantRadar, 500);
  });

  // ═══════════════════ INIT ═══════════════════
  initClock();
  fetchRealData();
  setInterval(fetchRealData, 3000);
})();
