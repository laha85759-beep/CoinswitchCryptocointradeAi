// ==============================================================================
// 3D HOLOGRAPHIC AI AGENT CHARACTERS WORKFORCE ENGINE
// Renders live rotating Three.js 3D avatars for all 5 Company Trading Agents
// ==============================================================================

function init3DAgentWorkforce() {
  if (typeof THREE === "undefined") {
    console.debug("Three.js not loaded, waiting for library...");
    setTimeout(init3DAgentWorkforce, 300);
    return;
  }

  const agentConfigs = [
    {
      id: "agent3d-scout-canvas",
      color: 0x00f090,
      accent: 0x00d4ff,
      type: "scout" // Radar Sphere with Dual Orbiting Scanning Rings
    },
    {
      id: "agent3d-intel-canvas",
      color: 0x00d4ff,
      accent: 0x38bdf8,
      type: "intel" // Octahedron Crystal with Floating Data Matrix Nodes
    },
    {
      id: "agent3d-quant-canvas",
      color: 0xa855f7,
      accent: 0xec4899,
      type: "quant" // Icosahedron Quantum Core with Pulsing Geodesic Wireframe
    },
    {
      id: "agent3d-risk-canvas",
      color: 0xf59e0b,
      accent: 0xef4444,
      type: "risk" // Golden Hexagonal Shield Torus with Perimeter Barrier
    },
    {
      id: "agent3d-router-canvas",
      color: 0xec4899,
      accent: 0xa855f7,
      type: "router" // High-speed Hyper-Speed Plasma Knot with Lightning Accents
    }
  ];

  agentConfigs.forEach(cfg => {
    const canvas = document.getElementById(cfg.id);
    if (!canvas) return;

    const width = 120;
    const height = 100;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0, 4.5);

    const renderer = new THREE.WebGLRenderer({
      canvas: canvas,
      alpha: true,
      antialias: true
    });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));

    // Ambient & Point Lighting
    const ambLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambLight);

    const pLight = new THREE.PointLight(cfg.color, 2.5, 20);
    pLight.position.set(2, 3, 4);
    scene.add(pLight);

    const pLight2 = new THREE.PointLight(cfg.accent, 1.8, 20);
    pLight2.position.set(-2, -3, 2);
    scene.add(pLight2);

    const group = new THREE.Group();
    scene.add(group);

    // Build specialized 3D geometries for each Character
    if (cfg.type === "scout") {
      // Atlas Horizon: Central Sphere + Orbiting Radar Rings
      const coreGeo = new THREE.SphereGeometry(0.75, 16, 16);
      const coreMat = new THREE.MeshPhongMaterial({
        color: cfg.color,
        emissive: 0x004d2c,
        wireframe: true,
        transparent: true,
        opacity: 0.85
      });
      const core = new THREE.Mesh(coreGeo, coreMat);
      group.add(core);

      const ringGeo = new THREE.TorusGeometry(1.2, 0.035, 8, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color: cfg.accent, wireframe: true });
      const ring1 = new THREE.Mesh(ringGeo, ringMat);
      ring1.rotation.x = Math.PI / 3;
      group.add(ring1);

      const ring2 = new THREE.Mesh(ringGeo, ringMat);
      ring2.rotation.y = Math.PI / 4;
      group.add(ring2);

    } else if (cfg.type === "intel") {
      // Sentinel Intel: Floating Octahedron Data Diamond
      const geo = new THREE.OctahedronGeometry(1.0, 0);
      const mat = new THREE.MeshStandardMaterial({
        color: cfg.color,
        emissive: 0x002244,
        roughness: 0.2,
        metalness: 0.8,
        wireframe: false
      });
      const diamond = new THREE.Mesh(geo, mat);
      group.add(diamond);

      const wireGeo = new THREE.OctahedronGeometry(1.25, 0);
      const wireMat = new THREE.MeshBasicMaterial({ color: cfg.accent, wireframe: true });
      const wire = new THREE.Mesh(wireGeo, wireMat);
      group.add(wire);

    } else if (cfg.type === "quant") {
      // Dr. Nemotron: Icosahedron Neural Core
      const geo = new THREE.IcosahedronGeometry(0.9, 0);
      const mat = new THREE.MeshPhongMaterial({
        color: cfg.color,
        emissive: 0x2e0854,
        wireframe: false
      });
      const quantCore = new THREE.Mesh(geo, mat);
      group.add(quantCore);

      const outerGeo = new THREE.IcosahedronGeometry(1.3, 1);
      const outerMat = new THREE.MeshBasicMaterial({
        color: cfg.accent,
        wireframe: true,
        transparent: true,
        opacity: 0.75
      });
      const outer = new THREE.Mesh(outerGeo, outerMat);
      group.add(outer);

    } else if (cfg.type === "risk") {
      // Aegis Guardian: Golden Hexagonal Shield Torus
      const geo = new THREE.TorusGeometry(0.9, 0.35, 6, 6);
      const mat = new THREE.MeshStandardMaterial({
        color: cfg.color,
        emissive: 0x451a03,
        roughness: 0.3,
        metalness: 0.9
      });
      const shield = new THREE.Mesh(geo, mat);
      group.add(shield);

      const ringGeo = new THREE.TorusGeometry(1.4, 0.02, 16, 32);
      const ringMat = new THREE.MeshBasicMaterial({ color: 0xfde68a, wireframe: true });
      const ring = new THREE.Mesh(ringGeo, ringMat);
      group.add(ring);

    } else {
      // Valkyrie Router: High-Speed Torus Knot Router
      const geo = new THREE.TorusKnotGeometry(0.65, 0.2, 48, 8, 2, 3);
      const mat = new THREE.MeshStandardMaterial({
        color: cfg.color,
        emissive: 0x500724,
        roughness: 0.2,
        metalness: 0.8
      });
      const routerMesh = new THREE.Mesh(geo, mat);
      group.add(routerMesh);
    }

    // Animation Loop
    let clock = new THREE.Clock();
    function animate() {
      requestAnimationFrame(animate);
      const delta = clock.getDelta();
      const time = clock.getElapsedTime();

      group.rotation.y += 0.85 * delta;
      group.rotation.x = Math.sin(time * 0.8) * 0.2;
      group.position.y = Math.sin(time * 1.5) * 0.08;

      renderer.render(scene, camera);
    }
    animate();
  });
}

// Hook into DOM ready and window load
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => setTimeout(init3DAgentWorkforce, 200));
} else {
  setTimeout(init3DAgentWorkforce, 200);
}
window.init3DAgentWorkforce = init3DAgentWorkforce;

// Global fallback: if Three.js or WebGL fails, render vibrant glowing holographic neon canvas icons
function drawFallbackAgentAvatars() {
  const configs = [
    { id: 'agent3d-scout-canvas', color: '#00f090', label: 'SCOUT' },
    { id: 'agent3d-intel-canvas', color: '#00d4ff', label: 'INTEL' },
    { id: 'agent3d-quant-canvas', color: '#a855f7', label: 'QUANT' },
    { id: 'agent3d-risk-canvas', color: '#f59e0b', label: 'RISK' },
    { id: 'agent3d-router-canvas', color: '#ec4899', label: 'ROUTER' }
  ];
  configs.forEach(cfg => {
    const canvas = document.getElementById(cfg.id);
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    ctx.save();
    ctx.beginPath();
    ctx.arc(w / 2, h / 2, 32, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(10, 25, 45, 0.8)';
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = cfg.color;
    ctx.shadowColor = cfg.color;
    ctx.shadowBlur = 12;
    ctx.stroke();
    ctx.font = 'bold 10px monospace';
    ctx.fillStyle = cfg.color;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(cfg.label, w / 2, h / 2);
    ctx.restore();
  });
}
window.drawFallbackAgentAvatars = drawFallbackAgentAvatars;


// ==============================================================================
// HERO 3D HOLOGRAPHIC AI TRADING AVATAR CHARACTER
// Renders an innovative futuristic 3D Cybernetic Core with dual orbiting rings,
// pulsing quantum core, and neural particle fields.
// ==============================================================================
function initHero3DCharacter() {
  const canvas = document.getElementById("agent3d-hero-character");
  if (!canvas) return;

  if (typeof THREE === "undefined") {
    setTimeout(initHero3DCharacter, 300);
    return;
  }

  const container = canvas.parentElement;
  const width = canvas.clientWidth || 460;
  const height = canvas.clientHeight || 320;

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.z = 4.8;
  camera.position.y = 0.2;

  let renderer;
  try {
    renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  } catch (e) {
    console.warn("WebGL not supported for hero character, using canvas fallback", e);
    drawHeroFallbackAvatar();
    return;
  }

  // Group container
  const mainGroup = new THREE.Group();
  scene.add(mainGroup);

  // 1. Central Core: Glowing Cybernetic Icosahedron (Quantum Intelligence Core)
  const coreGeo = new THREE.IcosahedronGeometry(1.0, 1);
  const coreMat = new THREE.MeshPhongMaterial({
    color: 0x00f090,
    emissive: 0x004422,
    wireframe: true,
    transparent: true,
    opacity: 0.85
  });
  const coreMesh = new THREE.Mesh(coreGeo, coreMat);
  mainGroup.add(coreMesh);

  // Inner Solid Plasma Sphere
  const innerGeo = new THREE.SphereGeometry(0.55, 16, 16);
  const innerMat = new THREE.MeshBasicMaterial({
    color: 0x00d4ff,
    wireframe: false,
    transparent: true,
    opacity: 0.6
  });
  const innerMesh = new THREE.Mesh(innerGeo, innerMat);
  mainGroup.add(innerMesh);

  // 2. Dual Orbiting Holographic Rings (Cyan & Gold)
  const ring1Geo = new THREE.TorusGeometry(1.65, 0.025, 16, 100);
  const ring1Mat = new THREE.MeshBasicMaterial({ color: 0x00d4ff, transparent: true, opacity: 0.75 });
  const ring1 = new THREE.Mesh(ring1Geo, ring1Mat);
  ring1.rotation.x = Math.PI / 3;
  mainGroup.add(ring1);

  const ring2Geo = new THREE.TorusGeometry(1.9, 0.02, 16, 100);
  const ring2Mat = new THREE.MeshBasicMaterial({ color: 0xf59e0b, transparent: true, opacity: 0.65 });
  const ring2 = new THREE.Mesh(ring2Geo, ring2Mat);
  ring2.rotation.y = Math.PI / 4;
  ring2.rotation.x = -Math.PI / 5;
  mainGroup.add(ring2);

  // 3. Floating Neural Particle Cloud
  const particleCount = 120;
  const particleGeo = new THREE.BufferGeometry();
  const particlePositions = new Float32Array(particleCount * 3);
  for (let i = 0; i < particleCount * 3; i += 3) {
    const r = 2.0 + Math.random() * 1.2;
    const theta = Math.random() * Math.PI * 2;
    const phi = (Math.random() - 0.5) * Math.PI;
    particlePositions[i] = r * Math.cos(phi) * Math.cos(theta);
    particlePositions[i + 1] = r * Math.sin(phi);
    particlePositions[i + 2] = r * Math.cos(phi) * Math.sin(theta);
  }
  particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
  const particleMat = new THREE.PointsMaterial({
    color: 0x00f090,
    size: 0.05,
    transparent: true,
    opacity: 0.7
  });
  const particleSystem = new THREE.Points(particleGeo, particleMat);
  mainGroup.add(particleSystem);

  // Lighting
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
  scene.add(ambientLight);

  const dirLight1 = new THREE.DirectionalLight(0x00f090, 1.5);
  dirLight1.position.set(3, 4, 3);
  scene.add(dirLight1);

  const dirLight2 = new THREE.DirectionalLight(0x00d4ff, 1.2);
  dirLight2.position.set(-3, -2, -2);
  scene.add(dirLight2);

  // Animation Loop
  let frame = 0;
  function animate() {
    requestAnimationFrame(animate);
    frame += 0.015;

    // Core pulsing & rotation
    coreMesh.rotation.x += 0.008;
    coreMesh.rotation.y += 0.012;
    const s = 1.0 + 0.06 * Math.sin(frame * 2.5);
    innerMesh.scale.set(s, s, s);

    // Orbiting rings
    ring1.rotation.z += 0.015;
    ring1.rotation.y += 0.006;
    ring2.rotation.z -= 0.012;
    ring2.rotation.x += 0.008;

    // Particles rotation
    particleSystem.rotation.y += 0.003;
    particleSystem.rotation.x = Math.sin(frame * 0.5) * 0.1;

    // Smooth hover bobbing
    mainGroup.position.y = Math.sin(frame) * 0.12;

    renderer.render(scene, camera);
  }
  animate();

  // Resize handler
  window.addEventListener("resize", () => {
    if (!canvas || !canvas.parentElement) return;
    const newW = canvas.clientWidth || 460;
    const newH = canvas.clientHeight || 320;
    camera.aspect = newW / newH;
    camera.updateProjectionMatrix();
    renderer.setSize(newW, newH);
  });
}

function drawHeroFallbackAvatar() {
  const canvas = document.getElementById("agent3d-hero-character");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  const w = canvas.width;
  const h = canvas.height;
  ctx.clearRect(0, 0, w, h);
  ctx.save();
  ctx.beginPath();
  ctx.arc(w / 2, h / 2, 70, 0, Math.PI * 2);
  ctx.fillStyle = "rgba(0, 240, 144, 0.1)";
  ctx.fill();
  ctx.lineWidth = 3;
  ctx.strokeStyle = "#00f090";
  ctx.shadowColor = "#00f090";
  ctx.shadowBlur = 18;
  ctx.stroke();

  ctx.font = "bold 16px monospace";
  ctx.fillStyle = "#00d4ff";
  ctx.textAlign = "center";
  ctx.fillText("AI QUANT SENTINEL", w / 2, h / 2 - 8);
  ctx.font = "12px monospace";
  ctx.fillStyle = "#00f090";
  ctx.fillText("ACTIVE 24/7", w / 2, h / 2 + 14);
  ctx.restore();
}

window.initHero3DCharacter = initHero3DCharacter;
window.drawHeroFallbackAvatar = drawHeroFallbackAvatar;

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => setTimeout(initHero3DCharacter, 300));
} else {
  setTimeout(initHero3DCharacter, 300);
}
