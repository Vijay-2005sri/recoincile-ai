import * as THREE from "./vendor/three.module.min.js";

const root = document.documentElement;
const sceneRoot = document.getElementById("scene-root");
const view = document.getElementById("scene-view");
const loading = document.getElementById("scene-loading");
const stateBadge = document.getElementById("scene-state");
const parentUrl = new URLSearchParams(window.location.search).get("streamlitUrl");
const targetOrigin = parentUrl ? new URL(parentUrl).origin : "*";

let cleanupScene = () => {};
let mountGeneration = 0;
let lastReportedHeight = 0;

function post(type, payload = {}) {
  window.parent.postMessage({ isStreamlitMessage: true, type, ...payload }, targetOrigin);
}

function reportHeight() {
  const height = Math.ceil(sceneRoot.getBoundingClientRect().height);
  if (height > 0 && height !== lastReportedHeight) {
    lastReportedHeight = height;
    post("streamlit:setFrameHeight", { height });
  }
}

function applyTheme(theme) {
  Object.entries(theme || {}).forEach(([token, value]) => root.style.setProperty(`--${token}`, value));
}

function colour(token) {
  return getComputedStyle(root).getPropertyValue(`--${token}`).trim();
}

function addLabel(labels, position, radius, title, subtitle, tone) {
  const label = document.createElement("div");
  const titleElement = document.createElement("strong");
  const subtitleElement = document.createElement("span");
  label.className = "scene-label";
  label.dataset.tone = tone;
  titleElement.textContent = title;
  subtitleElement.textContent = subtitle;
  label.append(titleElement, subtitleElement);
  view.appendChild(label);
  labels.push({ label, position: position.clone(), offset: new THREE.Vector3(0, radius + .52, 0) });
}

function disposeObject(object) {
  object.traverse((child) => {
    if (child.geometry) child.geometry.dispose();
    if (child.material) {
      const materials = Array.isArray(child.material) ? child.material : [child.material];
      materials.forEach((material) => material.dispose());
    }
  });
}

function mountScene(payload, generation) {
  if (generation !== mountGeneration) return;

  try {
    const count = (name) => Number(payload.counts?.[name] || 0);
    const colors = {
      canvas: colour("scene-canvas"),
      grid: colour("scene-grid"),
      source: colour("accent-info"),
      success: colour("scene-node-success"),
      warning: colour("scene-node-warning"),
      critical: colour("scene-node-critical"),
      review: colour("scene-node-review"),
      particle: colour("scene-particle"),
    };
    // Streamlit mounts the component in an iframe. Waiting for #scene-view to
    // have dimensions prevents a zero-size WebGL drawing buffer on first paint.
    const canvas = document.createElement("canvas");
    const contextAttributes = { alpha: false, antialias: true, powerPreference: "high-performance" };
    const context = canvas.getContext("webgl2", contextAttributes) || canvas.getContext("webgl", contextAttributes);
    if (!context) throw new Error("WebGL is unavailable for the reconciliation scene.");
    const renderer = new THREE.WebGLRenderer({ canvas, context, antialias: true, alpha: false, powerPreference: "high-performance" });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setClearColor(colors.canvas, 1);
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    view.insertBefore(renderer.domElement, loading);

    const scene = new THREE.Scene();
    scene.fog = new THREE.Fog(colors.canvas, 13, 28);
    const camera = new THREE.PerspectiveCamera(39, 1, .1, 100);
    camera.position.set(0, 4.7, 15.5);
    const world = new THREE.Group();
    scene.add(world);
    scene.add(new THREE.HemisphereLight(colour("scene-light-top"), colour("scene-light-bottom"), 1.5));

    const keyLight = new THREE.PointLight(colors.source, 26, 19, 2);
    keyLight.position.set(-2, 4, 7);
    scene.add(keyLight);
    const successLight = new THREE.PointLight(colors.success, 18, 15, 2);
    successLight.position.set(5, 1, 5);
    scene.add(successLight);
    const criticalLight = new THREE.PointLight(colors.critical, 13, 13, 2);
    criticalLight.position.set(5, -3, 3);
    scene.add(criticalLight);

    const grid = new THREE.GridHelper(18, 18, colors.grid, colors.grid);
    grid.position.y = -4.1;
    grid.material.transparent = true;
    grid.material.opacity = .36;
    world.add(grid);

    const volume = Math.max(count("orders"), count("payments"), count("settlements"), 1);
    const tubeRadius = (value) => .045 + (.13 * Math.sqrt(Math.max(value, 1) / volume));
    const labels = [];
    const nodes = [];
    const flows = [];

    function addNode(id, title, subtitle, position, tone, radius, labelTone) {
      const group = new THREE.Group();
      group.position.copy(position);
      const geometry = id === "verify" ? new THREE.SphereGeometry(radius, 32, 24) : new THREE.IcosahedronGeometry(radius, 2);
      const material = new THREE.MeshStandardMaterial({ color: tone, emissive: tone, emissiveIntensity: id === "verify" ? .46 : .16, metalness: .48, roughness: .28 });
      const mesh = new THREE.Mesh(geometry, material);
      const halo = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.52, 24, 16), new THREE.MeshBasicMaterial({ color: tone, transparent: true, opacity: .075, depthWrite: false }));
      const ring = new THREE.Mesh(new THREE.TorusGeometry(radius * 1.27, .018, 8, 48), new THREE.MeshBasicMaterial({ color: tone, transparent: true, opacity: .72 }));
      ring.rotation.x = Math.PI / 2.35;
      group.add(mesh, halo, ring);
      world.add(group);
      addLabel(labels, position, radius, title, subtitle, labelTone);
      nodes.push({ id, ring, mesh });
      return position;
    }

    const positions = {
      orders: addNode("orders", "Orders", `${count("orders").toLocaleString()} loaded`, new THREE.Vector3(-5.0, 2.45, .65), colors.source, .62, "info"),
      payments: addNode("payments", "Payments", `${count("payments").toLocaleString()} linked`, new THREE.Vector3(-5.15, -.15, -1.1), colors.review, .58, "review"),
      settlements: addNode("settlements", "Settlements", `${count("settlements").toLocaleString()} linked`, new THREE.Vector3(-4.8, -2.65, .35), colors.warning, .58, "warning"),
      verify: addNode("verify", "Verify core", `${count("orders").toLocaleString()} rules`, new THREE.Vector3(0, 0, 0), colors.source, 1.12, "info"),
      verified: addNode("verified", "Verified", `${count("verified").toLocaleString()} reconciled`, new THREE.Vector3(5.15, 1.55, .15), colors.success, .68, "success"),
      exceptions: addNode("exceptions", "Exceptions", `${count("exceptions").toLocaleString()} queued`, new THREE.Vector3(5.1, -2.05, .75), colors.critical, .64, "critical"),
    };

    function addFlow(from, to, tone, value, curveLift) {
      const midpoint = from.clone().lerp(to, .5);
      const bend = new THREE.Vector3(0, curveLift, (from.z - to.z) * .36 + .62);
      const curve = new THREE.CatmullRomCurve3([from, from.clone().lerp(midpoint, .43).add(bend), to.clone().lerp(midpoint, .43).add(bend), to]);
      const radius = tubeRadius(value);
      const tube = new THREE.Mesh(new THREE.TubeGeometry(curve, 80, radius, 10, false), new THREE.MeshStandardMaterial({ color: tone, emissive: tone, emissiveIntensity: .35, metalness: .32, roughness: .3, transparent: true, opacity: .82 }));
      const tangent = curve.getTangentAt(.72).normalize();
      const arrow = new THREE.Mesh(new THREE.ConeGeometry(radius * 3.5, radius * 9, 14), new THREE.MeshStandardMaterial({ color: tone, emissive: tone, emissiveIntensity: .24, metalness: .3, roughness: .3 }));
      arrow.position.copy(curve.getPointAt(.72));
      arrow.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), tangent);
      world.add(tube, arrow);
      const particles = Array.from({ length: Math.max(2, Math.min(6, Math.ceil(value / volume * 5))) }, (_, index) => {
        const mesh = new THREE.Mesh(new THREE.SphereGeometry(radius * 1.6, 12, 10), new THREE.MeshBasicMaterial({ color: colors.particle }));
        world.add(mesh);
        return { mesh, progress: index / 5, speed: .075 + index * .012 };
      });
      flows.push({ curve, particles });
    }

    addFlow(positions.orders, positions.verify, colors.source, count("orders"), .76);
    addFlow(positions.payments, positions.verify, colors.review, count("payments"), .16);
    addFlow(positions.settlements, positions.verify, colors.warning, count("settlements"), -.58);
    addFlow(positions.verify, positions.verified, colors.success, count("verified"), .52);
    addFlow(positions.verify, positions.exceptions, colors.critical, count("exceptions"), -.38);

    function resize() {
      const width = view.clientWidth || 1;
      const height = view.clientHeight || 1;
      camera.aspect = width / height;
      camera.updateProjectionMatrix();
      renderer.setSize(width, height, false);
    }
    function projectLabels() {
      labels.forEach(({ label, position, offset }) => {
        const projected = position.clone().add(offset).project(camera);
        label.style.transform = `translate(${(projected.x * .5 + .5) * view.clientWidth}px, ${(-projected.y * .5 + .5) * view.clientHeight}px) translate(-50%, -50%)`;
        label.style.opacity = projected.z < 1 ? "1" : "0";
      });
    }

    let frame;
    const started = performance.now();
    function render(now) {
      const elapsed = (now - started) / 1000;
      if (payload.motionEnabled) {
        world.rotation.y = Math.sin(elapsed * .22) * .12;
        world.rotation.x = Math.cos(elapsed * .18) * .025;
        camera.position.x = Math.sin(elapsed * .17) * .92;
        camera.position.y = 4.6 + Math.cos(elapsed * .14) * .25;
        nodes.forEach(({ id, ring, mesh }, index) => {
          ring.rotation.z = elapsed * (.25 + index * .018);
          if (id === "verify") mesh.rotation.y = elapsed * .32;
        });
        flows.forEach(({ curve, particles }) => particles.forEach((particle) => {
          particle.progress = (particle.progress + particle.speed / 60) % 1;
          particle.mesh.position.copy(curve.getPointAt(particle.progress));
        }));
      } else {
        flows.forEach(({ curve, particles }) => particles.forEach((particle) => particle.mesh.position.copy(curve.getPointAt(particle.progress))));
      }
      camera.lookAt(0, -.08, 0);
      projectLabels();
      renderer.render(scene, camera);
      if (payload.motionEnabled) frame = requestAnimationFrame(render);
    }

    const observer = new ResizeObserver(() => {
      if (generation !== mountGeneration) return;
      resize();
      reportHeight();
    });
    observer.observe(view);
    resize();
    loading.hidden = true;
    render(performance.now());
    view.dataset.sceneState = "ready";
    reportHeight();
    cleanupScene = () => {
      if (frame) cancelAnimationFrame(frame);
      observer.disconnect();
      labels.forEach(({ label }) => label.remove());
      disposeObject(scene);
      renderer.dispose();
      renderer.domElement.remove();
    };
  } catch (error) {
    // Keep diagnostics in the browser console. Do not replace a real 3D scene
    // with a generic error panel when a supported browser is still mounting.
    console.error("Reconciliation scene initialization failed", error);
    loading.hidden = true;
    view.dataset.sceneState = "failed";
  }
}

function scheduleSceneMount(payload) {
  const generation = ++mountGeneration;
  cleanupScene();
  cleanupScene = () => {};
  applyTheme(payload.theme);
  stateBadge.textContent = payload.processing ? "PROCESSING" : "LIVE DATA FLOW";
  loading.hidden = false;
  view.dataset.sceneState = "mounting";

  let attempts = 0;
  const waitForViewport = () => {
    if (generation !== mountGeneration) return;
    if (view.clientWidth >= 32 && view.clientHeight >= 80) {
      mountScene(payload, generation);
      return;
    }
    attempts += 1;
    if (attempts < 90) {
      requestAnimationFrame(waitForViewport);
      return;
    }
    // Diagnostic only: the next Streamlit layout render retries mounting.
    console.error("Reconciliation scene viewport did not receive usable dimensions.");
    loading.hidden = true;
    view.dataset.sceneState = "waiting-for-layout";
  };
  requestAnimationFrame(waitForViewport);
}

window.addEventListener("message", (event) => {
  if (event.data?.type === "streamlit:render") scheduleSceneMount(event.data.args?.scene || {});
});

new ResizeObserver(reportHeight).observe(sceneRoot);
post("streamlit:componentReady", { apiVersion: 1 });
reportHeight();
