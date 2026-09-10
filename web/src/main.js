import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { ReferenceDemo } from "./demo.js";
import { NeuralActivity } from "./neural-activity.js";
import "./style.css";

const app = document.querySelector("#app");
app.innerHTML = `
<header class="topbar">
  <div class="experiment-title"><h1>GangnamFly</h1><span>MaleCNS v1.0 / Flybody / MuJoCo</span></div>
  <div class="status"><i id="statusDot"></i><span id="statusText">conectando</span><span class="live" id="liveLabel">LOCAL</span></div>
</header>
<main id="main">
  <nav class="view-switch" aria-label="Secciones">
    <button id="experimentView" class="active" aria-pressed="true">Experimento</button>
    <button id="demoView" aria-pressed="false">DEMO</button>
  </nav>
  <section id="liveControls" class="control-strip" aria-label="Controles de simulación">
    <div class="mode-tabs">
      <button data-action="observe" class="active">Observar</button>
      <button data-action="train">Entrenar</button>
      <button data-action="replay">Replay</button>
    </div>
    <button class="pause" data-action="pause" aria-label="Pausar simulación"><span id="pauseIcon">Ⅱ</span> <span id="pauseText">Pausar</span></button>
    <button class="stop" data-action="stop">Detener</button>
    <span class="keyhint">Espacio: pausar</span>
  </section>
  <section id="demoControls" class="control-strip demo-controls" aria-label="Controles de demo" hidden>
    <button id="demoPause" disabled>Pausar demo</button>
    <button id="demoRestart" disabled>Reiniciar</button>
    <label>Velocidad <select id="demoSpeed" disabled><option value="0.25">0.25×</option><option value="0.5">0.5×</option><option value="1" selected>1×</option><option value="2">2×</option></select></label>
    <label class="demo-timeline">Posición <input id="demoSeek" type="range" min="0" max="1" step="0.01" value="0" disabled></label>
    <output id="demoClock" aria-live="off">0.00 / 0.00 s</output>
  </section>
  <div class="workspace">
    <section id="viewportPanel" class="scene-wrap" aria-label="Simulación física">
      <div id="scene" aria-label="Visualización 3D de Flybody" role="img"></div>
      <div id="liveProofOverlay" class="proof-overlay" hidden></div>
      <div class="scene-label"><span>Flybody · unidades en cm</span><span id="simClock">t = 0.00 s</span></div>
      <div class="view-tools">
        <button id="resetView">Restablecer cámara</button><button id="toggleMotion">Pausar imagen</button><span id="renderFps">— FPS</span>
      </div>
      <div id="modelMessage" role="status">Cargando geometría…</div>
      <p id="runMessage" role="status" aria-live="polite">Cargando el experimento…</p>
      <p id="commandError" role="alert"></p>
    </section>
    <aside id="liveTelemetry" class="telemetry" aria-label="Telemetría">
      <section class="panel metrics">
        <div class="panel-head"><h2>Estado</h2><span class="pill" id="modePill">OBSERVAR</span></div>
        <div class="metric-grid">
          <div><small>Velocidad</small><strong id="speed">—</strong><span>cm/s</span></div>
          <div><small>Recompensa instantánea</small><strong id="reward">—</strong></div><div><small>Media del intento</small><strong id="rewardMean">—</strong></div>
          <div><small>Error articular</small><strong id="tracking">—</strong><span>rad²</span></div>
          <div><small>Tiempo real</small><strong id="rtf">—</strong><span>×</span></div>
        </div>
        <p class="weight-stat">Conexiones modificadas: <b id="changedEdges">0</b></p>
        <div class="timings">
          <div><span>Simulación</span><b id="simTime">—</b></div>
          <div><span>Cerebro</span><b id="brainHz">—</b></div>
          <div><span>Física</span><b id="physicsHz">—</b></div>
        </div>
      </section>
      <section class="panel brain">
        <div class="panel-head"><h2>Actividad descendente</h2></div>
        <div id="neurons" class="neuron-list"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div>
        <details><summary>Actividad neuronal motora (VNC)</summary><p>VNC: cordón nervioso ventral. Hz = disparos por segundo simulado, promediados y suavizados por grupo; no es fuerza ni frecuencia de movimiento.</p><p>T1: patas delanteras · T2: medias · T3: traseras. L: izquierda · R: derecha.</p><div id="vncrates"></div></details>
      </section>
    </aside>
    <aside id="demoInfo" class="panel demo-info" aria-label="Referencia de movimiento" hidden>
      <div class="panel-head"><h2>Referencia programada</h2><span class="pill">DEMO</span></div>
      <p id="demoDescription">Captura continua de Xsens · Gangnam Style, adaptada al cuerpo anatómico de Flybody.</p>
      <p><span id="demoPhase">Incorporación</span> · 2,5 s de incorporación, 31,07 s de captura y 2,5 s de cierre.</p>
      <p>Animación cinemática: no evalúa equilibrio ni fuerzas. Es la toma completa de 31 segundos, no la canción completa.</p>
      <p>MaleCNS no controla esta animación. Ver el movimiento aquí no demuestra que la mosca lo haya aprendido.</p>
      <p>El evaluador del entrenamiento compara la física con esta misma referencia; no impone estas poses al cuerpo.</p>
      <p id="demoMessage" role="status">Cargando referencia…</p>
      <p class="demo-background">El experimento conserva su estado; si estaba corriendo, continúa en segundo plano.</p>
    </aside>
  </div>
  <section id="neuralActivity" class="panel neural-activity" aria-label="Actividad neuronal en vivo"></section>
  <section id="trainingProof" class="panel training-proof" aria-label="Evidencia de entrenamiento">
    <div class="panel-head"><h2>Aprendizaje medido</h2><span class="pill" id="trainingPhase">SIN SESIÓN</span></div>
    <p id="trainingStage"></p><p id="trainingNext"></p><p id="trainingPhysical"></p><details id="trainingAllStages"><summary>Ver todas las microetapas</summary><ol id="trainingStages" aria-label="Etapas del aprendizaje"></ol></details>
    <div class="proof-grid"><div>Intentos <b id="trainingAttempts">—</b></div><div>Tiempo acumulado <b id="trainingSeconds">—</b></div><div>Baseline <b id="trainingBaseline">—</b></div><div>Mejor evaluación <b id="trainingBest">—</b></div></div>
    <p id="trainingNotice">La evidencia aparece cuando el servidor registra una sesión real.</p><svg id="trainingChart" class="training-chart" viewBox="0 0 300 54" role="img" aria-label="Historial medido de evaluaciones"></svg>
    <p id="trainingQuality">El cambio de pesos no demuestra que aprendió a bailar.</p><p id="trainingLatest"></p>
    <details open><summary>Proveniencia y cambios reales</summary><p id="trainingEvidence">Pendiente de verificación.</p><p id="trainingHashes">Hashes: —</p><p id="trainingWeights">Cambios: —</p><a id="evidenceDownload" hidden>Descargar evidencia</a><code id="reproductionCommand" hidden></code></details>
  </section>
  <section id="savedEpisodes" class="panel episodes">
    <div class="panel-head"><h2>Episodios guardados</h2><span id="episodeCount">0 registrados</span></div>
    <div id="episodeList" class="episode-list"><p class="empty">Aún no hay episodios registrados.</p></div>
  </section>
  <details id="modelNotes" class="model-notes">
    <summary>Modelo y límites</summary>
    <p>166.700 neuronas y 25.582.938 conexiones de MaleCNS v1.0. Dinámica LIF simplificada; cuerpo Flybody en MuJoCo. Correspondencia sensorial y motora provisional.</p>
    <p>MaleCNS controla 30 actuadores. Los restantes mantienen comandos estáticos. El entrenamiento modifica conexiones existentes; la referencia proviene de una captura de Xsens adaptada a 30 articulaciones. Aprendizaje de la coreografía aún no validado.</p>
  </details>
</main>
<footer><span id="connection">API local · esperando datos</span></footer>`;

const $ = (id) => document.getElementById(id);
const neuralActivity = new NeuralActivity($("neuralActivity"));
const sceneEl = $("scene");
let lastState = null,
  modelLoaded = false,
  commandBusy = false;
let motion = !matchMedia("(prefers-reduced-motion: reduce)").matches;
let renderer, camera, controls, world;
let experimentCamera = null;
const objects = new Map();
const quaternionA = new THREE.Quaternion();
const quaternionB = new THREE.Quaternion();
const nextPosition = new THREE.Vector3();
const demo = new ReferenceDemo(
  (a, b, fraction) => {
    a.geoms.forEach((geom, i) => {
      const object = objects.get(geom.id);
      if (!object) return;
      const next = b.geoms[i];
      object.position
        .set(...geom.pos)
        .lerp(nextPosition.set(...next.pos), fraction);
      quaternionA.set(geom.quat[1], geom.quat[2], geom.quat[3], geom.quat[0]);
      quaternionB.set(next.quat[1], next.quat[2], next.quat[3], next.quat[0]);
      object.quaternion.copy(quaternionA).slerp(quaternionB, fraction);
    });
  },
  (active) => {
    neuralActivity.reset();
    for (const id of [
      "liveControls",
      "liveTelemetry",
      "neuralActivity",
      "savedEpisodes",
      "trainingProof",
      "liveProofOverlay",
      "modelNotes",
      "toggleMotion",
      "runMessage",
      "commandError",
    ])
      $(id).hidden = active;
    $("demoControls").hidden = $("demoInfo").hidden = !active;
    for (const [id, selected] of [
      ["demoView", active],
      ["experimentView", !active],
    ]) {
      $(id).classList.toggle("active", selected);
      $(id).setAttribute("aria-pressed", String(selected));
    }
    $("viewportPanel").setAttribute(
      "aria-label",
      active ? "Demo cinemática" : "Simulación física",
    );
    if (active) {
      if (camera && controls && !experimentCamera)
        experimentCamera = {
          position: camera.position.clone(),
          target: controls.target.clone(),
        };
      if (camera && controls) {
        camera.position.set(0.95, -0.2, 0.22);
        controls.target.set(0.06, 0.02, 0.045);
        controls.update();
      }
      text("liveLabel", "DEMO");
      text("simClock", `DEMO · ${demo.time.toFixed(2)} s`);
    } else if (lastState) {
      if (experimentCamera) {
        camera.position.copy(experimentCamera.position);
        controls.target.copy(experimentCamera.target);
        controls.update();
        experimentCamera = null;
      }
      applyState(lastState);
      applyTransforms(lastState);
    }
  },
);
$("demoView").addEventListener("click", () => demo.activate());
$("experimentView").addEventListener("click", () => demo.deactivate());

function text(id, value) {
  $(id).textContent = value;
}
function number(value, digits = 2) {
  return Number.isFinite(value) ? value.toFixed(digits) : "—";
}
function updateMotion() {
  text("toggleMotion", motion ? "Pausar imagen" : "Activar imagen");
  $("toggleMotion").setAttribute("aria-pressed", String(!motion));
}
updateMotion();
try {
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
  renderer.setSize(sceneEl.clientWidth, sceneEl.clientHeight);
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute(
    "aria-label",
    "Mosca anatómica en MuJoCo. Arrastrá para rotar y usá la rueda para acercar.",
  );
  sceneEl.appendChild(renderer.domElement);
  camera = new THREE.PerspectiveCamera(
    36,
    sceneEl.clientWidth / sceneEl.clientHeight,
    0.001,
    100,
  );
  camera.up.set(0, 0, 1);
  world = new THREE.Scene();
  world.background = new THREE.Color("#171c1c");
  world.add(new THREE.HemisphereLight("#dcefe7", "#25211d", 2.4));
  const key = new THREE.DirectionalLight("#fff0d0", 3);
  key.position.set(1, 2, 2);
  world.add(key);
  const fill = new THREE.DirectionalLight("#b9d8ee", 2);
  fill.position.set(-1, -2, 1);
  world.add(fill);
  const grid = new THREE.GridHelper(3, 30, "#42504b", "#293330");
  grid.rotation.x = Math.PI / 2;
  grid.position.z = -0.132;
  world.add(grid);
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = false;
  controls.minDistance = 0.12;
  controls.maxDistance = 5;
  function resetView() {
    if (demo.active) {
      camera.position.set(0.95, -0.2, 0.22);
      controls.target.set(0.06, 0.02, 0.045);
    } else {
      camera.position.set(0.65, -0.65, 0.4);
      controls.target.set(0, 0, 0);
    }
    controls.update();
  }
  resetView();
  $("resetView").addEventListener("click", resetView);
  // Keyboard alternatives for orbit and zoom.
  renderer.domElement.tabIndex = 0;
  renderer.domElement.addEventListener("keydown", (event) => {
    if (
      !["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown", "+", "-"].includes(
        event.key,
      )
    )
      return;
    event.preventDefault();
    const offset = camera.position.clone().sub(controls.target);
    if (event.key === "ArrowLeft" || event.key === "ArrowRight")
      offset.applyAxisAngle(
        new THREE.Vector3(0, 0, 1),
        event.key === "ArrowLeft" ? 0.12 : -0.12,
      );
    else if (event.key === "ArrowUp" || event.key === "ArrowDown")
      offset.z += event.key === "ArrowUp" ? 0.05 : -0.05;
    else offset.multiplyScalar(event.key === "+" ? 0.9 : 1.1);
    camera.position.copy(controls.target).add(offset);
    controls.update();
  });
  new ResizeObserver(() => {
    renderer.setSize(sceneEl.clientWidth, sceneEl.clientHeight);
    camera.aspect = sceneEl.clientWidth / sceneEl.clientHeight;
    camera.updateProjectionMatrix();
  }).observe(sceneEl);
} catch (error) {
  text(
    "modelMessage",
    "No se pudo iniciar WebGL. Activá la aceleración gráfica del navegador.",
  );
  console.error(error);
}

function applyTransforms(state) {
  if (!state?.geoms) return;
  state.geoms.forEach((x) => {
    const object = objects.get(x.id);
    if (object) {
      object.position.set(...x.pos);
      object.quaternion.set(x.quat[1], x.quat[2], x.quat[3], x.quat[0]);
    }
  });
}
async function loadModel() {
  if (!renderer) return;
  try {
    const response = await fetch("/api/model", {
      signal: AbortSignal.timeout(45000),
    });
    if (!response.ok) throw Error("Modelo todavía no disponible");
    const model = await response.json();
    const geometry = new Map();
    for (const mesh of model.meshes) {
      const g = new THREE.BufferGeometry();
      g.setAttribute(
        "position",
        new THREE.Float32BufferAttribute(mesh.vertices, 3),
      );
      g.setIndex(mesh.faces);
      g.computeVertexNormals();
      geometry.set(mesh.id, g);
    }
    for (const geom of model.geoms) {
      const material = new THREE.MeshStandardMaterial({
        color: new THREE.Color(...geom.rgba.slice(0, 3)),
        opacity: geom.rgba[3],
        transparent: geom.rgba[3] < 1,
        side: THREE.DoubleSide,
        roughness: 0.7,
      });
      const mesh = new THREE.Mesh(geometry.get(geom.mesh), material);
      objects.set(geom.id, mesh);
      world.add(mesh);
    }
    modelLoaded = true;
    if (demo.active) demo.dirty = true;
    else applyTransforms(lastState);
    text(
      "modelMessage",
      "Geometría anatómica de Flybody · arrastrá para rotar",
    );
  } catch (error) {
    text("modelMessage", "Esperando geometría anatómica. Reintentando…");
    setTimeout(loadModel, 2500);
  }
}
loadModel();

function renderNeurons(rows, targetId = "neurons") {
  if (!rows.length) {
    $(targetId).textContent = "Esperando actividad neuronal…";
    return;
  }
  const fragment = document.createDocumentFragment();
  for (const row of rows) {
    const el = document.createElement("div");
    el.className = "neuron";
    const name = document.createElement("span");
    name.textContent = row.name;
    const bar = document.createElement("div");
    bar.className = "bar";
    bar.setAttribute("aria-hidden", "true");
    const fill = document.createElement("i");
    fill.style.width = `${Math.min(100, Math.max(0, row.rate || 0))}%`;
    bar.append(fill);
    const rate = document.createElement("b");
    rate.textContent = `${number(row.rate, 1)} Hz`;
    el.append(name, bar, rate);
    fragment.append(el);
  }
  $(targetId).replaceChildren(fragment);
}
let episodeSignature = "";
function renderEpisodes(rows) {
  text("episodeCount", `${rows.length} registrados`);
  const signature = JSON.stringify(rows);
  if (signature === episodeSignature) return;
  episodeSignature = signature;
  const fragment = document.createDocumentFragment();
  if (!rows.length) {
    const p = document.createElement("p");
    p.className = "empty";
    p.textContent =
      "Todavía no hay episodios. Iniciá una observación o un entrenamiento.";
    fragment.append(p);
  }
  for (const row of rows.slice(-6).reverse()) {
    const button = document.createElement("button");
    button.className = "episode";
    button.title = `Reproducir ${row.id}`;
    button.setAttribute("aria-label", `Reproducir episodio ${row.id}`);
    const name = document.createElement("span");
    name.textContent = `${row.mode === "train" ? "Entrenamiento" : "Observación"} · ${row.id.slice(-8)}`;
    const score = document.createElement("b");
    score.textContent = number(row.score);
    const duration = document.createElement("small");
    duration.textContent = `${number(row.seconds, 1)} s`;
    button.append(name, score, duration);
    button.addEventListener("click", () => command("replay", row.id));
    fragment.append(button);
  }
  $("episodeList").replaceChildren(fragment);
}
function updateButtons() {
  const unavailable =
    commandBusy ||
    !lastState ||
    ["loading", "error", "offline"].includes(lastState.status);
  document.querySelectorAll("[data-action]").forEach((button) => {
    const action = button.dataset.action;
    button.disabled =
      unavailable ||
      (action === "pause" &&
        !["running", "paused", "replay"].includes(lastState?.status)) ||
      (action === "stop" &&
        !["running", "paused", "replay"].includes(lastState?.status)) ||
      (action === "train" &&
        lastState?.training?.active &&
        lastState?.status !== "paused") ||
      (action === "replay" && !lastState?.episodes?.length);
    button.classList.toggle(
      "active",
      (action === "train" && lastState?.training?.active) ||
        (action !== "train" &&
          !lastState?.training?.active &&
          lastState?.mode ===
            { observe: "observe", train: "train", replay: "replay" }[action]),
    );
    if (button.closest(".mode-tabs"))
      button.setAttribute(
        "aria-pressed",
        String(button.classList.contains("active")),
      );
  });
}
function applyState(state) {
  lastState = state;
  if (demo.active) {
    text(
      "statusText",
      `experimento: ${state.status === "running" ? "en ejecución" : state.status === "paused" ? "pausado" : state.status === "idle" ? "listo" : state.status}`,
    );
    $("statusDot").className = ["error", "offline"].includes(state.status)
      ? "bad"
      : "";
    return;
  }
  neuralActivity.update(state);
  const statuses = {
    loading: "cargando",
    idle: "listo",
    running: "en ejecución",
    paused: "pausado",
    error: "error",
    replay: "replay",
    offline: "sin conexión",
  };
  text("statusText", statuses[state.status] || state.status);
  $("statusDot").className = ["error", "offline"].includes(state.status)
    ? "bad"
    : "";
  text(
    "liveLabel",
    state.status === "replay"
      ? "REPLAY"
      : state.status === "running"
        ? "LIVE"
        : "LOCAL",
  );
  text(
    "modePill",
    { train: "PLASTICIDAD", observe: "PESOS FIJOS", replay: "REPLAY" }[
      state.mode
    ] || "CARGANDO",
  );
  text("simClock", `t = ${number(state.sim_time)} s`);
  text("simTime", `${number(state.sim_time)} s`);
  text("brainHz", `${number(state.brain_hz, 1)} Hz`);
  text("physicsHz", `${number(state.physics_hz, 0)} Hz`);
  text("rtf", number(state.realtime_factor));
  text("reward", number(state.reward, 3));
  text(
    "rewardMean",
    Number.isFinite(state.reward_mean) ? number(state.reward_mean, 3) : "—",
  );
  text("tracking", number(state.tracking_error, 3));
  text("speed", number(state.speed));
  text(
    "changedEdges",
    Number.isFinite(state.changed_edges)
      ? state.changed_edges.toLocaleString("es-AR")
      : "—",
  );
  text("runMessage", state.message || "");
  const training = state.training || {};
  const stage = training.stage;
  text(
    "trainingStage",
    stage ? `Etapa ${stage.index + 1}/${stage.count} · ${stage.label}` : "",
  );
  text(
    "trainingNext",
    stage
      ? `Próximas: ${
          (training.stages || [])
            .slice(stage.index + 1, stage.index + 3)
            .map((s) => s.label)
            .join(" → ") || "ninguna"
        }`
      : "",
  );
  const metrics = state.objective_metrics;
  text(
    "trainingPhysical",
    stage?.protocol === "micro-v1" && metrics
      ? `Patas: ${number(100 * metrics.foot_load_fraction, 1)}% del peso · cuerpo: ${number(100 * metrics.other_load_fraction, 1)}% · Etapa: ${metrics.stage_ok ? "cumple este paso" : "pendiente"} · Erguida: ${metrics.standing_ok ? "sí" : "no"}. La aprobación requiere sostenerlo y pasar dos pruebas congeladas.`
      : "",
  );
  const stages = $("trainingStages");
  const stageText = JSON.stringify(training.stages || []);
  if (stages.dataset.state !== stageText) {
    stages.dataset.state = stageText;
    stages.replaceChildren(
      ...(training.stages || []).map((step) => {
        const item = document.createElement("li");
        item.textContent = `${step.label} · ${step.completed ? `comprobada · media ${number(step.score, 3)}` : step.active ? "actual" : "bloqueada"}`;
        if (step.active) item.setAttribute("aria-current", "step");
        return item;
      }),
    );
  }
  const stageHistory = (training.history || []).filter(
    (row) => !stage || row.stage_index === stage.index,
  );
  text(
    "trainingBaseline",
    Number.isFinite(training.baseline_score)
      ? number(training.baseline_score)
      : "pendiente",
  );
  text(
    "trainingQuality",
    stage
      ? `${stage.criterion_label} Dos evaluaciones con pesos congelados para avanzar.`
      : "Éxito: ≥90% de la secuencia completa dentro de 0,25 rad articular, 0,35 rad de orientación y 0,05 cm de posición; dos evaluaciones congeladas mejores que el baseline.",
  );
  if (
    training.trial_duration &&
    training.trial_duration < training.target_duration
  ) {
    text(
      "trainingQuality",
      `PRUEBA TÉCNICA CORTA: ${number(training.trial_duration, 2)} s por intento de ${number(training.target_duration, 2)} s de referencia. Comprueba aprendizaje ejecutado; no demuestra la coreografía ni puede alcanzar éxito.`,
    );
  }
  const latestTrial = stageHistory.at(-1);
  text(
    "trainingLatest",
    latestTrial
      ? `Último ${latestTrial.phase}: recompensa ${number(latestTrial.score, 3)}, ${stage?.protocol === "micro-v1" ? `criterio de etapa ${number(100 * (latestTrial.stage_fraction || 0), 1)}%, erguida ${number(100 * (latestTrial.standing_fraction || 0), 1)}%, movimiento ${Number.isFinite(latestTrial.motion_tracking_fraction) ? number(100 * latestTrial.motion_tracking_fraction, 1) + "%" : "no aplica"}` : `seguimiento ${number(100 * (latestTrial.tracking_fraction || 0), 1)}%`}, cobertura ${number(100 * (latestTrial.coverage || 0), 1)}%. ${latestTrial.passed ? "Cumplió el criterio del episodio." : "No cumplió el criterio."}`
      : `Primeras dos pruebas: baseline sin aprendizaje de esta etapa. Cada intento dura ${number(training.trial_duration || 36.08, 2)} s simulados.`,
  );
  const evidence = state.evidence || {};
  $("trainingProof").hidden = state.mode === "replay";
  $("liveProofOverlay").hidden = state.mode === "replay" || !training.active;
  text(
    "liveProofOverlay",
    `MaleCNS → MuJoCo${stage ? ` · ${stage.label}` : ""} · ${training.phase === "train" ? "APRENDIZAJE ACTIVO" : "PESOS CONGELADOS"}
Intento ${training.attempt || 0} · ${Number(evidence.total_spikes || 0).toLocaleString("es-AR")} spikes en el episodio
Último paso: ${evidence.changed_this_step || 0} pesos cambiados · ΔL1 ${number(evidence.update_l1, 5)}${training.trial_duration < training.target_duration ? "\nPRUEBA CORTA · no demuestra la coreografía" : ""}`,
  );
  const phaseLabels = {
    baseline: "BASELINE CONGELADO",
    train: "APRENDIZAJE ACTIVO",
    evaluate: "EVALUACIÓN CONGELADA",
    complete: "COMPLETO",
    stopped: "DETENIDO",
  };
  text("trainingPhase", phaseLabels[training.phase] || "SIN SESIÓN");
  text(
    "trainingAttempts",
    Number.isFinite(training.attempt) ? training.attempt : "—",
  );
  text(
    "trainingSeconds",
    Number.isFinite(training.simulated_seconds)
      ? `${number(training.simulated_seconds + (training.current_trial_seconds || 0) + (training.interrupted_seconds || 0), 2)} s`
      : "—",
  );
  text(
    "trainingBest",
    Number.isFinite(training.best_score) ? number(training.best_score) : "—",
  );
  text(
    "trainingNotice",
    training.phase === "baseline"
      ? "Baseline congelado: mide el punto de partida; todavía no hay aprendizaje."
      : training.active
        ? training.phase === "evaluate"
          ? "Evaluación congelada: mide la transferencia."
          : "Aprendizaje MaleCNS en curso: los actuadores reciben spikes."
        : "Sesión detenida o sin iniciar.",
  );
  const history = Array.isArray(training.history)
    ? stageHistory.filter((row) => Number.isFinite(row.score))
    : [];
  const chart = $("trainingChart");
  chart.innerHTML =
    history.length > 1
      ? `<polyline points="${history.map((row, i) => `${(i / (history.length - 1)) * 300},${52 - Math.min(1, Math.max(0, row.score)) * 50}`).join(" ")}" />`
      : "";
  const verified = evidence.verified === true;
  text(
    "trainingEvidence",
    verified
      ? `Verificada · ${evidence.source || "MaleCNS → MuJoCo"}`
      : "Verificación pendiente: faltan pruebas del episodio.",
  );
  text(
    "trainingHashes",
    `Target ${String(evidence.target_hash || "—").slice(0, 12)} · Graph ${String(evidence.graph_hash || "—").slice(0, 12)} · Kernel ${String(evidence.kernel_hash || "—").slice(0, 12)}`,
  );
  const examples = Array.isArray(evidence.weight_examples)
    ? evidence.weight_examples.slice(0, 5)
    : [];
  text(
    "trainingWeights",
    `Spikes acumulados del episodio: ${Number.isFinite(evidence.total_spikes) ? evidence.total_spikes.toLocaleString("es-AR") : "—"}. Último paso: ${Number(evidence.changed_this_step) || 0} conexiones cambiadas; ΔL1 ${number(evidence.update_l1, 6)}.
` +
      (examples.length
        ? examples
            .map(
              (x) =>
                `${x.pre_id} → ${x.post_id}: ${number(x.before, 6)} → ${number(x.after, 6)} (Δ ${number(x.delta, 6)} desde inicio del episodio)`,
            )
            .join("\n")
        : "Sin diferencias de pesos respecto del inicio de este episodio."),
  );
  const link = $("evidenceDownload");
  if (evidence.last_episode_id) {
    link.hidden = false;
    link.href = `/api/evidence/${encodeURIComponent(evidence.last_episode_id)}`;
    link.textContent = "Descargar evidencia del episodio";
    $("reproductionCommand").hidden = false;
    $("reproductionCommand").textContent =
      `python -m gangnamfly.verify episodes/${evidence.last_episode_id}`;
  } else {
    link.hidden = true;
    $("reproductionCommand").hidden = true;
  }
  text("pauseText", state.status === "paused" ? "Continuar" : "Pausar");
  $("pauseText").parentElement.setAttribute(
    "aria-label",
    state.status === "paused" ? "Continuar simulación" : "Pausar simulación",
  );
  text("pauseIcon", state.status === "paused" ? "▶" : "Ⅱ");
  if (modelLoaded && motion) applyTransforms(state);
  renderNeurons(state.motor_rates || []);
  renderNeurons(state.vnc_rates || [], "vncrates");
  renderEpisodes(state.episodes || []);
  updateButtons();
}
async function command(action, episode) {
  if (commandBusy || demo.active) return;
  commandBusy = true;
  updateButtons();
  text("commandError", "");
  try {
    const response = await fetch("/api/command", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action, ...(episode ? { episode } : {}) }),
      signal: AbortSignal.timeout(5000),
    });
    const result = await response.json();
    if (!response.ok)
      throw Error(result.error || "No se pudo ejecutar el comando");
    if (["train", "observe", "replay"].includes(action)) {
      motion = true;
      updateMotion();
    }
  } catch (error) {
    text(
      "commandError",
      error.message || "No se pudo conectar con el servidor.",
    );
  } finally {
    commandBusy = false;
    updateButtons();
  }
}
document
  .querySelectorAll("[data-action]")
  .forEach((button) =>
    button.addEventListener("click", () => command(button.dataset.action)),
  );
$("toggleMotion").addEventListener("click", () => {
  motion = !motion;
  updateMotion();
});
addEventListener("keydown", (event) => {
  if (
    event.code === "Space" &&
    event.target === document.body &&
    (demo.active || !document.querySelector('[data-action="pause"]').disabled)
  ) {
    event.preventDefault();
    if (demo.active) demo.toggle();
    else command("pause");
  }
});
async function poll() {
  try {
    const response = await fetch("/api/state", {
      cache: "no-store",
      signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw Error("Estado no disponible");
    applyState(await response.json());
    text("connection", "API local · conectada");
  } catch {
    lastState = { ...lastState, status: "offline" };
    neuralActivity.update(lastState);
    text("statusText", "sin conexión");
    text("liveLabel", demo.active ? "DEMO" : "OFFLINE");
    $("statusDot").className = "bad";
    text(
      "connection",
      "Sin conexión. Los datos mostrados son los últimos recibidos.",
    );
    updateButtons();
  }
  setTimeout(poll, 100);
}
poll();
let frames = 0,
  fpsStart = performance.now();
function draw(now) {
  if (renderer) {
    demo.render(now);
    renderer.render(world, camera);
    frames++;
    if (now - fpsStart >= 1000) {
      text(
        "renderFps",
        `${Math.round((frames * 1000) / (now - fpsStart))} FPS`,
      );
      frames = 0;
      fpsStart = now;
    }
    requestAnimationFrame(draw);
  }
}
requestAnimationFrame(draw);
