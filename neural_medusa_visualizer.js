/**
 * NEURAL MEDUSA-01 & YC SECOND BRAIN INTERACTIVE VISUALIZER
 * High-performance 60FPS dual-mode canvas engine:
 * Mode A: "MEDUSA-01" - 3D Bioluminescent jellyfish dome with trailing neural filaments and floating contract tokens
 * Mode B: "YC SECOND BRAIN" - Force-directed knowledge cluster graph with neural bridges, category bubbles and agent centroids
 */

(function () {
  'use strict';

  class NeuralMedusaEngine {
    constructor(canvasId, options = {}) {
      this.canvas = document.getElementById(canvasId);
      if (!this.canvas) return;
      this.ctx = this.canvas.getContext('2d');
      this.mode = options.mode || 'medusa'; // 'medusa' or 'yc_brain'
      this.width = 0;
      this.height = 0;
      this.animId = null;
      this.lastTime = performance.now();
      this.fps = 60;
      this.frameCount = 0;
      this.fpsTimer = performance.now();
      this.yaw = 0;
      this.pitch = 0.2;

      // Mouse interaction
      this.mouse = { x: 0, y: 0, isHover: false };

      this.initNodes();
      this.resize();
      window.addEventListener('resize', () => this.resize());

      this.canvas.addEventListener('mousemove', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - rect.left;
        this.mouse.y = e.clientY - rect.top;
        this.mouse.isHover = true;
      });

      this.canvas.addEventListener('mouseleave', () => {
        this.mouse.isHover = false;
      });

      this.animate = this.animate.bind(this);
      this.start();
    }

    setMode(newMode) {
      this.mode = newMode;
      const modeBtnMedusa = document.getElementById('btnModeMedusa');
      const modeBtnYc = document.getElementById('btnModeYc');
      if (modeBtnMedusa && modeBtnYc) {
        if (newMode === 'medusa') {
          modeBtnMedusa.classList.add('active');
          modeBtnYc.classList.remove('active');
        } else {
          modeBtnYc.classList.add('active');
          modeBtnMedusa.classList.remove('active');
        }
      }
    }

    resize() {
      if (!this.canvas) return;
      const rect = this.canvas.parentElement.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      this.width = rect.width;
      this.height = rect.height || 380;
      this.canvas.width = this.width * dpr;
      this.canvas.height = this.height * dpr;
      this.ctx.scale(dpr, dpr);
    }

    initNodes() {
      // 1. Medusa Dome Nodes (3D Hemispherical layout)
      this.medusaDomeParticles = [];
      const domeCount = 180;
      for (let i = 0; i < domeCount; i++) {
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(Math.random()) * 0.95; // Hemispherical dome
        const radius = 110 + Math.random() * 25;
        this.medusaDomeParticles.push({
          x: radius * Math.sin(phi) * Math.cos(theta),
          y: -radius * Math.cos(phi) + 20,
          z: radius * Math.sin(phi) * Math.sin(theta),
          origRadius: radius,
          phi,
          theta,
          pulse: Math.random() * Math.PI * 2,
          color: Math.random() > 0.4 ? '#00f0ff' : (Math.random() > 0.5 ? '#ff6b00' : '#ec4899')
        });
      }

      // Medusa Tentacles / Neural Filaments
      this.tentacles = [];
      const tentacleCount = 16;
      for (let t = 0; t < tentacleCount; t++) {
        const angle = (t / tentacleCount) * Math.PI * 2;
        const r = 80 + (t % 3) * 15;
        const rootX = r * Math.cos(angle);
        const rootZ = r * Math.sin(angle);
        const segments = [];
        const segCount = 18;
        for (let s = 0; s < segCount; s++) {
          segments.push({
            x: rootX,
            y: 20 + s * 12,
            z: rootZ,
            offset: Math.random() * Math.PI * 2
          });
        }
        this.tentacles.push({ rootX, rootZ, segments, color: t % 2 === 0 ? '#00f0ff' : '#a855f7' });
      }

      // Floating Trading Brain Tokens (Medusa mode labels)
      this.floatingTokens = [
        { label: 'COINBASE::PERP', sub: 'ETH-PERP / BTC-PERP', x: -140, y: -60, z: 20, color: '#00f0ff' },
        { label: 'DELTA::INDIA', sub: 'XRPUSD / BTC FUTURES', x: 140, y: -50, z: 10, color: '#00e676' },
        { label: 'COINSWITCH::PRO', sub: 'SPOT ROUTER / USDT', x: -120, y: 70, z: -30, color: '#ff6b00' },
        { label: 'PP_SUPERTREND', sub: 'P=2 / ATR=3.0 / 10', x: 130, y: 65, z: 30, color: '#ec4899' },
        { label: 'GHOST_PROTOCOL', sub: 'REVERSAL V3 + FRVP', x: 0, y: -125, z: -20, color: '#38bdf8' },
        { label: 'CAPITAL_SAFEGUARD', sub: 'TRAILING RATCHET 70%', x: 0, y: 140, z: 40, color: '#f59e0b' }
      ];

      // 2. YC Second Brain Clusters (Mode B)
      this.clusters = [
        { id: 'gbrain', name: 'ONE MEMORY CORE', count: 42, color: '#00f0ff', x: 0, y: -20 },
        { id: 'claude', name: 'NEMOTRON / GLM-5.3', count: 28, color: '#ff6b00', x: -180, y: -80 },
        { id: 'delta', name: 'DELTA FUTURES', count: 18, color: '#00e676', x: 190, y: -70 },
        { id: 'coinbase', name: 'COINBASE DERIVATIVES', count: 15, color: '#38bdf8', x: -160, y: 90 },
        { id: 'signals', name: 'GHOST REVERSALS', count: 33, color: '#ec4899', x: 170, y: 80 },
        { id: 'risk', name: 'RISK / DRAWDOWN', count: 24, color: '#fbbf24', x: 0, y: 130 }
      ];

      this.ycParticles = [];
      for (let i = 0; i < 90; i++) {
        const cluster = this.clusters[i % this.clusters.length];
        const angle = Math.random() * Math.PI * 2;
        const dist = 25 + Math.random() * 55;
        this.ycParticles.push({
          clusterId: cluster.id,
          x: cluster.x + Math.cos(angle) * dist,
          y: cluster.y + Math.sin(angle) * dist,
          vx: (Math.random() - 0.5) * 0.4,
          vy: (Math.random() - 0.5) * 0.4,
          size: 1.5 + Math.random() * 2.5,
          color: cluster.color
        });
      }
    }

    animate(now) {
      this.animId = requestAnimationFrame(this.animate);
      const delta = (now - this.lastTime) / 1000;
      this.lastTime = now;

      // Calculate FPS
      this.frameCount++;
      if (now - this.fpsTimer >= 500) {
        this.fps = Math.round((this.frameCount * 1000) / (now - this.fpsTimer));
        this.frameCount = 0;
        this.fpsTimer = now;
        const fpsEl = document.getElementById('medusaFpsVal');
        if (fpsEl) fpsEl.textContent = this.fps + ' FPS';
        const yawEl = document.getElementById('medusaYawVal');
        if (yawEl) yawEl.textContent = 'YAW ' + Math.round((this.yaw * 180 / Math.PI) % 360) + '°';
      }

      this.yaw += 0.008;

      this.ctx.clearRect(0, 0, this.width, this.height);

      if (this.mode === 'medusa') {
        this.renderMedusaMode(now);
      } else {
        this.renderYcBrainMode(now);
      }
    }

    // 3D Projection Helper
    project(x, y, z, cx, cy) {
      // Rotate around Y axis
      const cosY = Math.cos(this.yaw);
      const sinY = Math.sin(this.yaw);
      const x1 = x * cosY - z * sinY;
      const z1 = x * sinY + z * cosY;

      // Rotate around X axis
      const cosX = Math.cos(this.pitch);
      const sinX = Math.sin(this.pitch);
      const y2 = y * cosX - z1 * sinX;
      const z2 = y * sinX + z1 * cosX;

      const fov = 340;
      const distance = 420;
      const scale = fov / (distance + z2);

      return {
        x: cx + x1 * scale,
        y: cy + y2 * scale,
        scale,
        depth: z2
      };
    }

    renderMedusaMode(now) {
      const cx = this.width / 2;
      const cy = this.height / 2 - 15;

      // Draw faint background dome ring
      this.ctx.save();
      this.ctx.strokeStyle = 'rgba(0, 240, 255, 0.05)';
      this.ctx.lineWidth = 1;
      this.ctx.beginPath();
      this.ctx.arc(cx, cy, 160, 0, Math.PI * 2);
      this.ctx.stroke();
      this.ctx.restore();

      // Project & Render Dome Particles
      const projectedDome = this.medusaDomeParticles.map(p => {
        // Breathe oscillation
        const breathe = Math.sin(now * 0.002 + p.pulse) * 4;
        const r = p.origRadius + breathe;
        const x = r * Math.sin(p.phi) * Math.cos(p.theta);
        const y = -r * Math.cos(p.phi) + 20;
        const z = r * Math.sin(p.phi) * Math.sin(p.theta);
        const proj = this.project(x, y, z, cx, cy);
        return { ...p, px: proj.x, py: proj.y, scale: proj.scale, depth: proj.depth };
      });

      // Sort by depth for correct 3D occlusion
      projectedDome.sort((a, b) => b.depth - a.depth);

      // Render Dome Neural Interconnects
      this.ctx.lineWidth = 0.6;
      for (let i = 0; i < projectedDome.length; i++) {
        const p1 = projectedDome[i];
        if (p1.scale < 0.2) continue;
        for (let j = i + 1; j < Math.min(i + 5, projectedDome.length); j++) {
          const p2 = projectedDome[j];
          const dx = p1.px - p2.px;
          const dy = p1.py - p2.py;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < 45) {
            const alpha = (1 - dist / 45) * 0.25 * Math.min(p1.scale, 1.2);
            this.ctx.strokeStyle = `rgba(0, 240, 255, ${alpha})`;
            this.ctx.beginPath();
            this.ctx.moveTo(p1.px, p1.py);
            this.ctx.lineTo(p2.px, p2.py);
            this.ctx.stroke();
          }
        }
      }

      // Render Dome Points
      for (const p of projectedDome) {
        if (p.scale < 0.1) continue;
        const size = Math.max(1, 2.2 * p.scale);
        this.ctx.fillStyle = p.color;
        this.ctx.shadowColor = p.color;
        this.ctx.shadowBlur = 6 * p.scale;
        this.ctx.beginPath();
        this.ctx.arc(p.px, p.py, size, 0, Math.PI * 2);
        this.ctx.fill();
      }
      this.ctx.shadowBlur = 0; // Reset blur

      // Render Bioluminescent Tentacles (Filaments trailing downwards)
      for (const t of this.tentacles) {
        this.ctx.strokeStyle = t.color;
        this.ctx.lineWidth = 1.2;
        this.ctx.beginPath();

        let prevP = null;
        for (let s = 0; s < t.segments.length; s++) {
          const seg = t.segments[s];
          const wave = Math.sin(now * 0.003 + seg.offset + s * 0.2) * (s * 2.8);
          const proj = this.project(seg.x + wave, seg.y, seg.z, cx, cy);

          if (s === 0) {
            this.ctx.moveTo(proj.x, proj.y);
          } else {
            const xc = (prevP.x + proj.x) / 2;
            const yc = (prevP.y + proj.y) / 2;
            this.ctx.quadraticCurveTo(prevP.x, prevP.y, xc, yc);
          }
          prevP = proj;
        }
        this.ctx.globalAlpha = 0.45;
        this.ctx.stroke();
        this.ctx.globalAlpha = 1.0;
      }

      // Render Floating Labeled Tokens with connecting stalks (Video 2 Style)
      for (const tok of this.floatingTokens) {
        const proj = this.project(tok.x, tok.y, tok.z, cx, cy);
        if (proj.scale < 0.2) continue;

        // Draw connecting filament to origin
        this.ctx.strokeStyle = 'rgba(0, 240, 255, 0.25)';
        this.ctx.lineWidth = 1;
        this.ctx.setLineDash([2, 4]);
        this.ctx.beginPath();
        this.ctx.moveTo(cx, cy);
        this.ctx.lineTo(proj.x, proj.y);
        this.ctx.stroke();
        this.ctx.setLineDash([]);

        // Node Glow Dot
        this.ctx.fillStyle = tok.color;
        this.ctx.shadowColor = tok.color;
        this.ctx.shadowBlur = 8;
        this.ctx.beginPath();
        this.ctx.arc(proj.x, proj.y, 4 * proj.scale, 0, Math.PI * 2);
        this.ctx.fill();
        this.ctx.shadowBlur = 0;

        // Labeled Pill Tag (from Video 2: CLAUDE.md, brain.py style)
        this.ctx.font = `600 ${Math.max(9, Math.round(10 * proj.scale))}px "JetBrains Mono", monospace`;
        const textWidth = this.ctx.measureText(tok.label).width;
        const boxW = textWidth + 14;
        const boxH = 18 * proj.scale;
        const boxX = proj.x + 8;
        const boxY = proj.y - boxH / 2;

        this.ctx.fillStyle = 'rgba(6, 11, 24, 0.88)';
        this.ctx.strokeStyle = tok.color;
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.roundRect(boxX, boxY, boxW, boxH, 4);
        this.ctx.fill();
        this.ctx.stroke();

        this.ctx.fillStyle = '#f8fafc';
        this.ctx.fillText(tok.label, boxX + 7, boxY + boxH * 0.72);
      }
    }

    renderYcBrainMode(now) {
      const cx = this.width / 2;
      const cy = this.height / 2;

      // Draw Neural Cluster Bridges
      this.ctx.lineWidth = 1.2;
      for (let i = 0; i < this.clusters.length; i++) {
        const c1 = this.clusters[i];
        for (let j = i + 1; j < this.clusters.length; j++) {
          const c2 = this.clusters[j];
          const grad = this.ctx.createLinearGradient(cx + c1.x, cy + c1.y, cx + c2.x, cy + c2.y);
          grad.addColorStop(0, c1.color + '33');
          grad.addColorStop(1, c2.color + '33');
          this.ctx.strokeStyle = grad;
          this.ctx.beginPath();
          this.ctx.moveTo(cx + c1.x, cy + c1.y);
          this.ctx.lineTo(cx + c2.x, cy + c2.y);
          this.ctx.stroke();
        }
      }

      // Draw Clustered Particles with gentle drift
      for (const p of this.ycParticles) {
        p.x += p.vx;
        p.y += p.vy;

        // Bound to cluster centroid
        const cluster = this.clusters.find(c => c.id === p.clusterId);
        if (cluster) {
          const dx = p.x - cluster.x;
          const dy = p.y - cluster.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist > 70) {
            p.vx -= dx * 0.005;
            p.vy -= dy * 0.005;
          }
        }

        // Draw particle
        this.ctx.fillStyle = p.color;
        this.ctx.beginPath();
        this.ctx.arc(cx + p.x, cy + p.y, p.size, 0, Math.PI * 2);
        this.ctx.fill();
      }

      // Draw Main Cluster Centroids (Video 1 style: gbrain, people, companies)
      for (const c of this.clusters) {
        const nx = cx + c.x;
        const ny = cy + c.y;

        // Outer glowing halo
        this.ctx.strokeStyle = c.color;
        this.ctx.lineWidth = 1.5;
        this.ctx.shadowColor = c.color;
        this.ctx.shadowBlur = 10;
        this.ctx.beginPath();
        this.ctx.arc(nx, ny, 16, 0, Math.PI * 2);
        this.ctx.stroke();
        this.ctx.shadowBlur = 0;

        // Inner solid core
        this.ctx.fillStyle = c.color;
        this.ctx.beginPath();
        this.ctx.arc(nx, ny, 6, 0, Math.PI * 2);
        this.ctx.fill();

        // Cluster Card Label
        this.ctx.font = '700 11px "Outfit", sans-serif';
        const label = `${c.name} (${c.count})`;
        const w = this.ctx.measureText(label).width;

        this.ctx.fillStyle = 'rgba(5, 8, 17, 0.9)';
        this.ctx.strokeStyle = c.color;
        this.ctx.lineWidth = 1;
        this.ctx.beginPath();
        this.ctx.roundRect(nx - w / 2 - 8, ny + 22, w + 16, 20, 4);
        this.ctx.fill();
        this.ctx.stroke();

        this.ctx.fillStyle = '#ffffff';
        this.ctx.fillText(label, nx - w / 2, ny + 36);
      }
    }

    stop() {
      if (this.animId) cancelAnimationFrame(this.animId);
    }

    start() {
      this.lastTime = performance.now();
      this.animate(this.lastTime);
    }
  }

  // Mini Sparkline Renderer Helper
  window.renderMiniSparkline = function (canvasId, dataPoints, strokeColor = '#00f0ff') {
    const cvs = document.getElementById(canvasId);
    if (!cvs) return;
    const ctx = cvs.getContext('2d');
    const w = cvs.width = cvs.parentElement.clientWidth || 100;
    const h = cvs.height = cvs.parentElement.clientHeight || 28;

    if (!dataPoints || dataPoints.length < 2) return;
    const min = Math.min(...dataPoints);
    const max = Math.max(...dataPoints);
    const range = (max - min) || 1;

    ctx.clearRect(0, 0, w, h);
    ctx.strokeStyle = strokeColor;
    ctx.lineWidth = 1.5;
    ctx.beginPath();

    for (let i = 0; i < dataPoints.length; i++) {
      const x = (i / (dataPoints.length - 1)) * w;
      const y = h - ((dataPoints[i] - min) / range) * (h - 6) - 3;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();

    // Fill under curve
    ctx.lineTo(w, h);
    ctx.lineTo(0, h);
    ctx.closePath();
    ctx.fillStyle = strokeColor + '1a';
    ctx.fill();
  };

  // Expose to window
  window.NeuralMedusaEngine = NeuralMedusaEngine;
})();
