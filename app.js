/* ==========================================================================
   0XFCDC POLYMARKET MAKER TERMINAL V2.1 — QUANT APPLICATION JS ENGINE
   Renders live dynamic canvas visualizers, neural network mesh, equity curve,
   fair-value probability model, volume histogram, and live ticking feeds.
   ========================================================================== */

document.addEventListener('DOMContentLoaded', () => {
  initClock();
  initTickerTapeAnimation();
  renderEquityCurve();
  renderConvexitySparkline();
  initNeuralMeshCanvas();
  renderAssetDonut();
  renderVolumeHistogram();
  renderProbabilityCurve();
  startLiveMetricsSimulation();
});

/* ── LIVE CLOCK ───────────────────────────────────────────────────────── */
function initClock() {
  const clockEl = document.getElementById('live-utc-clock');
  function update() {
    const now = new Date();
    const hrs = String(now.getUTCHours()).padStart(2, '0');
    const mins = String(now.getUTCMinutes()).padStart(2, '0');
    const secs = String(now.getUTCSeconds()).padStart(2, '0');
    if (clockEl) clockEl.textContent = `${hrs}:${mins}:${secs}`;
  }
  update();
  setInterval(update, 1000);
}

/* ── TICKER TAPE LIVE SIMULATION ─────────────────────────────────────── */
function initTickerTapeAnimation() {
  const tape = document.getElementById('tape-content');
  if (!tape) return;
  const trades = [
    { text: 'BUY ETH DOWN $3.86 @ $0.760', type: 'buy-down' },
    { text: 'BUY BTC UP $1.42 @ $0.270', type: 'buy-up' },
    { text: 'BUY SOL DOWN $23.17 @ $0.900', type: 'buy-down' },
    { text: 'BUY SOL DOWN $11.71 @ $0.910', type: 'buy-up' },
    { text: 'BUY XRP UP $14.50 @ $0.480', type: 'buy-up' },
    { text: 'BUY BTC DOWN $8.90 @ $0.730', type: 'buy-down' },
    { text: 'BUY ETH UP $12.40 @ $0.340', type: 'buy-up' },
    { text: 'BUY SOL UP $45.20 @ $0.120', type: 'buy-up' }
  ];

  function pushTrade() {
    const t = trades[Math.floor(Math.random() * trades.length)];
    const span = document.createElement('span');
    span.className = `tape-trade ${t.type}`;
    span.textContent = t.text;
    tape.appendChild(span);
    if (tape.children.length > 20) {
      tape.removeChild(tape.children[0]);
    }
  }
  setInterval(pushTrade, 2000);
}

/* ── EQUITY CURVE CANVAS ─────────────────────────────────────────────── */
function renderEquityCurve() {
  const canvas = document.getElementById('equityCurveCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;
  ctx.scale(dpr, dpr);

  const w = rect.width;
  const h = rect.height;

  // Generate smooth upward equity curve
  const points = [];
  let val = h * 0.75;
  for (let x = 0; x <= w; x += 10) {
    val += (Math.random() - 0.42) * 6;
    val = Math.max(10, Math.min(h - 10, val));
    points.push({ x, y: val });
  }

  // Draw gradient area under line
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, 'rgba(0, 255, 136, 0.35)');
  grad.addColorStop(1, 'rgba(0, 255, 136, 0.0)');

  ctx.beginPath();
  ctx.moveTo(0, h);
  points.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(w, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Draw glowing equity line
  ctx.beginPath();
  points.forEach((p, i) => i === 0 ? ctx.moveTo(p.x, p.y) : ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = '#00ff88';
  ctx.lineWidth = 2;
  ctx.shadowColor = '#00ff88';
  ctx.shadowBlur = 8;
  ctx.stroke();
  ctx.shadowBlur = 0;
}

/* ── SPARKLINE CANVAS ────────────────────────────────────────────────── */
function renderConvexitySparkline() {
  const canvas = document.getElementById('convexitySparkline');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const w = canvas.width;
  const h = canvas.height;

  ctx.clearRect(0, 0, w, h);
  ctx.beginPath();
  ctx.moveTo(0, h - 5);
  ctx.quadraticCurveTo(w * 0.6, h * 0.8, w, 5);
  ctx.strokeStyle = '#00ff88';
  ctx.lineWidth = 2.5;
  ctx.shadowColor = '#00ff88';
  ctx.shadowBlur = 10;
  ctx.stroke();
}

/* ── NEURAL MESH INTERACTIVE CANVAS VISUALIZER ───────────────────────── */
function initNeuralMeshCanvas() {
  const canvas = document.getElementById('neuralMeshCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  
  function resize() {
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width;
    canvas.height = rect.height;
  }
  resize();
  window.addEventListener('resize', resize);

  // Define 4 Neural Layers (Inputs -> Model -> Pairs -> Positions)
  const layers = [
    { name: 'INPUTS', count: 6, xRatio: 0.1 },
    { name: 'MODEL', count: 8, xRatio: 0.38 },
    { name: 'PAIRS', count: 7, xRatio: 0.68 },
    { name: 'POSITIONS', count: 5, xRatio: 0.9 }
  ];

  let pulses = [];

  function animate() {
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Calculate node coordinates
    const layerNodes = layers.map(layer => {
      const x = w * layer.xRatio;
      const nodes = [];
      const padding = 25;
      const availableH = h - padding * 2;
      const step = availableH / (layer.count - 1);
      for (let i = 0; i < layer.count; i++) {
        nodes.push({ x, y: padding + i * step });
      }
      return nodes;
    });

    // Draw connecting synapses
    ctx.lineWidth = 0.8;
    for (let l = 0; l < layerNodes.length - 1; l++) {
      const currentLayer = layerNodes[l];
      const nextLayer = layerNodes[l + 1];
      currentLayer.forEach(node1 => {
        nextLayer.forEach(node2 => {
          ctx.beginPath();
          ctx.moveTo(node1.x, node1.y);
          ctx.lineTo(node2.x, node2.y);
          ctx.strokeStyle = 'rgba(36, 49, 64, 0.4)';
          ctx.stroke();
        });
      });
    }

    // Spawn animated traveling pulses
    if (Math.random() < 0.3) {
      const lIdx = Math.floor(Math.random() * (layerNodes.length - 1));
      const n1 = layerNodes[lIdx][Math.floor(Math.random() * layerNodes[lIdx].length)];
      const n2 = layerNodes[lIdx + 1][Math.floor(Math.random() * layerNodes[lIdx + 1].length)];
      const isGreen = Math.random() > 0.3;
      pulses.push({
        x1: n1.x, y1: n1.y,
        x2: n2.x, y2: n2.y,
        progress: 0,
        speed: 0.02 + Math.random() * 0.03,
        color: isGreen ? '#00ff88' : '#00e5ff'
      });
    }

    // Update and draw traveling pulses
    pulses.forEach((p, idx) => {
      p.progress += p.speed;
      const px = p.x1 + (p.x2 - p.x1) * p.progress;
      const py = p.y1 + (p.y2 - p.y1) * p.progress;

      ctx.beginPath();
      ctx.arc(px, py, 3, 0, Math.PI * 2);
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 8;
      ctx.fill();
      ctx.shadowBlur = 0;

      if (p.progress >= 1) pulses.splice(idx, 1);
    });

    // Draw neural nodes
    layerNodes.forEach((layer, lIdx) => {
      layer.forEach(node => {
        ctx.beginPath();
        ctx.arc(node.x, node.y, 4, 0, Math.PI * 2);
        ctx.fillStyle = lIdx === 0 ? '#ff9900' : (lIdx === 3 ? '#00ff88' : '#00e5ff');
        ctx.shadowColor = ctx.fillStyle;
        ctx.shadowBlur = 6;
        ctx.fill();
        ctx.shadowBlur = 0;

        ctx.beginPath();
        ctx.arc(node.x, node.y, 2, 0, Math.PI * 2);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
      });
    });

    requestAnimationFrame(animate);
  }

  animate();
}

/* ── ASSET ALLOCATION DONUT CANVAS ───────────────────────────────────── */
function renderAssetDonut() {
  const canvas = document.getElementById('assetDonutCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const size = canvas.width;
  const center = size / 2;
  const radius = size * 0.38;
  const innerRadius = size * 0.26;

  const data = [
    { label: 'ETH', pct: 0.483, color: '#00ff88' },
    { label: 'SOL', pct: 0.227, color: '#00e5ff' },
    { label: 'BTC', pct: 0.203, color: '#ff9900' },
    { label: 'XRP', pct: 0.086, color: '#ffd700' }
  ];

  let startAngle = -Math.PI / 2;

  data.forEach(item => {
    const sliceAngle = item.pct * Math.PI * 2;
    ctx.beginPath();
    ctx.arc(center, center, radius, startAngle, startAngle + sliceAngle);
    ctx.arc(center, center, innerRadius, startAngle + sliceAngle, startAngle, true);
    ctx.closePath();
    ctx.fillStyle = item.color;
    ctx.shadowColor = item.color;
    ctx.shadowBlur = 4;
    ctx.fill();
    ctx.shadowBlur = 0;

    startAngle += sliceAngle;
  });
}

/* ── VOLUME HISTOGRAM CANVAS ─────────────────────────────────────────── */
function renderVolumeHistogram() {
  const canvas = document.getElementById('volumeHistogramCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  const w = canvas.width;
  const h = canvas.height;
  const numBars = 45;
  const barWidth = w / numBars - 2;

  for (let i = 0; i < numBars; i++) {
    const barHeight = Math.random() * (h * 0.85) + 5;
    const x = i * (barWidth + 2);
    const y = h - barHeight;

    ctx.fillStyle = i > numBars - 5 ? '#00ff88' : '#ffd700';
    ctx.fillRect(x, y, barWidth, barHeight);
  }
}

/* ── FAIR-VALUE PROBABILITY MODEL CANVAS ─────────────────────────────── */
function renderProbabilityCurve() {
  const canvas = document.getElementById('probabilityCurveCanvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');
  const rect = canvas.getBoundingClientRect();
  canvas.width = rect.width;
  canvas.height = rect.height;

  const w = canvas.width;
  const h = canvas.height;

  // Draw grid lines
  ctx.strokeStyle = '#16202c';
  ctx.lineWidth = 1;
  for (let y = 20; y < h; y += 30) {
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }

  // Draw Model Fair P(UP) curve (Green)
  ctx.beginPath();
  ctx.moveTo(20, h * 0.35);
  ctx.bezierCurveTo(w * 0.3, h * 0.2, w * 0.7, h * 0.6, w - 20, h * 0.5);
  ctx.strokeStyle = '#00ff88';
  ctx.lineWidth = 2.5;
  ctx.shadowColor = '#00ff88';
  ctx.shadowBlur = 8;
  ctx.stroke();
  ctx.shadowBlur = 0;

  // Draw Polymarket UP Ask curve (Yellow)
  ctx.beginPath();
  ctx.moveTo(20, h * 0.5);
  ctx.bezierCurveTo(w * 0.3, h * 0.55, w * 0.7, h * 0.7, w - 20, h * 0.65);
  ctx.strokeStyle = '#ffd700';
  ctx.lineWidth = 2;
  ctx.setLineDash([4, 4]);
  ctx.stroke();
  ctx.setLineDash([]);
}

/* ── LIVE REAL-TIME METRICS SIMULATION ──────────────────────────────── */
function startLiveMetricsSimulation() {
  async function fetchRealData() {
    try {
      const res = await fetch('/api/terminal-data');
      if (!res.ok) return;
      const data = await res.json();
      if (!data || data.status !== 'success') return;

      // Update Tickers
      if (data.tickers) {
        const btcEl = document.getElementById('header-btc');
        const ethEl = document.getElementById('header-eth');
        const solEl = document.getElementById('header-sol');
        const xrpEl = document.getElementById('header-xrp');
        if (btcEl && data.tickers.btc) btcEl.textContent = `$${data.tickers.btc.toLocaleString()}`;
        if (ethEl && data.tickers.eth) ethEl.textContent = `$${data.tickers.eth.toLocaleString()}`;
        if (solEl && data.tickers.sol) solEl.textContent = `$${data.tickers.sol.toLocaleString()}`;
        if (xrpEl && data.tickers.xrp) xrpEl.textContent = `$${data.tickers.xrp.toLocaleString()}`;
      }

      // Update Capital & Balances
      if (data.balances) {
        const pnlEl = document.getElementById('alltime-pnl');
        if (pnlEl) {
          const totalCap = data.balances.total_capital_usdt || 27.59;
          pnlEl.textContent = `$${totalCap.toFixed(2)} USDT`;
        }
      }

      // Update Positions Count
      if (data.open_positions) {
        const posHeldEl = document.getElementById('mesh-pos-held');
        if (posHeldEl) {
          posHeldEl.textContent = data.open_positions.total_count || 1;
        }
      }

      // Update Realized PnL & Trade Count
      if (data.performance) {
        const tradesEl = document.getElementById('header-trades');
        const statTradesEl = document.getElementById('stat-trades');
        const pnlTotalEl = document.getElementById('treasury-pnl-total');

        if (tradesEl) tradesEl.textContent = (data.performance.closed_trades_count || 0).toLocaleString();
        if (statTradesEl) statTradesEl.textContent = (data.performance.closed_trades_count || 0).toLocaleString();
        if (pnlTotalEl) {
          const pnlVal = data.performance.total_realized_pnl_usdt || 0.0;
          pnlTotalEl.textContent = `${pnlVal >= 0 ? '+' : ''}$${pnlVal.toFixed(2)} USDT`;
        }
      }

    } catch (e) {
      console.log('API sync notice:', e);
    }
  }

  fetchRealData();
  setInterval(fetchRealData, 3000);
}
