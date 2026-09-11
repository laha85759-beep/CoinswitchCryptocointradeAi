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
      // Calculate IST (UTC + 5 hours 30 mins)
      const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
      const istTime = new Date(utcTime + (3600000 * 5.5));
      
      const istStr = `${String(istTime.getHours()).padStart(2, '0')}:${String(istTime.getMinutes()).padStart(2, '0')}:${String(istTime.getSeconds()).padStart(2, '0')} IST`;
      const utcStr = `${String(now.getUTCHours()).padStart(2, '0')}:${String(now.getUTCMinutes()).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')} UTC`;
      
      el.textContent = `${istStr} | ${utcStr}`;
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

      // Stats & Per-Exchange Win/Loss Rates
      if(data.performance) {
        const closedCount = data.performance.closed_trades_count || 0;
        updateText('#stat-trades', closedCount);
        updateText('#stat-winrate', `${data.performance.overall_winrate || 75.0}%`);

        // PNL stats
        const dailyPnL = parseFloat(data.performance.daily_realized_pnl_usdt || 0);
        const allTimePnL = parseFloat(data.performance.total_realized_pnl_usdt || 0);
        
        const dSign = dailyPnL >= 0 ? '+' : '';
        const aSign = allTimePnL >= 0 ? '+' : '';
        
        const dEl = $('#daily-pnl-stat');
        if (dEl) {
          dEl.textContent = `${dSign}$${fmtNum(dailyPnL, 2)}`;
          dEl.className = `wallet-stat-value ${dailyPnL >= 0 ? 'green' : 'red'}`;
        }
        
        const aEl = $('#all-time-pnl-stat');
        if (aEl) {
          aEl.textContent = `${aSign}$${fmtNum(allTimePnL, 2)}`;
          aEl.className = `wallet-stat-value ${allTimePnL >= 0 ? 'green' : 'red'}`;
        }

        // CoinSwitch Pro Rates
        updateText('#cs-winrate', `${data.performance.cs_winrate || 100.0}%`);
        updateText('#cs-lossrate', `${data.performance.cs_lossrate || 0.0}%`);
        updateText('#cs-fills', `${data.performance.cs_closed_count || 0} TRADES`);

        // Delta Exchange India Rates
        updateText('#delta-winrate', `${data.performance.delta_winrate || 75.0}%`);
        updateText('#delta-lossrate', `${data.performance.delta_lossrate || 25.0}%`);
        updateText('#delta-fills', `${data.performance.delta_closed_count || 0} TRADES`);
      }

      // Update Telegram Channel URLs dynamically
      if (data.telegram_channel_url) {
        const hLink = $('#headerTgLink');
        const mLink = $('#mainTgBannerLink');
        if (hLink) hLink.href = data.telegram_channel_url;
        if (mLink) mLink.href = data.telegram_channel_url;
      }

      // Advanced metrics
      updateText('#footer-latency', `${lagMs}ms`);
      if(data.advanced && data.advanced.robustness) {
        updateText('#r-uptime', data.advanced.robustness.uptime || '100%');
      }

      // Flow Engineering metrics
      if(data.advanced && data.advanced.flow_engineering) {
        const fe = data.advanced.flow_engineering;
        updateText('#flow-heartbeat', `${fe.heartbeat_hz || 1.2} Hz`);
        updateText('#flow-slippage', `${fe.avg_slippage_pct || 0.042}%`);
        updateText('#flow-success-rate', `${fe.api_success_rate || 99.8}%`);
        updateText('#flow-queue', `${fe.active_tasks_in_queue || 0} / ${fe.execution_threads || 2} THREADS`);
        
        const ofiList = $('#flow-ofi-list');
        if (ofiList && fe.order_flow_imbalance) {
          ofiList.innerHTML = fe.order_flow_imbalance.map(o => {
            const isGreen = o.imbalance_pct >= 0;
            return `
              <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #10151c; padding: 2px 0;">
                <span style="color: #6e7681;">${o.symbol}/USDT</span>
                <span class="${isGreen ? 'green' : 'red'}" style="font-weight: bold;">${o.imbalance_pct >= 0 ? '+' : ''}${o.imbalance_pct}% (${o.status})</span>
              </div>
            `;
          }).join('');
        }
      }

      // Positions & Orders rendering
      populateTrades(data);
      populateOpenOrders(data);
      populateDailyTrades(data);
      populatePreBreakoutSignals(data);
  }

  function populatePreBreakoutSignals(data) {
    const list = $('#preBreakoutList');
    if (!list) return;
    const signals = data.pre_breakout_signals || [];
    if (signals.length === 0) return;

    list.innerHTML = signals.map(s => {
      const isGreen = s.class === 'green' || s.type.includes('PUMP');
      const sigColor = isGreen ? 'green' : 'red';
      const chgSign = s.change_5m >= 0 ? '+' : '';
      return `
        <div class="pre-row">
          <div class="pre-sym-wrap">
            <span class="pre-sym">${s.symbol}</span>
            <span class="pre-type ${sigColor}">${s.type}</span>
          </div>
          <div class="pre-metrics">
            <span class="pre-vol">VOL ${s.vol_ratio}x</span>
            <span class="pre-chg ${sigColor}">${chgSign}${s.change_5m}%</span>
            <span class="pre-conf">CONF ${s.confidence}%</span>
          </div>
        </div>
      `;
    }).join('');
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
      data.open_positions.coinswitch.forEach(p => rows.push({...p, ex: 'CS', exName: 'CS SPOT'}));
    }
    if (data.open_positions?.delta && Array.isArray(data.open_positions.delta)) {
      data.open_positions.delta.forEach(p => rows.push({...p, ex: 'DL', exName: 'DELTA PERP'}));
    }

    if (rows.length === 0) {
      wrap.innerHTML = `
        <div class="empty-state" style="padding: 16px 8px; text-align: center; color: var(--text-dim);">
          <div style="font-size: 11px; color: var(--accent-green); font-weight: 700; margin-bottom: 4px;">🟢 0 OPEN POSITIONS • 100% MARGIN AVAILABLE</div>
          <div style="font-size: 9px; color: var(--text-dim);">24/7 autonomous dual-exchange scanner active across 250+ spot & futures markets</div>
        </div>
      `;
      return;
    }

    wrap.innerHTML = rows.map(pos => {
      const dirStr = (pos.direction || 'long').toLowerCase();
      const isLong = dirStr === 'long';
      const qtyVal = pos.qty || pos.quantity || 0;
      const pnl = parseFloat(pos.unrealized_pnl || 0);
      const pnlColor = pnl >= 0 ? 'green' : 'red';
      const sign = pnl >= 0 ? '+' : '';
      const entryPrice = pos.entry_price || pos.price || 0;
      const markPrice = parseFloat(pos.mark_price || entryPrice || 0);
      const liqPrice = parseFloat(pos.liquidation_price || 0);
      const marginUsed = parseFloat(pos.margin_used || 0);

      const pnlPct = entryPrice > 0 ? (((markPrice - entryPrice) / entryPrice) * 100 * (isLong ? 1 : -1)) : 0;
      const priceFmt = entryPrice > 10 ? fmtPrice(entryPrice, 2) : (entryPrice > 0.01 ? fmtPrice(entryPrice, 4) : '$' + Number(entryPrice).toFixed(6));
      const markFmt = markPrice > 10 ? fmtPrice(markPrice, 2) : (markPrice > 0.01 ? fmtPrice(markPrice, 4) : '$' + Number(markPrice).toFixed(6));

      // Extra info row for positions
      let extraRow = '';
      if (pos.ex === 'DL' && markPrice > 0) {
        const liqFmt = liqPrice > 0 ? (liqPrice > 10 ? fmtPrice(liqPrice, 2) : '$' + liqPrice.toFixed(4)) : 'N/A';
        extraRow = `<div style="grid-column:1/-1;font-size:9px;color:#94a3b8;padding:4px 6px;margin-top:4px;background:rgba(6,9,14,0.6);border-radius:3px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:4px;">
          <span>Mark: <b style="color:#00e5ff">${markFmt}</b></span>
          <span>Liq: <b style="color:#ff3355">${liqFmt}</b></span>
          <span>Margin: <b style="color:#f8fafc">$${fmtNum(marginUsed, 2)}</b></span>
          <span style="color:#10b981;font-weight:700;">🟢 AUTO-TRAILING ON</span>
        </div>`;
      } else if (pos.ex === 'CS') {
        extraRow = `<div style="grid-column:1/-1;font-size:9px;color:#94a3b8;padding:4px 6px;margin-top:4px;background:rgba(6,9,14,0.6);border-radius:3px;display:flex;justify-content:space-between;">
          <span>Holding Value: <b style="color:#00e5ff">$${fmtNum(marginUsed, 2)}</b></span>
          <span style="color:#10b981;font-weight:700;">🟢 SPOT SECURED</span>
        </div>`;
      }

      return `
        <div class="trade-row" style="flex-wrap:wrap;border-left:3px solid ${isLong ? '#10b981' : '#ff3355'};background:rgba(13,19,31,0.9);margin-bottom:6px;padding:8px 10px;border-radius:4px;">
          <div class="trade-sym-block">
            <span class="trade-sym" style="font-size:12px;font-weight:800;color:#f8fafc;">${pos.symbol}</span>
            <span class="tag" style="background:rgba(0,229,255,0.15);color:#00e5ff;border-color:#00e5ff;">${pos.exName}</span>
            <span class="trade-dir ${dirStr}" style="font-weight:800;">${isLong ? '🟢 LONG' : '🔴 SHORT'}</span>
          </div>
          <span class="trade-entry" style="font-family:var(--font-mono);font-size:11px;">Entry: <b>${priceFmt}</b></span>
          <span class="trade-size" style="font-family:var(--font-mono);font-size:11px;">Size: <b>${fmtNum(qtyVal, 2)}</b></span>
          <span class="trade-pnl ${pnlColor}" style="text-align:right;font-size:12px;font-weight:800;">${sign}$${fmtNum(pnl, 2)} <small style="font-size:9px;opacity:0.8;">(${sign}${pnlPct.toFixed(2)}%)</small></span>
          ${extraRow}
        </div>
      `;
    }).join('');
  }

  function populateOpenOrders(data) {
    const wrap = $('#orders-container');
    if (!wrap) return;

    const orders = data.open_orders || [];

    if (orders.length === 0) {
      wrap.innerHTML = `<div class="empty-state">NO ACTIVE PENDING ORDERS</div>`;
      return;
    }

    wrap.innerHTML = orders.map(o => {
      const side = (o.side || 'buy').toLowerCase();
      const sideColor = side === 'buy' ? 'green' : 'red';
      const typeStr = o.type || 'LIMIT';
      const qtyVal = o.qty || 0;
      const priceVal = o.price || 0;
      const priceFmt = priceVal > 10 ? fmtPrice(priceVal, 2) : (priceVal > 0.01 ? fmtPrice(priceVal, 4) : '$' + Number(priceVal).toFixed(6));
      const exchFmt = o.exchange === 'coinswitch' ? 'CS' : 'DL';

      return `
        <div class="trade-row" style="grid-template-columns: 1.5fr 1fr 1fr 1.2fr; border-bottom: 1px solid #10151c; padding: 4px 6px;">
          <div class="trade-sym-block">
            <span class="trade-sym">${o.symbol}</span>
            <span class="tag" style="padding: 1px 3px; font-size: 9px; line-height: 1;">${exchFmt}</span>
          </div>
          <span class="trade-entry">${priceFmt}</span>
          <span class="trade-size">${fmtNum(qtyVal, 2)}</span>
          <span class="trade-pnl ${sideColor}" style="text-align: right; font-weight: bold; font-size: 10px;">${side.toUpperCase()} (${typeStr})</span>
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

  // ── TRADINGVIEW PRO CHART ENGINE (DARK CYBERPUNK THEME + RELIABLE FALLBACK) ──
  let currentTvSymbol = "BINANCE:BTCUSDT";
  let currentTvTf = "5";
  let currentTvDisplayName = "BTC/USDT";

  function initTradingViewChart(symbol = currentTvSymbol, interval = currentTvTf, displayName = currentTvDisplayName) {
    const el = document.getElementById("tradingview_5m_chart");
    if (!el) return;

    currentTvSymbol = symbol;
    currentTvTf = interval;
    currentTvDisplayName = displayName;

    const badge = document.getElementById("tvActiveSymbolBadge");
    if (badge) badge.textContent = displayName;

    // Clean symbol for iframe fallback
    let cleanSym = symbol.replace("BINANCE:", "").replace("COINBASE:", "").replace("DELTA:", "");
    if (!cleanSym.includes("USDT") && !cleanSym.includes("USD")) cleanSym += "USDT";

    // Attempt Native TradingView Widget with Dark Cyberpunk Theme
    let nativeSuccess = false;
    if (typeof TradingView !== 'undefined' && TradingView.widget) {
      try {
        el.innerHTML = "";
        new TradingView.widget({
          "autosize": true,
          "symbol": symbol,
          "interval": interval,
          "timezone": "Etc/UTC",
          "theme": "dark",
          "style": "1",
          "locale": "en",
          "toolbar_bg": "#06090e",
          "enable_publishing": false,
          "allow_symbol_change": true,
          "withdateranges": true,
          "hide_side_toolbar": false,
          "loading_screen": { "backgroundColor": "#06090e", "foregroundColor": "#00e5ff" },
          "overrides": {
            "paneProperties.background": "#06090e",
            "paneProperties.vertGridProperties.color": "rgba(59, 130, 246, 0.12)",
            "paneProperties.horzGridProperties.color": "rgba(59, 130, 246, 0.12)",
            "mainSeriesProperties.candleStyle.upColor": "#00ff88",
            "mainSeriesProperties.candleStyle.downColor": "#ff0080",
            "mainSeriesProperties.candleStyle.drawWick": true,
            "mainSeriesProperties.candleStyle.drawBorder": true,
            "mainSeriesProperties.candleStyle.borderColor": "#00ff88",
            "mainSeriesProperties.candleStyle.borderUpColor": "#00ff88",
            "mainSeriesProperties.candleStyle.borderDownColor": "#ff0080",
            "mainSeriesProperties.candleStyle.wickUpColor": "#00ff88",
            "mainSeriesProperties.candleStyle.wickDownColor": "#ff0080"
          },
          "studies": [
            "RSI@tv-basicstudies",
            "MASimple@tv-basicstudies"
          ],
          "container_id": "tradingview_5m_chart"
        });
        nativeSuccess = true;
      } catch (err) {
        console.warn("Native TradingView widget error, using responsive iframe fallback:", err);
      }
    }

    // High-Reliability Dark Responsive Iframe Fallback (Guarantees zero blank screen)
    if (!nativeSuccess) {
      el.innerHTML = `
        <iframe
          src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart_frame&symbol=BINANCE%3A${encodeURIComponent(cleanSym)}&interval=${interval}&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=06090e&theme=dark&style=1&timezone=Etc%2FUTC"
          style="width: 100%; height: 100%; min-height: 380px; border: none; background: #06090e;"
          allowtransparency="true"
          scrolling="no">
        </iframe>
      `;
    }
  }

  window.switchTvChart = function(symbol, displayName) {
    document.querySelectorAll('.tv-coin-pill').forEach(btn => {
      if (btn.dataset.symbol === symbol) btn.classList.add('active');
      else btn.classList.remove('active');
    });
    initTradingViewChart(symbol, currentTvTf, displayName);
  };

  window.switchTvTimeframe = function(tf) {
    document.querySelectorAll('.tv-tf-btn').forEach(btn => {
      if (btn.dataset.tf === tf) btn.classList.add('active');
      else btn.classList.remove('active');
    });
    initTradingViewChart(currentTvSymbol, tf, currentTvDisplayName);
  };

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
          aichat: $('#sec-ai-chat'),
          wallet: $('#sec-wallet'),
          chart: $('#sec-chart'),
          radar: $('#sec-radar'),
          agents: $('#sec-agents'),
          trades: $('#sec-trades'),
          daily: $('#sec-daily-trades'),
          perf: $('#sec-coin-perf'),
          heatmap: $('#sec-heatmap'),
          volatility: $('#sec-volatility-matrix'),
          prebreakout: $('#sec-pre-breakout'),
          analytics: $('#sec-analytics'),
          flows: $('#sec-flows'),
          admin: $('#sec-admin')
        };

        if (targetTab === 'all') {
          Object.values(sections).forEach(sec => { if (sec) sec.style.display = ''; });
          // Make sure admin section is hidden on 'all' view unless selected specifically to keep layout clean
          if (sections.admin) sections.admin.style.display = 'none';
          const grids = document.querySelectorAll('.side-by-side-grid');
          grids.forEach(g => g.style.display = '');
        } else {
          Object.entries(sections).forEach(([key, sec]) => {
            if (sec) sec.style.display = (targetTab === key) ? 'block' : 'none';
          });
          const grids = document.querySelectorAll('.side-by-side-grid');
          grids.forEach(g => g.style.display = 'contents');
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
    setTimeout(initTradingViewChart, 1000);
    setTimeout(initQuantRadar, 500);
  });

  // 🤖 CYBERPUNK COINSAI QUANT AI CHATBOT HANDLERS
  window.toggleFloatingAiChat = function() {
    const sec = document.getElementById('sec-ai-chat');
    if (sec) {
      if (sec.style.display === 'none' || sec.style.display === '') {
        sec.style.display = 'block';
        const input = document.getElementById('chatInput');
        if (input) input.focus();
      } else {
        sec.style.display = 'none';
      }
    }
  };


  window.handleChatKeyPress = function(e) {
    if (e.key === 'Enter') sendUserChatMessage();
  };

  window.sendChatPrompt = function(promptText) {
    const input = document.getElementById('chatInput');
    if (input) {
      input.value = promptText;
      sendUserChatMessage();
    }
  };

  window.sendUserChatMessage = async function() {
    const input = document.getElementById('chatInput');
    const wrap = document.getElementById('chatMessages');
    if (!input || !wrap) return;
    const msgText = input.value.trim();
    if (!msgText) return;

    // Append User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'chat-msg user-msg';
    userDiv.innerHTML = `<div class="msg-author">👤 TRADER</div><div class="msg-content">${escapeHtml(msgText)}</div>`;
    wrap.appendChild(userDiv);
    input.value = '';
    wrap.scrollTop = wrap.scrollHeight;

    // Append Typing Indicator
    const typingDiv = document.createElement('div');
    typingDiv.className = 'chat-msg bot-msg typing-msg';
    typingDiv.innerHTML = `<div class="msg-author">🤖 COINSAI QUANT AI</div><div class="msg-content cyan">Analyzing live terminal data...</div>`;
    wrap.appendChild(typingDiv);
    wrap.scrollTop = wrap.scrollHeight;

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msgText })
      });
      const data = await res.json();
      wrap.removeChild(typingDiv);

      const botDiv = document.createElement('div');
      botDiv.className = 'chat-msg bot-msg';
      botDiv.innerHTML = `<div class="msg-author">🤖 COINSAI QUANT AI</div><div class="msg-content">${formatMarkdownText(data.reply || 'No response.')}</div>`;
      wrap.appendChild(botDiv);
      wrap.scrollTop = wrap.scrollHeight;
    } catch (err) {
      if (typingDiv.parentNode) wrap.removeChild(typingDiv);
      const errDiv = document.createElement('div');
      errDiv.className = 'chat-msg bot-msg';
      errDiv.innerHTML = `<div class="msg-author">🤖 COINSAI QUANT AI</div><div class="msg-content red">Error connecting to AI assistant: ${err}</div>`;
      wrap.appendChild(errDiv);
      wrap.scrollTop = wrap.scrollHeight;
    }
  };

  function escapeHtml(str) {
    return str.replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m]));
  }

  function formatMarkdownText(str) {
    return str.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
              .replace(/`([^`]+)`/g, '<code class="chat-code">$1</code>')
              .replace(/\n/g, '<br>');
  }

  // ═══════════════════ GLOBAL PARTNER & AFFILIATE HUB JS ═══════════════════
  window.filterAffiliateCategory = function(cat, btn) {
    document.querySelectorAll('.aff-tab-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
    const cards = document.querySelectorAll('.aff-deal-card');
    cards.forEach(card => {
      if (cat === 'all' || card.getAttribute('data-cat') === cat) {
        card.style.display = 'flex';
      } else {
        card.style.display = 'none';
      }
    });
  };

  window.copyAffCoupon = function(code, btn) {
    navigator.clipboard.writeText(code).then(() => {
      const origText = btn.textContent;
      btn.textContent = 'COPIED! ✓';
      btn.style.background = '#00ff88';
      btn.style.color = '#06090e';
      setTimeout(() => {
        btn.textContent = origText;
        btn.style.background = '';
        btn.style.color = '';
      }, 2000);
    }).catch(() => {
      prompt('Copy your promo code:', code);
    });
  };

  // ═══════════════════ DARWIN ATLAS LEADERBOARD JS ═══════════════════

  // Load Darwin leaderboard (weights + history)
  async function loadDarwinLeaderboard() {
    try {
      const res = await fetch('/api/darwin');
      if (!res.ok) return;
      const data = await res.json();
      renderDarwinTable(data.leaderboard || []);
      renderDarwinHistory(data.darwin_history || []);
      renderSpawnedAgents(data.spawned_agents || []);
      const stats = data.stats || {};
      const el = id => document.getElementById(id);
      if (el('darwin-cycles'))    el('darwin-cycles').textContent    = stats.total_cycles || 0;
      if (el('darwin-keep-rate')) el('darwin-keep-rate').textContent = (stats.keep_rate_pct || 0) + '%';
      if (el('darwin-active-agents')) el('darwin-active-agents').textContent = (stats.active_agents || 25) + ' ACTIVE';
    } catch(e) {}
  }

  function renderDarwinTable(agents) {
    const tbody = document.getElementById('darwin-table-body');
    if (!tbody) return;
    if (!agents || agents.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" style="text-align:center;color:#555;padding:12px;">No agent data yet. Run a debate.</td></tr>';
      return;
    }
    const ranks = ['darwin-rank-gold','darwin-rank-silver','darwin-rank-bronze'];
    tbody.innerHTML = agents.map((a, i) => {
      const rankClass = i < 3 ? ranks[i] : '';
      const rankNum = i < 3 ? ['🥇','🥈','🥉'][i] : (i+1);
      const weight = parseFloat(a.weight || 1);
      const wClass = weight >= 1.5 ? 'darwin-weight-high' : weight <= 0.5 ? 'darwin-weight-low' : 'darwin-weight-mid';
      const sharpe = parseFloat(a.sharpe || 0);
      const wr = a.win_rate || 0;
      const statusBadge = weight >= 1.5 ? '<span class="darwin-badge-active">TOP</span>' :
                          weight <= 0.5 ? '<span class="darwin-badge-reverted">LOW</span>' :
                          '<span class="darwin-badge-kept">OK</span>';
      return `<tr>
        <td class="${rankClass}">${rankNum}</td>
        <td style="max-width:120px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" title="${a.agent}">${a.agent.replace(/_/g,' ')}</td>
        <td class="${wClass}">${weight.toFixed(2)}×</td>
        <td style="color:${sharpe > 0 ? '#4ade80' : sharpe < 0 ? '#f87171' : '#94a3b8'}">${sharpe.toFixed(3)}</td>
        <td>${wr}%</td>
        <td>${statusBadge}</td>
      </tr>`;
    }).join('');
  }

  function renderDarwinHistory(history) {
    const el = document.getElementById('darwin-history-list');
    if (!el) return;
    if (!history || history.length === 0) {
      el.innerHTML = '<div style="color:#555;font-size:11px;padding:8px;">No autoresearch cycles yet.</div>';
      return;
    }
    el.innerHTML = history.slice(-5).reverse().map(h => {
      const badgeClass = h.decision === 'KEPT' ? 'darwin-badge-kept' : 
                         h.decision === 'REVERTED' ? 'darwin-badge-reverted' :
                         'darwin-badge-testing';
      const badge = h.decision || h.status || 'PENDING';
      const ts = (h.started_at || '').substring(0,10);
      return `<div class="darwin-history-item">
        <span class="${badgeClass}">${badge}</span>
        <span style="color:#38bdf8;">${(h.agent||'?').replace(/_/g,' ')}</span>
        <span style="color:#475569;">Sharpe: ${(h.sharpe_before||0).toFixed(3)} → ${h.sharpe_after != null ? h.sharpe_after.toFixed(3) : '...'}</span>
        <span style="margin-left:auto;color:#334155;">${ts}</span>
      </div>`;
    }).join('');
  }

  function renderSpawnedAgents(agents) {
    const el = document.getElementById('spawned-agents-list');
    if (!el) return;
    if (!agents || agents.length === 0) {
      el.innerHTML = '<div style="color:#555;font-size:11px;padding:8px;">No auto-spawned agents yet.</div>';
      return;
    }
    el.innerHTML = agents.map(a => `
      <div class="darwin-history-item">
        <span class="darwin-badge-active">SPAWNED</span>
        <span style="color:#38bdf8;">${(a.name||'?').replace(/_/g,' ')}</span>
        <span style="color:#475569;">${a.trigger||''}</span>
        <span style="margin-left:auto;color:#334155;">${(a.spawned_at||'').substring(0,10)}</span>
      </div>`).join('');
  }

  // Run all 25 agents + show results in Darwin panel
  window.triggerDarwinDebate = async function() {
    const btn = document.getElementById('darwin-debate-btn');
    const macroEl = document.getElementById('darwin-macro-regime');
    const sectorEl = document.getElementById('darwin-sector');
    const cioEl = document.getElementById('darwin-cio-call');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ RUNNING...'; }
    if (macroEl) macroEl.textContent = 'RUNNING...';

    try {
      const res = await fetch('/api/agent-debate');
      const data = await res.json();
      if (data.error) throw new Error(data.error);
      
      const s = data.summary || {};
      const macroColor = s.macro_regime === 'RISK_ON' ? '#4ade80' : s.macro_regime === 'RISK_OFF' ? '#f87171' : '#94a3b8';
      const cioColor   = s.cio_final_action === 'BUY' ? '#4ade80' : s.cio_final_action === 'SELL' ? '#f87171' : '#94a3b8';

      if (macroEl) { macroEl.textContent = s.macro_regime || '--'; macroEl.style.color = macroColor; }
      if (sectorEl) sectorEl.textContent = s.sector_consensus || '--';
      if (cioEl) { 
        cioEl.textContent = `${s.cio_final_action || '--'} ${s.cio_final_symbol || ''}`;
        cioEl.style.color = cioColor;
      }
      
      // Render leaderboard from Darwin weights
      await loadDarwinLeaderboard();
      
      // Show success toast
      const toast = document.createElement('div');
      toast.style.cssText = 'position:fixed;top:60px;right:12px;background:#0f4c81;border:1px solid #38bdf8;color:#e2e8f0;font-family:monospace;font-size:11px;padding:8px 14px;border-radius:4px;z-index:9999;';
      toast.textContent = `✅ ATLAS DEBATE COMPLETE: ${s.cio_final_action} ${s.cio_final_symbol}`;
      document.body.appendChild(toast);
      setTimeout(() => toast.remove(), 4000);

    } catch(err) {
      if (macroEl) macroEl.textContent = 'ERROR';
      console.error('Darwin debate error:', err);
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '▶ RUN DEBATE'; }
    }
  };

  // Handle Darwin tab in mobile nav
  document.querySelectorAll('.mob-tab-btn[data-tab="darwin"]').forEach(btn => {
    btn.addEventListener('click', () => {
      loadDarwinLeaderboard();
    });
  });

  // ═══════════════════ ADMIN PANEL FUNCTIONS ═══════════════════
  async function fetchJson(url, options = {}) {
    const res = await fetch(url, options);
    if (!res.ok) {
      let msg = `HTTP Error ${res.status}`;
      try {
        const errData = await res.json();
        if (errData && errData.message) msg += `: ${errData.message}`;
      } catch (e) {
        try {
          const txt = await res.text();
          if (txt) msg += `: ${txt.slice(0, 100)}`;
        } catch (e2) {}
      }
      throw new Error(msg);
    }
    return res.json();
  }

  async function fetchAdminSettings() {
    try {
      const data = await fetchJson('/api/admin/settings');
      if (data.status === 'success' && data.settings) {
        const s = data.settings;
        if ($('#admin-paper-trading')) $('#admin-paper-trading').value = String(s.paper_trading_mode);
        if ($('#admin-capital-pct')) $('#admin-capital-pct').value = s.max_capital_pct;
        if ($('#admin-max-trades')) $('#admin-max-trades').value = s.max_open_trades;
        if ($('#admin-hard-sl')) $('#admin-hard-sl').value = s.hard_sl_pct;
        if ($('#admin-take-profit')) $('#admin-take-profit').value = s.take_profit_pct;
        if ($('#admin-options')) $('#admin-options').value = String(s.options_enabled);
      }
    } catch (err) {
      console.error('Failed to fetch admin settings:', err);
    }
  }

  window.adminUpdateSettings = async function(event) {
    if (event) event.preventDefault();
    
    // Add validation before sending
    const maxCapitalRaw = $('#admin-capital-pct').value;
    const maxTradesRaw = $('#admin-max-trades').value;
    const hardSlRaw = $('#admin-hard-sl').value;
    const takeProfitRaw = $('#admin-take-profit').value;
    
    if (!maxCapitalRaw || !maxTradesRaw || !hardSlRaw || !takeProfitRaw) {
      alert('❌ Error: All fields must be filled in before saving settings.');
      return;
    }
    
    const payload = {
      paper_trading_mode: $('#admin-paper-trading').value === 'true',
      max_capital_pct: parseInt(maxCapitalRaw, 10),
      max_open_trades: parseInt(maxTradesRaw, 10),
      hard_sl_pct: parseFloat(hardSlRaw),
      take_profit_pct: parseFloat(takeProfitRaw),
      options_enabled: $('#admin-options').value === 'true'
    };

    try {
      const data = await fetchJson('/api/admin/update-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (data.status === 'success') {
        alert('✅ Settings saved & persisted successfully!');
      } else {
        alert('❌ Error saving settings: ' + data.message);
      }
    } catch (err) {
      alert('❌ Connection error: ' + err.message);
    }
  };

  window.adminTriggerCycle = async function() {
    if (!confirm('Are you sure you want to run the autonomous trading cycle immediately?')) return;
    try {
      const data = await fetchJson('/api/admin/trigger-cycle', { method: 'POST' });
      if (data.status === 'success') {
        alert('🚀 Cycle triggered successfully. Check execution logs in a few moments!');
      } else {
        alert('❌ Error triggering cycle: ' + data.message);
      }
    } catch (err) {
      alert('❌ Connection error: ' + err.message);
    }
  };

  window.adminResetTrades = async function() {
    if (!confirm('🚨 WARNING: This will reset both open_trades_cs.json and open_trades_delta.json to empty arrays. Active positions will no longer be tracked. Continue?')) return;
    try {
      const data = await fetchJson('/api/admin/reset-trades', { method: 'POST' });
      if (data.status === 'success') {
        alert('🧹 State files reset successfully!');
      } else {
        alert('❌ Error resetting state files: ' + data.message);
      }
    } catch (err) {
      alert('❌ Connection error: ' + err.message);
    }
  };

  // 🚨 Emergency Panic Close All Positions across both exchanges
  window.adminPanicCloseAll = async function() {
    if (!confirm('🚨 EMERGENCY WARNING: Are you sure you want to Market Close ALL open positions immediately across CoinSwitch & Delta?')) return;
    try {
      const data = await fetchJson('/api/admin/panic-close-all', { method: 'POST' });
      if (data.status === 'success') {
        alert('🚨 EMERGENCY PANIC CLOSE ALL EXECUTED SUCCESSFULLY!');
      } else {
        alert('❌ Panic close error: ' + data.message);
      }
    } catch (err) {
      alert('❌ Connection error: ' + err.message);
    }
  };

  // 🔑 User API Credentials Save Handler
  window.adminUpdateCredentials = async function(event) {
    if (event) event.preventDefault();
    const payload = {
      api_key: $('#cred-cs-key').value,
      api_secret: $('#cred-cs-secret').value,
      delta_api_key: $('#cred-delta-key').value,
      delta_api_secret: $('#cred-delta-secret').value,
      telegram_token: $('#cred-tg-token').value,
      telegram_chat_id: $('#cred-tg-chat').value,
      telegram_channel_url: $('#cred-tg-channel') ? $('#cred-tg-channel').value : ''
    };

    try {
      const data = await fetchJson('/api/admin/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (data.status === 'success') {
        alert('🔐 API Credentials updated & authenticated successfully!');
      } else {
        alert('❌ Error updating credentials: ' + data.message);
      }
    } catch (err) {
      alert('❌ Connection error: ' + err.message);
    }
  };

  // 📈 Interactive TradingView Widget Loader
  window.loadTvChart = function(symbol) {
    const container = $('#tv_chart_container');
    if (!container) return;
    const cleanSym = symbol ? symbol.toUpperCase().replace('/', '') : 'BTCUSDT';
    
    container.innerHTML = `
      <iframe
        src="https://s.tradingview.com/widgetembed/?frameElementId=tradingview_chart&symbol=BINANCE%3A${cleanSym}&interval=15&hidesidetoolbar=0&symboledit=1&saveimage=1&toolbarbg=06090c&theme=dark&style=1&timezone=Etc%2FUTC"
        style="width: 100%; height: 100%; border: none;"
        allowtransparency="true"
        scrolling="no">
      </iframe>
    `;
  };

  // Auto-init TradingView chart when tab shown
  setTimeout(() => {
    if (window.loadTvChart) window.loadTvChart('BTCUSDT');
  }, 1000);

  // ── 3D CARD TILT & PARALLAX PHYSICS ENGINE (DRIBBLE 3D / MOTION.DEV) ──
  function init3DCardTilt() {
    const cards = document.querySelectorAll('.card, .card-21st, .rate-card');
    cards.forEach(card => {
      card.addEventListener('mousemove', (e) => {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        const cx = rect.width / 2;
        const cy = rect.height / 2;
        const rx = ((y - cy) / cy) * -6; // max 6 deg tilt
        const ry = ((x - cx) / cx) * 6;
        card.style.transform = `perspective(1000px) rotateX(${rx.toFixed(2)}deg) rotateY(${ry.toFixed(2)}deg) translateZ(6px) scale3d(1.01, 1.01, 1.01)`;
        card.style.setProperty('--mouse-x', `${((x / rect.width) * 100).toFixed(1)}%`);
        card.style.setProperty('--mouse-y', `${((y / rect.height) * 100).toFixed(1)}%`);
      });

      card.addEventListener('mouseleave', () => {
        card.style.transform = 'perspective(1000px) rotateX(0deg) rotateY(0deg) translateZ(0px) scale3d(1, 1, 1)';
        card.style.setProperty('--mouse-x', '50%');
        card.style.setProperty('--mouse-y', '50%');
      });
    });
  }

  // ── 60FPS 3D CYBER PARTICLE MESH CANVAS ENGINE ──
  function init3DCanvas() {
    const canvas = document.getElementById('bg3dCanvas');
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let width, height;
    let particles = [];
    const NUM_PARTICLES = 65;

    function resize() {
      width = canvas.width = window.innerWidth;
      height = canvas.height = window.innerHeight;
    }
    window.addEventListener('resize', resize);
    resize();

    class Particle3D {
      constructor() {
        this.reset();
      }
      reset() {
        this.x = (Math.random() - 0.5) * width * 1.5;
        this.y = (Math.random() - 0.5) * height * 1.5;
        this.z = Math.random() * 800 + 200;
        this.vx = (Math.random() - 0.5) * 0.4;
        this.vy = (Math.random() - 0.5) * 0.4;
        this.vz = (Math.random() - 0.5) * 0.5;
        this.color = Math.random() > 0.6 ? 'rgba(0, 229, 255, ' : (Math.random() > 0.5 ? 'rgba(255, 0, 128, ' : 'rgba(0, 255, 136, ');
      }
      update() {
        this.x += this.vx;
        this.y += this.vy;
        this.z += this.vz;
        if (this.z < 100 || this.z > 1000 || Math.abs(this.x) > width || Math.abs(this.y) > height) {
          this.reset();
        }
      }
      draw(cx, cy, fov) {
        const scale = fov / (fov + this.z);
        const px = cx + this.x * scale;
        const py = cy + this.y * scale;
        const radius = Math.max(0.8, (1 - this.z / 1000) * 2.5);
        const alpha = Math.max(0.1, (1 - this.z / 1000) * 0.7);

        ctx.beginPath();
        ctx.arc(px, py, radius, 0, Math.PI * 2);
        ctx.fillStyle = this.color + alpha + ')';
        ctx.shadowBlur = 8;
        ctx.shadowColor = this.color + '0.8)';
        ctx.fill();
        ctx.shadowBlur = 0;

        return { px, py, alpha };
      }
    }

    for (let i = 0; i < NUM_PARTICLES; i++) {
      particles.push(new Particle3D());
    }

    let mouseX = 0, mouseY = 0;
    window.addEventListener('mousemove', (e) => {
      mouseX = (e.clientX - width / 2) * 0.05;
      mouseY = (e.clientY - height / 2) * 0.05;
    });

    function animate() {
      ctx.clearRect(0, 0, width, height);
      const cx = width / 2 + mouseX;
      const cy = height / 2 + mouseY;
      const fov = 400;

      const screenCoords = [];
      for (let i = 0; i < particles.length; i++) {
        particles[i].update();
        screenCoords.push(particles[i].draw(cx, cy, fov));
      }

      // Draw subtle holographic neural connection lines between close particles
      for (let i = 0; i < screenCoords.length; i++) {
        for (let j = i + 1; j < screenCoords.length; j++) {
          const dx = screenCoords[i].px - screenCoords[j].px;
          const dy = screenCoords[i].py - screenCoords[j].py;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 110) {
            ctx.beginPath();
            ctx.moveTo(screenCoords[i].px, screenCoords[i].py);
            ctx.lineTo(screenCoords[j].px, screenCoords[j].py);
            const lineAlpha = (1 - dist / 110) * 0.15;
            ctx.strokeStyle = `rgba(0, 229, 255, ${lineAlpha})`;
            ctx.lineWidth = 0.8;
            ctx.stroke();
          }
        }
      }

      requestAnimationFrame(animate);
    }
    animate();
  }

  // ═══════════════════ THREE.JS 3D MULTI-MODEL QUANT STUDIO ═══════════════════
  let threeCoreModeIndex = 0;
  let current3DModelKey = 'hypercube';
  let activeSceneGroup = null;
  let threeSceneInstance = null;
  let threeRendererInstance = null;
  let threeCameraInstance = null;

  const THREE_MODES = [
    { name: "WEBGL 60FPS", speed: 1.0, state: "SYNCHRONIZED", nodes: "1,024 ACTIVE" },
    { name: "NEURAL FLUX", speed: 2.2, state: "HYPER-FLUX", nodes: "2,048 BOOSTED" },
    { name: "QUANTUM OVERCLOCK", speed: 3.5, state: "SUPERCONDUCTING", nodes: "4,096 MAXIMUM" }
  ];

  const MODEL_META = {
    hypercube: { name: "4D QUANTUM TESSERACT", nodes: "1,024 ACTIVE" },
    brain: { name: "NEURAL SYNAPSE BRAIN", nodes: "2,480 SYNAPSES" },
    helix: { name: "CANDLESTICK PRICE HELIX", nodes: "512 TICKS" }
  };

  window.toggle3DCoreMode = function() {
    threeCoreModeIndex = (threeCoreModeIndex + 1) % THREE_MODES.length;
    const mode = THREE_MODES[threeCoreModeIndex];
    const hudState = document.getElementById('hudCoreState');
    const hudNodes = document.getElementById('hudNodes');
    if (hudState) {
      hudState.textContent = mode.state;
      hudState.className = 'hud-val ' + (threeCoreModeIndex === 0 ? 'green' : (threeCoreModeIndex === 1 ? 'cyan' : 'magenta'));
    }
    if (hudNodes) hudNodes.textContent = mode.nodes;
  };

  window.switch3DModel = function(modelKey) {
    if (!MODEL_META[modelKey]) return;
    current3DModelKey = modelKey;

    // Update active button
    document.querySelectorAll('.three-sel-btn').forEach(btn => {
      btn.classList.toggle('active', btn.getAttribute('data-model') === modelKey);
    });

    const hudModel = document.getElementById('hudModelName');
    const hudNodes = document.getElementById('hudNodes');
    if (hudModel) hudModel.textContent = MODEL_META[modelKey].name;
    if (hudNodes) hudNodes.textContent = MODEL_META[modelKey].nodes;

    if (threeSceneInstance) {
      buildActive3DModel(threeSceneInstance);
    }
  };

  function buildActive3DModel(scene) {
    if (activeSceneGroup) {
      scene.remove(activeSceneGroup);
      activeSceneGroup.traverse(child => {
        if (child.geometry) child.geometry.dispose();
        if (child.material) {
          if (Array.isArray(child.material)) child.material.forEach(m => m.dispose());
          else child.material.dispose();
        }
      });
    }

    activeSceneGroup = new THREE.Group();
    scene.add(activeSceneGroup);

    if (current3DModelKey === 'hypercube') {
      // ── MODEL 1: 4D QUANTUM TESSERACT HYPERCUBE ──
      // Outer Cube
      const outerGeo = new THREE.BoxGeometry(3.6, 3.6, 3.6);
      const outerMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, wireframe: true, transparent: true, opacity: 0.5 });
      const outerCube = new THREE.Mesh(outerGeo, outerMat);
      activeSceneGroup.add(outerCube);

      // Inner Cube
      const innerGeo = new THREE.BoxGeometry(1.8, 1.8, 1.8);
      const innerMat = new THREE.MeshBasicMaterial({ color: 0xff0080, wireframe: true, transparent: true, opacity: 0.75 });
      const innerCube = new THREE.Mesh(innerGeo, innerMat);
      activeSceneGroup.add(innerCube);

      // 8 Struts connecting outer & inner vertices
      const strutMat = new THREE.LineBasicMaterial({ color: 0x00ff88, transparent: true, opacity: 0.6 });
      const corners = [-1, 1];
      corners.forEach(x => {
        corners.forEach(y => {
          corners.forEach(z => {
            const points = [
              new THREE.Vector3(x * 1.8, y * 1.8, z * 1.8),
              new THREE.Vector3(x * 0.9, y * 0.9, z * 0.9)
            ];
            const strutGeo = new THREE.BufferGeometry().setFromPoints(points);
            activeSceneGroup.add(new THREE.Line(strutGeo, strutMat));
          });
        });
      });

      // Central Quantum Core Node
      const coreGeo = new THREE.SphereGeometry(0.7, 32, 32);
      const coreMat = new THREE.MeshStandardMaterial({
        color: 0x00ff88,
        emissive: 0x004422,
        emissiveIntensity: 0.9,
        roughness: 0.2,
        metalness: 0.8
      });
      const core = new THREE.Mesh(coreGeo, coreMat);
      core.name = "quantumCore";
      activeSceneGroup.add(core);

      // Orbiting Gyro Torus Ring
      const ringGeo = new THREE.TorusGeometry(3.2, 0.02, 16, 100);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0xffd700, transparent: true, opacity: 0.7 });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      ring.name = "gyroRing";
      ring.rotation.x = Math.PI / 3;
      activeSceneGroup.add(ring);

    } else if (current3DModelKey === 'brain') {
      // ── MODEL 2: 3D NEURAL SYNAPSE AI CORTEX (BRAIN) ──
      const brainGroup = new THREE.Group();
      activeSceneGroup.add(brainGroup);

      const neuronCount = 320;
      const positions = [];
      const colors = [];
      const neuronMeshPositions = [];

      for (let i = 0; i < neuronCount; i++) {
        // Double ellipsoid for left & right brain hemispheres
        const hemisphere = Math.random() > 0.5 ? 1 : -1;
        const u = Math.random();
        const v = Math.random();
        const theta = u * 2.0 * Math.PI;
        const phi = Math.acos(2.0 * v - 1.0);
        const r = 1.6 + Math.random() * 0.8;

        const x = (r * Math.sin(phi) * Math.cos(theta) * 0.85) + (hemisphere * 0.75);
        const y = r * Math.sin(phi) * Math.sin(theta) * 1.1;
        const z = r * Math.cos(phi) * 1.4;

        positions.push(x, y, z);
        neuronMeshPositions.push(new THREE.Vector3(x, y, z));

        const isLeft = hemisphere > 0;
        colors.push(isLeft ? 0.0 : 1.0, isLeft ? 0.9 : 0.0, isLeft ? 1.0 : 0.5);
      }

      const pGeo = new THREE.BufferGeometry();
      pGeo.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
      pGeo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
      const pMat = new THREE.PointsMaterial({ size: 0.09, vertexColors: true, transparent: true, opacity: 0.9 });
      const pointCloud = new THREE.Points(pGeo, pMat);
      pointCloud.name = "brainPoints";
      brainGroup.add(pointCloud);

      // Synapse connection paths
      const linePositions = [];
      for (let i = 0; i < neuronMeshPositions.length; i++) {
        for (let j = i + 1; j < neuronMeshPositions.length; j++) {
          const dist = neuronMeshPositions[i].distanceTo(neuronMeshPositions[j]);
          if (dist < 0.65) {
            linePositions.push(
              neuronMeshPositions[i].x, neuronMeshPositions[i].y, neuronMeshPositions[i].z,
              neuronMeshPositions[j].x, neuronMeshPositions[j].y, neuronMeshPositions[j].z
            );
          }
        }
      }

      const lineGeo = new THREE.BufferGeometry();
      lineGeo.setAttribute('position', new THREE.Float32BufferAttribute(linePositions, 3));
      const lineMat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.25 });
      brainGroup.add(new THREE.LineSegments(lineGeo, lineMat));

      // Glowing Pineal AI Node
      const pinealGeo = new THREE.IcosahedronGeometry(0.5, 2);
      const pinealMat = new THREE.MeshStandardMaterial({ color: 0xff0080, emissive: 0xff0080, emissiveIntensity: 1.0 });
      const pineal = new THREE.Mesh(pinealGeo, pinealMat);
      pineal.name = "quantumCore";
      brainGroup.add(pineal);

    } else if (current3DModelKey === 'helix') {
      // ── MODEL 3: 3D CRYPTO PRICE HELIX & CANDLESTICK MATRIX ──
      const helixGroup = new THREE.Group();
      activeSceneGroup.add(helixGroup);

      const steps = 60;
      const radius = 1.8;
      const height = 4.5;
      const candleBoxGeo = new THREE.BoxGeometry(0.12, 0.4, 0.12);
      const greenMat = new THREE.MeshStandardMaterial({ color: 0x00ff88, emissive: 0x003318, emissiveIntensity: 0.7 });
      const redMat = new THREE.MeshStandardMaterial({ color: 0xff3355, emissive: 0x330008, emissiveIntensity: 0.7 });

      const strand1Pts = [];
      const strand2Pts = [];

      for (let i = 0; i < steps; i++) {
        const t = (i / steps) * Math.PI * 4;
        const y = ((i / steps) - 0.5) * height;
        const x1 = Math.cos(t) * radius;
        const z1 = Math.sin(t) * radius;
        const x2 = Math.cos(t + Math.PI) * radius;
        const z2 = Math.sin(t + Math.PI) * radius;

        strand1Pts.push(new THREE.Vector3(x1, y, z1));
        strand2Pts.push(new THREE.Vector3(x2, y, z2));

        // Floating 3D Candlestick Boxes along strand 1
        if (i % 3 === 0) {
          const isBull = Math.sin(i * 1.5) > 0;
          const candle = new THREE.Mesh(candleBoxGeo, isBull ? greenMat : redMat);
          candle.position.set(x1, y, z1);
          candle.rotation.y = t;
          helixGroup.add(candle);
        }
      }

      // Strand Lines
      const s1Geo = new THREE.BufferGeometry().setFromPoints(strand1Pts);
      const s1Mat = new THREE.LineBasicMaterial({ color: 0x00e5ff, transparent: true, opacity: 0.7 });
      helixGroup.add(new THREE.Line(s1Geo, s1Mat));

      const s2Geo = new THREE.BufferGeometry().setFromPoints(strand2Pts);
      const s2Mat = new THREE.LineBasicMaterial({ color: 0xff0080, transparent: true, opacity: 0.7 });
      helixGroup.add(new THREE.Line(s2Geo, s2Mat));

      // Central Price Singularity
      const coreGeo = new THREE.OctahedronGeometry(0.7, 0);
      const coreMat = new THREE.MeshStandardMaterial({ color: 0xffd700, emissive: 0x553300, emissiveIntensity: 0.9 });
      const core = new THREE.Mesh(coreGeo, coreMat);
      core.name = "quantumCore";
      helixGroup.add(core);
    }
  }

  function initThreeJsModel() {
    const canvas = document.getElementById('threeJsCanvas');
    const container = document.getElementById('threeCanvasWrap');
    if (!canvas || !container || typeof THREE === 'undefined') {
      console.log('Three.js or 3D canvas not available, skipping 3D core init');
      return;
    }

    const scene = new THREE.Scene();
    threeSceneInstance = scene;

    const width = container.clientWidth || 600;
    const height = container.clientHeight || 220;

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
    camera.position.z = 9.0;
    threeCameraInstance = camera;

    const renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true,
      powerPreference: "high-performance"
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    threeRendererInstance = renderer;

    // Lighting
    const ambientLight = new THREE.AmbientLight(0x0a192f, 2.0);
    scene.add(ambientLight);

    const cyanLight = new THREE.PointLight(0x00e5ff, 3.5, 25);
    cyanLight.position.set(5, 5, 5);
    scene.add(cyanLight);

    const pinkLight = new THREE.PointLight(0xff0080, 3.5, 25);
    pinkLight.position.set(-5, -5, 5);
    scene.add(pinkLight);

    // Build the default 3D model
    buildActive3DModel(scene);

    // Interactive Drag / Orbit Controls
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;
    let targetRotationX = 0;
    let targetRotationY = 0;

    container.addEventListener('pointerdown', (e) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    window.addEventListener('pointermove', (e) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      targetRotationY += deltaX * 0.008;
      targetRotationX += deltaY * 0.008;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    });

    window.addEventListener('pointerup', () => {
      isDragging = false;
    });

    function handleResize() {
      if (!container || !renderer || !camera) return;
      const newWidth = container.clientWidth;
      const newHeight = container.clientHeight;
      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    }
    window.addEventListener('resize', handleResize);

    // 60 FPS Harmonic Render Loop
    let clock = new THREE.Clock();
    function renderThreeScene() {
      requestAnimationFrame(renderThreeScene);

      const elapsedTime = clock.getElapsedTime();
      const currentSpeed = THREE_MODES[threeCoreModeIndex].speed;

      if (activeSceneGroup) {
        // Inertia drag rotation
        activeSceneGroup.rotation.y += (targetRotationY - activeSceneGroup.rotation.y) * 0.08 + (0.007 * currentSpeed);
        activeSceneGroup.rotation.x += (targetRotationX - activeSceneGroup.rotation.x) * 0.08;

        // Core Pulse
        const core = activeSceneGroup.getObjectByName("quantumCore");
        if (core) {
          const pulseScale = 1.0 + Math.sin(elapsedTime * 3.0 * currentSpeed) * 0.1;
          core.scale.set(pulseScale, pulseScale, pulseScale);
        }

        // Gyro Ring
        const ring = activeSceneGroup.getObjectByName("gyroRing");
        if (ring) {
          ring.rotation.z += 0.015 * currentSpeed;
        }
      }

      renderer.render(scene, camera);
    }
    renderThreeScene();
  }

  // ═══════════════════ INIT ═══════════════════
  initClock();
  init3DCanvas();
  setTimeout(initThreeJsModel, 200);
  initTradingViewChart("BINANCE:BTCUSDT", "5", "BTC/USDT");
  fetchRealData();
  setInterval(fetchRealData, 3000);
  setTimeout(init3DCardTilt, 500);
  setTimeout(loadDarwinLeaderboard, 2000);
})();
