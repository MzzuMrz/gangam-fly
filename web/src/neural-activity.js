// Read-only display of published rates. No individual spike timing is inferred.
export class ActivityHistory {
  constructor() {
    this.clear();
  }
  clear() {
    this.samples = [];
    this.channels = [];
    this.key = null;
    this.previous = null;
    this.graphRate = null;
    this.total = null;
  }
  update(state) {
    if (
      !["running", "paused", "idle"].includes(state.status) ||
      state.mode === "replay"
    ) {
      this.clear();
      return true;
    }
    const key = state.episode_id;
    if (!key) {
      if (this.key !== state.evidence?.last_episode_id) this.clear();
      return false;
    }
    const time = state.sim_time,
      total = state.evidence?.total_spikes;
    if (
      !key ||
      !Number.isFinite(time) ||
      time < 0 ||
      !Number.isSafeInteger(total) ||
      total < 0
    ) {
      this.clear();
      return true;
    }
    const rows = [
      ...(state.motor_rates || []).map((r) => ({ ...r, kind: "DN" })),
      ...(state.vnc_rates || []).map((r) => ({ ...r, kind: "VNC" })),
    ];
    const channels = rows.map((r) => `${r.kind} · ${r.name}`);
    if (
      key !== this.key ||
      JSON.stringify(channels) !== JSON.stringify(this.channels) ||
      (this.previous &&
        (time < this.previous.time || total < this.previous.total))
    )
      this.clear();
    this.key = key;
    this.channels = channels;
    this.total = total;
    if (this.previous?.time === time) return false;
    this.graphRate = this.previous
      ? (total - this.previous.total) / (time - this.previous.time)
      : null;
    const rates = rows.map((r) =>
      Number.isFinite(r.rate) && r.rate >= 0 ? r.rate : null,
    );
    this.samples.push({ time, rates });
    this.samples = this.samples.filter((s) => s.time >= time - 4).slice(-200);
    this.previous = { time, total };
    return true;
  }
}

export class NeuralActivity {
  constructor(root) {
    this.root = root;
    this.history = new ActivityHistory();
    this.paused = false;
    root.innerHTML = `
      <div class="panel-head"><h2>Actividad neuronal · MaleCNS</h2><span id="neuralStatus" class="pill">ESPERANDO</span></div>
      <p>6 observadores descendentes y 6 medias motoras VNC. Tasas reales publicadas por el cerebro; no es un mapa anatómico ni un raster de las 166.700 neuronas.</p>
      <div class="neural-stats"><div>Spikes del grafo en el episodio <b id="neuralTotal">—</b></div><div>Spikes/s del grafo entre muestras <b id="neuralGraphRate">—</b></div><div>Muestras del visor <b id="neuralSamples">0</b></div></div>
      <div class="neural-actions"><button id="neuralPause" aria-pressed="false">Pausar gráfico</button><button id="neuralClear">Limpiar gráfico</button></div>
      <p id="neuralMessage" role="status">Esperando telemetría neuronal.</p>
      <canvas id="neuralCanvas" width="900" height="300" role="img" aria-label="Historial de tasas neuronales observadas" aria-describedby="neuralLegend"></canvas>
      <p id="neuralLegend">Ventana: 4 s simulados. Cada marca representa una muestra de 20 ms; los huecos no tienen datos. Color: 0–100 Hz (satura a 100). VNC: media de 10 tasas poblacionales por pata, filtradas a 80 ms. Hz significa spikes por segundo simulado, no fuerza ni movimiento.</p>
      <details><summary>Tasas numéricas por canal</summary><table class="neural-table"><caption>Última muestra publicada; las medias VNC no representan una neurona individual.</caption><thead><tr><th scope="col">Canal</th><th scope="col">Hz</th></tr></thead><tbody id="neuralRates"></tbody></table></details>`;
    this.canvas = root.querySelector("canvas");
    this.ctx = this.canvas.getContext("2d");
    root.querySelector("#neuralPause").addEventListener("click", () => {
      this.paused = !this.paused;
      if (!this.paused) this.history.clear();
      root.querySelector("#neuralPause").textContent = this.paused
        ? "Continuar gráfico"
        : "Pausar gráfico";
      root
        .querySelector("#neuralPause")
        .setAttribute("aria-pressed", String(this.paused));
      this.render(this.lastState);
    });
    root.querySelector("#neuralClear").addEventListener("click", () => {
      this.history.clear();
      this.render(this.lastState);
    });
  }
  reset() {
    this.history.clear();
    this.render(this.lastState);
  }
  update(state) {
    this.lastState = state;
    const invalid =
      !["running", "paused", "idle"].includes(state.status) ||
      state.mode === "replay";
    const key = state.episode_id || state.evidence?.last_episode_id;
    if (invalid || (this.history.key && key !== this.history.key))
      this.history.clear();
    if (!this.paused) this.history.update(state);
    this.render(state);
  }
  text(id, value) {
    this.root.querySelector(`#${id}`).textContent = value;
  }
  render(state = {}) {
    const replay = state?.mode === "replay";
    const unavailable = !["running", "paused", "idle"].includes(state?.status);
    const h = this.history;
    this.text(
      "neuralStatus",
      replay
        ? "REPLAY · SIN DATOS"
        : unavailable
          ? "SIN DATOS"
          : this.paused
            ? "GRÁFICO PAUSADO"
            : state.status === "paused"
              ? "SIMULACIÓN PAUSADA"
              : state.status === "idle"
                ? h.samples.length
                  ? "ÚLTIMA MUESTRA"
                  : "ESPERANDO EPISODIO"
                : "EN VIVO",
    );
    this.text(
      "neuralMessage",
      replay
        ? "No se presenta el contador del cerebro vivo como actividad del replay."
        : unavailable
          ? "Telemetría no disponible; esperando conexión."
          : this.paused
            ? state.status === "running" && state.mode === "train"
              ? "Sólo el gráfico está pausado. El entrenamiento continúa."
              : "El gráfico está congelado; este control no cambia el estado de la simulación."
            : !h.samples.length
              ? "Sin muestras neuronales de una ejecución activa."
              : "Observación del cerebro; no demuestra aprendizaje. Los huecos quedan sin rellenar.",
    );
    this.text(
      "neuralTotal",
      h.total === null ? "—" : h.total.toLocaleString("es-AR"),
    );
    this.text(
      "neuralGraphRate",
      h.graphRate === null
        ? "—"
        : h.graphRate.toLocaleString("es-AR", { maximumFractionDigits: 0 }),
    );
    this.text("neuralSamples", String(h.samples.length));
    const body = this.root.querySelector("#neuralRates");
    const last = h.samples.at(-1);
    body.replaceChildren(
      ...h.channels.map((name, i) => {
        const tr = document.createElement("tr"),
          label = document.createElement("th"),
          value = document.createElement("td");
        label.scope = "row";
        label.textContent = name;
        value.textContent =
          last?.rates[i] === null || !last ? "—" : last.rates[i].toFixed(1);
        tr.append(label, value);
        return tr;
      }),
    );
    const w = Math.max(
      280,
      Math.round(this.canvas.getBoundingClientRect().width),
    );
    const height = 300,
      ratio = Math.min(3, globalThis.devicePixelRatio || 1);
    this.canvas.style.height = `${height}px`;
    if (
      this.canvas.width !== Math.round(w * ratio) ||
      this.canvas.height !== Math.round(height * ratio)
    ) {
      this.canvas.width = Math.round(w * ratio);
      this.canvas.height = Math.round(height * ratio);
    }
    const c = this.ctx;
    c.setTransform(ratio, 0, 0, ratio, 0, 0);
    c.fillStyle = "#111815";
    c.fillRect(0, 0, w, height);
    if (!last) return;
    const left = w < 500 ? 125 : 160,
      right = 60,
      top = 10,
      rowHeight = 20,
      plotWidth = w - left - right;
    const start = Math.max(0, last.time - 4),
      span = Math.max(0.02, last.time - start);
    c.font = "12px monospace";
    c.textBaseline = "middle";
    h.channels.forEach((name, i) => {
      c.fillStyle = "#dce6de";
      c.fillText(name, 8, top + i * rowHeight + 9);
      c.fillText(
        last.rates[i] === null ? "—" : last.rates[i].toFixed(1),
        w - right + 6,
        top + i * rowHeight + 9,
      );
    });
    h.samples.forEach((sample) => {
      const x = left + ((sample.time - 0.02 - start) / span) * plotWidth;
      sample.rates.forEach((rate, i) => {
        if (rate === null) return;
        const v = Math.min(1, rate / 100);
        c.fillStyle = `rgb(${Math.round(35 + 150 * v)},${Math.round(55 + 175 * v)},${Math.round(45 + 55 * v)})`;
        c.fillRect(
          Math.max(left, x),
          top + i * rowHeight,
          Math.min((plotWidth * 0.02) / span, w - right - Math.max(left, x)),
          16,
        );
      });
    });
    c.fillStyle = "#dce6de";
    c.fillText(`${Math.max(0, start).toFixed(2)} s`, left, height - 16);
    c.textAlign = "right";
    c.fillText(`${last.time.toFixed(2)} s`, w - right, height - 16);
    c.textAlign = "left";
  }
}
