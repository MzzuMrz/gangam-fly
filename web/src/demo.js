// Local playback only. The clip was sampled on an independent MuJoCo MjData.
export class ReferenceDemo {
  constructor(applyFrame, onMode) {
    this.applyFrame = applyFrame;
    this.onMode = onMode;
    this.active = false;
    this.playing = !matchMedia("(prefers-reduced-motion: reduce)").matches;
    this.clip = null;
    this.pending = null;
    this.time = 0;
    this.speed = 1;
    this.previous = null;
    this.dirty = true;
    this.phase = "Incorporación";
    this.ui = Object.fromEntries(
      [
        "demoPause",
        "demoRestart",
        "demoSeek",
        "demoSpeed",
        "demoClock",
        "demoMessage",
      ].map((id) => [id, document.getElementById(id)]),
    );
    this.ui.demoPause.addEventListener("click", () => this.toggle());
    this.ui.demoRestart.addEventListener("click", () => this.seek(0));
    this.ui.demoSeek.addEventListener("input", (event) =>
      this.seek(Number(event.target.value)),
    );
    this.ui.demoSpeed.addEventListener("change", (event) => {
      this.speed = Number(event.target.value);
      this.previous = null;
    });
    this.refresh();
  }

  async activate() {
    this.active = true;
    this.previous = null;
    this.dirty = true;
    this.onMode(true);
    if (!this.clip) {
      this.ui.demoMessage.textContent = "Preparando captura continua…";
      try {
        this.pending ||= this.fetchClip();
        this.clip = await this.pending;
        this.ui.demoSeek.max = this.clip.duration;
      } catch (error) {
        if (this.active) this.ui.demoMessage.textContent = error.message;
        return;
      } finally {
        this.pending = null;
      }
    }
    this.ui.demoMessage.textContent =
      "Captura continua · Xsens · Gangnam Style";
    this.updatePhase();
    this.refresh();
  }

  async fetchClip() {
    const deadline = performance.now() + 60000;
    while (performance.now() < deadline) {
      const response = await fetch("/api/demo", {
        signal: AbortSignal.timeout(
          Math.max(1, Math.min(15000, Math.ceil(deadline - performance.now()))),
        ),
      });
      if (response.ok) return response.json();
      if (response.status !== 503)
        throw Error("No se pudo cargar la referencia.");
      if (this.active) this.ui.demoMessage.textContent = "Generando captura…";
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
    throw Error("La referencia tardó demasiado. Volvé a intentar DEMO.");
  }

  deactivate() {
    this.active = false;
    this.previous = null;
    this.onMode(false);
  }

  updatePhase() {
    if (!this.clip) return;
    const next =
      this.time < this.clip.stand_seconds
        ? "Incorporación"
        : this.time < this.clip.duration - this.clip.finish_seconds
          ? "Captura continua"
          : "Cierre";
    if (next !== this.phase) {
      this.phase = next;
      const phase = document.getElementById("demoPhase");
      if (phase) phase.textContent = next;
    }
  }

  toggle() {
    if (!this.clip) return;
    this.playing = !this.playing;
    this.previous = null;
    this.refresh();
  }

  seek(seconds) {
    if (!this.clip) return;
    this.time = Math.max(0, Math.min(seconds, this.clip.duration));
    this.updatePhase();
    this.previous = null;
    this.dirty = true;
    this.refresh();
  }

  refresh() {
    for (const id of ["demoPause", "demoRestart", "demoSeek", "demoSpeed"])
      this.ui[id].disabled = !this.clip;
    this.ui.demoPause.textContent = this.playing ? "Pausar demo" : "Reproducir";
    this.ui.demoPause.setAttribute("aria-pressed", String(!this.playing));
    this.ui.demoSeek.value = this.time;
    this.ui.demoClock.textContent = `${this.time.toFixed(2)} / ${(this.clip?.duration || 0).toFixed(2)} s`;
  }

  render(now) {
    if (!this.active || !this.clip) return;
    if (this.playing && this.previous !== null) {
      this.time =
        (this.time + ((now - this.previous) / 1000) * this.speed) %
        this.clip.duration;
      this.dirty = true;
    }
    this.previous = now;
    this.updatePhase();
    if (!this.dirty) return;
    const frames = this.clip.frames;
    const sample = (this.time / this.clip.duration) * (frames.length - 1);
    const index = Math.min(Math.floor(sample), frames.length - 2);
    this.applyFrame(frames[index], frames[index + 1], sample - index);
    document.getElementById("simClock").textContent =
      `DEMO · ${this.time.toFixed(2)} s`;
    this.refresh();
    this.dirty = false;
  }
}
