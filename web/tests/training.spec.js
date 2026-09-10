import { test, expect } from "@playwright/test";

// AC-4: synthetic API fixtures test presentation only, not real neural learning.
test("evidence UI shows measured values and never invents verification", async ({
  page,
  request,
}) => {
  const base = await (await request.get("/api/state")).json();
  const episode = "20260909T120000-abcdef12";
  const fixture = {
    ...base,
    status: "running",
    mode: "observe",
    training: {
      active: true,
      phase: "baseline",
      attempt: 0,
      simulated_seconds: 0,
      baseline_score: null,
      best_score: null,
      history: [],
    },
    evidence: {
      source: "MaleCNS → MuJoCo",
      verified: false,
      target_hash: "target-fixture",
      graph_hash: "graph-fixture",
      kernel_hash: "kernel-fixture",
      total_spikes: 12345,
      changed_this_step: 0,
      update_l1: 0,
      weight_examples: [],
      last_episode_id: episode,
    },
  };
  await page.route("**/api/state", (route) => route.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(page.locator("#trainingPhase")).toHaveText("BASELINE CONGELADO");
  await expect(page.locator("#trainingNotice")).toContainText(
    "todavía no hay aprendizaje",
  );
  await expect(page.locator('[data-action="train"]')).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await expect(page.locator('[data-action="observe"]')).toHaveAttribute(
    "aria-pressed",
    "false",
  );
  await expect(page.locator("#trainingEvidence")).toContainText("pendiente");
  const overlay = await page.locator("#liveProofOverlay").boundingBox();
  const viewport = await page.locator("#viewportPanel").boundingBox();
  expect(overlay.y).toBeGreaterThan(viewport.y);
  expect(overlay.x).toBeGreaterThan(viewport.x);
  fixture.mode = "train";
  fixture.training.phase = "train";
  fixture.training.attempt = 2;
  fixture.training.baseline_score = 0.12;
  fixture.training.history = [
    { phase: "baseline", score: 0.12 },
    { phase: "train", score: 0.25, coverage: 0.01, passed: false },
  ];
  fixture.evidence.changed_this_step = 17;
  fixture.evidence.update_l1 = 0.002;
  fixture.evidence.weight_examples = [
    { pre_id: 100, post_id: 200, before: 1, after: 1.001, delta: 0.001 },
  ];
  await expect(page.locator("#trainingPhase")).toHaveText("APRENDIZAJE ACTIVO");
  await expect(page.locator("#trainingWeights")).toContainText(
    "17 conexiones cambiadas",
  );
  await expect(page.locator("#trainingWeights")).toContainText("100 → 200");
  await expect(page.locator("#trainingLatest")).toContainText("No cumplió");
  await expect(page.locator("#evidenceDownload")).toHaveAttribute(
    "href",
    `/api/evidence/${episode}`,
  );
  await expect(page.locator("#reproductionCommand")).toContainText(episode);
  await expect(page.locator("#trainingHashes")).toContainText("graph-fixtur");
  fixture.mode = "observe";
  fixture.training.phase = "evaluate";
  fixture.evidence.changed_this_step = 0;
  fixture.evidence.update_l1 = 0;
  fixture.evidence.weight_examples = [];
  await expect(page.locator("#trainingPhase")).toHaveText(
    "EVALUACIÓN CONGELADA",
  );
  await expect(page.locator("#trainingEvidence")).toContainText("pendiente");
  await page.getByRole("button", { name: "DEMO", exact: true }).click();
  await expect(page.locator("#trainingProof")).toBeHidden();
});

// AC-4, AC-5: real saved evidence, no API fixture or simulated verification.
test("saved verified episode downloads from the actual local server", async ({
  page,
  request,
}) => {
  const state = await (await request.get("/api/state")).json();
  expect(state.evidence.last_episode_id).toBeTruthy();
  await page.goto("/");
  await expect(page.locator("#evidenceDownload")).toBeVisible();
  const response = await request.get(
    `/api/evidence/${state.evidence.last_episode_id}`,
  );
  expect(response.status()).toBe(200);
  expect(response.headers()["content-type"]).toBe("application/zip");
  expect((await response.body()).subarray(0, 2).toString()).toBe("PK");
  if (state.evidence.verified) {
    await expect(page.locator("#trainingEvidence")).toContainText("Verificada");
  }
});

// Curriculum AC-4: stage-local measurements and locked future steps.
test("curriculum shows prerequisites and separates stage reward histories", async ({
  page,
  request,
}) => {
  const fixture = await (await request.get("/api/state")).json();
  fixture.status = "running";
  fixture.mode = "train";
  fixture.reward = 0.2;
  fixture.reward_mean = 0.123;
  fixture.training = {
    active: true,
    phase: "train",
    attempt: 1,
    trial_duration: 4,
    target_duration: 4,
    stage: {
      index: 0,
      count: 6,
      id: "stand",
      label: "Incorporarse",
      criterion_label: "Postura estable durante 1 s",
    },
    stages: [
      { id: "stand", label: "Incorporarse", active: true, completed: false },
      {
        id: "balance",
        label: "Mantener el equilibrio",
        active: false,
        completed: false,
      },
    ],
    history: [
      { stage_index: 0, phase: "baseline", score: 0.1 },
      { stage_index: 0, phase: "train", score: 0.2 },
    ],
  };
  await page.route("**/api/state", (route) => route.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(page.locator("#trainingStage")).toHaveText(
    "Etapa 1/6 · Incorporarse",
  );
  await expect(page.locator("#trainingStages")).toContainText(
    "Mantener el equilibrio · bloqueada",
  );
  await expect(page.locator("#rewardMean")).toHaveText("0.123");
  await expect(page.locator("#trainingQuality")).toContainText(
    "Postura estable durante 1 s",
  );
  await expect(page.locator("#trainingChart polyline")).toBeVisible();
  fixture.training.stage = {
    ...fixture.training.stage,
    index: 1,
    id: "balance",
    label: "Mantener el equilibrio",
  };
  fixture.training.history.push({
    stage_index: 1,
    phase: "baseline",
    score: 0.4,
  });
  await expect(page.locator("#trainingStage")).toHaveText(
    "Etapa 2/6 · Mantener el equilibrio",
  );
  await expect(page.locator("#trainingChart polyline")).toHaveCount(0);
  await expect(page.locator("#trainingLatest")).toContainText("0.400");
});

// Micro AC-3, AC-5: many stages stay compact and support is not labeled standing.
test("microcurriculum keeps stage list compact and distinguishes standing", async ({
  page,
  request,
}) => {
  const fixture = await (await request.get("/api/state")).json();
  fixture.status = "running";
  fixture.mode = "train";
  fixture.training = {
    active: true,
    phase: "train",
    stage: {
      index: 0,
      count: 176,
      label: "Apoyar patas",
      protocol: "micro-v1",
      criterion_label: "Apoyo parcial",
    },
    stages: Array.from({ length: 176 }, (_, i) => ({
      label: `Paso ${i + 1}`,
      active: i === 0,
      completed: false,
    })),
    history: [],
  };
  fixture.objective_metrics = {
    foot_load_fraction: 0.3,
    other_load_fraction: 0.7,
    stage_ok: true,
    standing_ok: false,
  };
  await page.route("**/api/state", (route) => route.fulfill({ json: fixture }));
  await page.goto("/");
  await expect(page.locator("#trainingNext")).toContainText("Paso 2");
  await expect(page.locator("#trainingStages")).toBeHidden();
  await expect(page.locator("#trainingPhysical")).toContainText("Erguida: no");
  await expect(page.locator("#trainingPhysical")).toContainText(
    "Etapa: cumple este paso",
  );
  await page.locator("#trainingAllStages summary").click();
  await expect(page.locator("#trainingStages li")).toHaveCount(176);
});
