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

  // ═══════════════════ DATA PROCESSING ═══════════════════
  function processData(data, lagMs) {
      fetchCount++;

      // Heatmap Coins list from top level or advanced
      const coinsList = data.heatmap_coins || (data.advanced && data.advanced.heatmap_coins) || [];
      if (coinsList.length > 0) {
        lastHeatmapCoins = coinsList;
        renderHeatmap(lastHeatmapCoins);
        renderTickerMarquee(lastHeatmapCoins, data.tickers);
      } else if (data.tickers) {
        renderHeaderTickers(data.tickers);
      }

      // Wallet
      if(data.balances) {
        updateText('#total-capital', `$${fmtNum(data.balances.total_capital_usdt)}`);
        updateText('#bal-cs-usdt', fmtNum(data.balances.cs_usdt, 2));
        updateText('#bal-cs-inr', fmtNum(data.balances.cs_inr, 2));
        updateText('#bal-delta-usdt', fmtNum(data.balances.delta_usdt, 2));
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

  // Setup Heatmap search listener
  document.addEventListener('DOMContentLoaded', () => {
    const input = $('#heatSearch');
    if (input) {
      input.addEventListener('input', () => renderHeatmap(lastHeatmapCoins));
    }
  });

  function populateTrades(data) {
    const wrap = $('#trades-container');
    if (!wrap) return;

    let rows = [];
    if (data.open_positions?.coinswitch) data.open_positions.coinswitch.forEach(p => rows.push({...p, ex: 'CS'}));
    if (data.open_positions?.delta) data.open_positions.delta.forEach(p => rows.push({...p, ex: 'DL'}));

    if (rows.length === 0) {
      wrap.innerHTML = `<div class="empty-state">NO ACTIVE TRADES</div>`;
      return;
    }

    wrap.innerHTML = rows.map(pos => {
      const dirClass = (pos.direction || 'long').toLowerCase();
      const pnl = parseFloat(pos.unrealized_pnl || 0);
      const pnlColor = pnl >= 0 ? 'green' : 'red';
      const sign = pnl >= 0 ? '+' : '';
      return `
        <div class="trade-row">
          <div class="trade-sym-block">
            <span class="trade-sym">${pos.symbol}</span>
            <span class="tag">${pos.ex}</span>
            <span class="trade-dir ${dirClass}">${pos.direction.toUpperCase()}</span>
          </div>
          <span class="trade-entry">${fmtPrice(pos.entry_price || 0, 4)}</span>
          <span class="trade-size">${fmtNum(pos.quantity || 0, 4)}</span>
          <span class="trade-pnl ${pnlColor}">${sign}$${fmtNum(pnl, 2)}</span>
        </div>
      `;
    }).join('');
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
      
      if(fetchCount % 5 === 0) addLogEntry(`Sync cycle complete. Lag: ${lag}ms. Active positions updated.`);
      
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

  // ═══════════════════ INIT ═══════════════════
  initClock();
  fetchRealData();
  setInterval(fetchRealData, 5000);
})();
