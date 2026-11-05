/**
 * 3D Holographic WebGL Universe Engine
 * Creates an interactive 3D Cybernetic Grid, Floating Cryptographic 3D Rings,
 * Interactive Neon Raycasting Particles, and Holographic Agent Nodes.
 */

(function init3DQuantumWebsite() {
  if (typeof THREE === 'undefined') {
    console.debug('Three.js loading...');
    setTimeout(init3DQuantumWebsite, 200);
    return;
  }

  // Create or attach dedicated 3D canvas container behind the UI
  let container = document.getElementById('webgl-3d-universe-container');
  if (!container) {
    container = document.createElement('div');
    container.id = 'webgl-3d-universe-container';
    container.style.position = 'fixed';
    container.style.top = '0';
    container.style.left = '0';
    container.style.width = '100vw';
    container.style.height = '100vh';
    container.style.zIndex = '0'; // Behind interactive UI cards
    container.style.pointerEvents = 'none'; // Lets clicks pass through to UI
    container.style.overflow = 'hidden';
    document.body.prepend(container);
  }

  // Hide 2D legacy canvas if present to boost WebGL 60FPS performance
  const c1 = document.getElementById('circuitBgCanvas');
  const c2 = document.getElementById('neuralBgCanvas');
  if (c1) c1.style.display = 'none';
  if (c2) c2.style.display = 'none';

  // 1. Scene, Camera, Renderer
  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x020813, 0.0018);

  const camera = new THREE.PerspectiveCamera(60, window.innerWidth / window.innerHeight, 1, 3000);
  camera.position.set(0, 80, 450);

  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  container.innerHTML = '';
  container.appendChild(renderer.domElement);

  // 2. Lighting
  const ambientLight = new THREE.AmbientLight(0x00d4ff, 0.6);
  scene.add(ambientLight);

  const neonGreenLight = new THREE.PointLight(0x00f090, 2.5, 900);
  neonGreenLight.position.set(-250, 200, 200);
  scene.add(neonGreenLight);

  const neonPurpleLight = new THREE.PointLight(0xa855f7, 2.5, 900);
  neonPurpleLight.position.set(250, -100, 150);
  scene.add(neonPurpleLight);

  // 3. 3D Cybernetic Tron Wave Grid
  const gridHelper = new THREE.GridHelper(1600, 60, 0x00d4ff, 0x072545);
  gridHelper.position.y = -180;
  gridHelper.material.opacity = 0.45;
  gridHelper.material.transparent = true;
  scene.add(gridHelper);

  // 4. Floating 3D Golden/Cyan SuperBrain Torus Rings (Quantum Core)
  const coreGroup = new THREE.Group();
  scene.add(coreGroup);

  const ringGeo1 = new THREE.TorusGeometry(120, 2.2, 16, 100);
  const ringMat1 = new THREE.MeshBasicMaterial({ color: 0x00d4ff, wireframe: true, transparent: true, opacity: 0.6 });
  const ring1 = new THREE.Mesh(ringGeo1, ringMat1);
  coreGroup.add(ring1);

  const ringGeo2 = new THREE.TorusGeometry(90, 1.8, 16, 100);
  const ringMat2 = new THREE.MeshBasicMaterial({ color: 0x00f090, wireframe: true, transparent: true, opacity: 0.5 });
  const ring2 = new THREE.Mesh(ringGeo2, ringMat2);
  ring2.rotation.x = Math.PI / 3;
  coreGroup.add(ring2);

  const ringGeo3 = new THREE.TorusGeometry(60, 1.5, 16, 80);
  const ringMat3 = new THREE.MeshBasicMaterial({ color: 0xf59e0b, wireframe: true, transparent: true, opacity: 0.5 });
  const ring3 = new THREE.Mesh(ringGeo3, ringMat3);
  ring3.rotation.y = Math.PI / 4;
  coreGroup.add(ring3);

  // 5. 3D Neural Particle Field (1,500 Dynamic Depth Stars)
  const particleCount = 1500;
  const particleGeo = new THREE.BufferGeometry();
  const particleCoords = new Float32Array(particleCount * 3);
  const particleColors = new Float32Array(particleCount * 3);

  const cCyan = new THREE.Color(0x00d4ff);
  const cGreen = new THREE.Color(0x00f090);
  const cGold = new THREE.Color(0xf59e0b);

  for (let i = 0; i < particleCount * 3; i += 3) {
    particleCoords[i] = (Math.random() - 0.5) * 1800;
    particleCoords[i + 1] = (Math.random() - 0.5) * 1200;
    particleCoords[i + 2] = (Math.random() - 0.5) * 1600;

    const rCol = Math.random();
    const chosenColor = rCol > 0.6 ? cCyan : (rCol > 0.3 ? cGreen : cGold);
    particleColors[i] = chosenColor.r;
    particleColors[i + 1] = chosenColor.g;
    particleColors[i + 2] = chosenColor.b;
  }

  particleGeo.setAttribute('position', new THREE.BufferAttribute(particleCoords, 3));
  particleGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

  const particleMat = new THREE.PointsMaterial({
    size: 3.5,
    vertexColors: true,
    transparent: true,
    opacity: 0.75,
    blending: THREE.AdditiveBlending
  });

  const particleCloud = new THREE.Points(particleGeo, particleMat);
  scene.add(particleCloud);

  // 6. Interactive Mouse & Scroll 3D Parallax Tracking
  let mouseX = 0, mouseY = 0;
  let targetCameraX = 0, targetCameraY = 80;

  window.addEventListener('mousemove', (e) => {
    mouseX = (e.clientX - window.innerWidth / 2) * 0.2;
    mouseY = (e.clientY - window.innerHeight / 2) * 0.15;
  }, { passive: true });

  window.addEventListener('scroll', () => {
    const scrollY = window.scrollY || window.pageYOffset;
    targetCameraY = 80 - (scrollY * 0.15);
    coreGroup.position.y = - (scrollY * 0.08);
  }, { passive: true });

  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });

  // 7. Animation Render Loop (60 FPS)
  let clock = new THREE.Clock();

  function animate3D() {
    requestAnimationFrame(animate3D);
    const elapsedTime = clock.getElapsedTime();

    // Smooth camera inertia
    camera.position.x += (mouseX - camera.position.x) * 0.04;
    camera.position.y += (targetCameraY - mouseY - camera.position.y) * 0.04;
    camera.lookAt(0, 0, 0);

    // Orbit rings rotation
    ring1.rotation.x = elapsedTime * 0.25;
    ring1.rotation.y = elapsedTime * 0.18;

    ring2.rotation.y = elapsedTime * 0.35;
    ring2.rotation.z = elapsedTime * 0.22;

    ring3.rotation.x = -elapsedTime * 0.40;
    ring3.rotation.z = elapsedTime * 0.30;

    // Pulse core
    const scale = 1.0 + Math.sin(elapsedTime * 2.5) * 0.06;
    coreGroup.scale.set(scale, scale, scale);

    // Float Tron Grid forward
    gridHelper.position.z = (elapsedTime * 45) % 50;

    // Slowly rotate particle field
    particleCloud.rotation.y = elapsedTime * 0.03;

    renderer.render(scene, camera);
  }

  animate3D();
  console.log('⚡ 3D Holographic WebGL Universe Engine Initialized Successfully!');
})();
