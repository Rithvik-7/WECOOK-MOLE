import {
  $, badge, escapeHtml, fmt, getJson, postJson, setModeBanner, timeAgo, toast,
} from "/assets/common.js";
import { drawForecastChart } from "/assets/charts.js";

let state = null;
let chartMetric = "tilt";
let pollTimer = null;
let lastChartKey = "";

function nodeName(id) {
  return id === 1 ? "Node A · movement zone" : "Node B · comparison zone";
}

function nodeCard(node) {
  const letter = node.node_id === 1 ? "A" : "B";
  const tiltHot = Number(node.tilt_change_deg) >= 3;
  const gapHot = Number(node.relative_mm) >= 2;
  const gapText = node.relative_mm == null
    ? (node.adc_raw == null ? "no ADC yet" : "save slider cal")
    : `${fmt(node.relative_mm)} mm`;
  const calibration = node.node_id === 1
    ? `<div class="metric${gapHot ? " hot" : ""}"><span>Crack gap</span><strong>${gapText}</strong></div>
        <div class="metric"><span>Slider ADC</span><strong>${node.adc_raw == null ? "—" : node.adc_raw}</strong></div>`
    : `<div class="metric"><span>Role</span><strong>Compare</strong></div>`;
  const latch = node.latched_alert ? badge("ALERT", node.acked ? "Alert acknowledged" : "Alert latched") : "";
  const baseline = node.baseline ? "Baseline captured" : "Baseline not captured";
  const imu = node.imu_ok === true ? "IMU valid" : node.imu_ok === false ? "IMU invalid" : "IMU unseen";
  return `
    <div class="card-head">
      <div>
        <p class="eyebrow">Fixed monitor ${letter}</p>
        <h2>${nodeName(node.node_id)}</h2>
      </div>
      <div class="row">${badge(node.status)}${latch}</div>
    </div>
    <div class="card-body">
      <div class="hero-metric${tiltHot ? " hot" : ""}">
        <span>Tilt from baseline</span>
        <strong>${fmt(node.tilt_change_deg)}°</strong>
      </div>
      <div class="metrics">
        ${calibration}
        <div class="metric"><span>Vibration</span><strong>${fmt(node.vibration_g, 4)} g</strong></div>
        <div class="metric"><span>Roll / pitch</span><strong>${fmt(node.roll_deg)}° / ${fmt(node.pitch_deg)}°</strong></div>
        <div class="metric"><span>Last packet</span><strong>${timeAgo(node.age_s)}</strong></div>
      </div>
      <p class="reason">${escapeHtml(node.reason)}</p>
      <p class="micro" style="margin-top:9px">
        ${baseline} · ${imu} · lost ${node.packets_lost} · dup ${node.duplicates}
      </p>
    </div>`;
}

function modelCard(id, ai, forecast) {
  const progress = Math.min(100, Math.round((ai.n_train / ai.min_train) * 100));
  const quality = forecast.quality || "INSUFFICIENT_DATA";
  const score = ai.score === null ? "—" : fmt(ai.score, 4);
  const feature = ai.top_feature || "—";
  const mae = forecast.mae === null ? "—" : `${fmt(forecast.mae, 5)} ${forecast.unit}`;
  const names = (ai.feature_names || []).join(", ") || "tilt_change_deg, vibration_g, d_tilt";
  const trainNote = ai.prior
    ? "Shipped tabletop prior — already trained"
    : ai.simulated
      ? "In-memory simulation model (not saved)"
      : ai.can_train
        ? (ai.trained_at || "Not trained yet")
        : "Persisted training blocked in simulation";
  const forecastModel = forecast.model || "sklearn forecast";
  return `
    <div class="model-box">
      <div class="spread">
        <strong>Node ${id === 1 ? "A" : "B"}</strong>
        <div class="row">${badge(ai.state)}${badge(quality)}</div>
      </div>
      <div class="progress" title="${progress}%"><span style="width:${progress}%"></span></div>
      <p class="micro">${ai.n_train}/${ai.min_train} NORMAL samples · Isolation Forest + LOF</p>
      <dl class="kv">
        <dt>Isolation Forest</dt><dd>${escapeHtml(ai.isolation_state || ai.state)}</dd>
        <dt>Local Outlier Factor</dt><dd>${escapeHtml(ai.lof_state || "INACTIVE")}</dd>
        <dt>Detector votes</dt><dd>${ai.votes ?? 0} / 2 unusual</dd>
        <dt>Anomaly score</dt><dd>${score}</dd>
        <dt>Largest deviation</dt><dd>${escapeHtml(feature)}</dd>
        <dt>Features</dt><dd>${escapeHtml(names)}</dd>
        <dt>Contamination</dt><dd>${ai.contamination ?? 0.05}</dd>
        <dt>Selected forecast</dt><dd>${escapeHtml(forecast.selected || "Ridge")}</dd>
        <dt>Forecast MAE</dt><dd>${mae}</dd>
        <dt>Forecast surprise</dt><dd>${forecast.surprise_state || "INACTIVE"}${forecast.surprise_z == null ? "" : ` · z=${fmt(forecast.surprise_z, 2)}`}</dd>
        <dt>Trained at</dt><dd>${escapeHtml(trainNote)}</dd>
      </dl>
      <p class="micro" style="margin-top:8px">${escapeHtml(forecastModel)}</p>
    </div>`;
}

const SCENARIO_HELP = {
  normal: "Quiet tabletop. Use this as the healthy baseline.",
  rising: "Node A tilt and crack climb slowly; Node B stays quiet. Best forecast demo.",
  watch: "Persistent ~3° Node A tilt. Rules should show WATCH.",
  alert: "Persistent ~6° Node A tilt. ALERT latches until recovered and cleared.",
  offline: "No packets. Both nodes become UNKNOWN after 5 s.",
  sensor_fault: "Node A IMU invalid; Node B still reporting.",
};

function etaText(seconds) {
  if (seconds === null || seconds === undefined) return "—";
  if (seconds <= 0) return "now";
  return `${fmt(seconds, 1)} s`;
}

function predictionRow(label, current, forecast) {
  if (!forecast) {
    return `<tr class="faded"><td>${escapeHtml(label)}</td><td colspan="6" class="muted">Not applicable</td></tr>`;
  }
  const now = current === null || current === undefined ? "—" : `${fmt(current, 3)} ${forecast.unit}`;
  const future = forecast.points?.length
    ? `${fmt(forecast.points[forecast.points.length - 1], 3)} ${forecast.unit}`
    : "learning";
  const mae = forecast.mae === null || forecast.mae === undefined
    ? "—"
    : `${fmt(forecast.mae, 4)} ${forecast.unit}`;
  const hot = forecast.seconds_to_alert !== null && forecast.seconds_to_alert <= 30;
  const warm = !hot && forecast.seconds_to_watch !== null && forecast.seconds_to_watch <= 30;
  return `<tr class="${hot ? "hot" : warm ? "warm" : ""}">
    <td>${escapeHtml(label)}</td>
    <td class="numeric">${now}</td>
    <td class="numeric">${future}</td>
    <td class="numeric">${mae}</td>
    <td>${badge(forecast.quality || "INSUFFICIENT_DATA")}</td>
    <td class="numeric">${etaText(forecast.seconds_to_watch)}</td>
    <td class="numeric">${etaText(forecast.seconds_to_alert)}</td>
  </tr>`;
}

function renderPredictions(next) {
  const a = next.nodes["1"];
  const b = next.nodes["2"];
  const fa = next.forecast["1"];
  const fb = next.forecast["2"];
  $("predictionRows").innerHTML = [
    predictionRow("Node A tilt", a.tilt_change_deg, fa.tilt),
    predictionRow("Node B tilt", b.tilt_change_deg, fb.tilt),
    predictionRow("Node A vibration", a.vibration_g, fa.vibration),
    predictionRow("Node B vibration", b.vibration_g, fb.vibration),
    predictionRow("Node A crack gap", a.relative_mm, fa.gap),
  ].join("");
}

function renderMlStack(next) {
  const box = $("mlStack");
  if (!box) return;
  const stack = next.ml_stack || {};
  const joint = next.joint || {};
  const fa = next.forecast["1"].tilt || {};
  const candidates = Object.entries(fa.candidates || {})
    .map(([name, mae]) => `${name} ${Number(mae).toFixed(4)}`)
    .join(" · ") || "learning";
  box.innerHTML = `
    <p class="micro">${escapeHtml(stack.label || "")}</p>
    <dl class="kv">
      <dt>Detectors</dt><dd>${escapeHtml((stack.detectors || []).join(" · "))}</dd>
      <dt>Forecast family</dt><dd>${escapeHtml((stack.forecasters || []).join(" · "))}</dd>
      <dt>Model selection</dt><dd>${escapeHtml(stack.selection || "holdout MAE")}</dd>
      <dt>Selected tilt model</dt><dd>${escapeHtml(fa.selected || "—")}</dd>
      <dt>Holdout MAE table</dt><dd>${escapeHtml(candidates)}</dd>
      <dt>Joint A vs B</dt><dd>${escapeHtml(joint.state || "INACTIVE")} · ${escapeHtml(joint.pattern || "UNKNOWN")}</dd>
      <dt>Joint score</dt><dd>${joint.score == null ? "—" : fmt(joint.score, 4)}</dd>
    </dl>
    <p class="reason">${escapeHtml(joint.reason || "Joint residual model is learning paired NORMAL samples.")}</p>
  `;
}

function renderWorkflow(status) {
  const inspect = status === "ALERT" || status === "WATCH";
  document.querySelectorAll("#workflow li").forEach((item) => {
    const step = item.dataset.step;
    item.classList.toggle("current", inspect ? step === "inspect" : step === "monitor");
  });
  const cta = $("inspectCta");
  if (cta) {
    cta.hidden = !inspect;
    const title = $("inspectCtaTitle");
    const text = $("inspectCtaText");
    if (status === "WATCH") {
      if (title) title.textContent = "WATCH is on.";
      if (text) text.textContent = "Rules fired first. Review the evidence, inspect with the rover if needed, then click Inspection done. IR will not auto-brake.";
    } else {
      if (title) title.textContent = "A warning is latched.";
      if (text) text.textContent = "Inspect with the rover, then click Inspection done on this page. That closes a recovered latch on both nodes. History stays.";
    }
  }
}

function currentChart() {
  if (!state || document.hidden) return;
  const a = state.nodes["1"].history || [];
  const b = state.nodes["2"].history || [];
  const key = `${chartMetric}:${state.nodes["1"].seq}:${state.nodes["2"].seq}:${state.calibration?.adc0}:${state.nodes["1"].relative_mm}:${state.forecast["1"].tilt?.points?.at(-1)}`;
  if (key === lastChartKey) return;
  lastChartKey = key;
  let seriesKey, unit, watch, alert, fa, fb;
  if (chartMetric === "vibration") {
    seriesKey = "vib"; unit = "g"; watch = null; alert = null;
    fa = state.forecast["1"].vibration;
    fb = state.forecast["2"].vibration;
  } else if (chartMetric === "gap") {
    seriesKey = "mm"; unit = "mm"; watch = 2; alert = 4;
    fa = state.forecast["1"].gap;
    fb = null;
  } else {
    seriesKey = "tilt"; unit = "deg"; watch = 3; alert = 6;
    fa = state.forecast["1"].tilt;
    fb = state.forecast["2"].tilt;
  }
  drawForecastChart($("signalChart"), {
    seriesA: a.map((p) => p[seriesKey]),
    seriesB: chartMetric === "gap" ? [] : b.map((p) => p[seriesKey]),
    forecastA: fa,
    forecastB: fb,
    unit, watch, alert,
  });
  const pieces = [fa?.label || "30 s sensor trend forecast — not a collapse prediction."];
  if (fa?.state === "READY") {
    pieces.push(`Node A ${fa.quality} quality; holdout MAE ${fmt(fa.mae, 5)} ${unit}.`);
    if (fa.seconds_to_alert !== null) {
      pieces.push(`At the recent fitted rate: ${fmt(fa.seconds_to_alert, 1)} s to ALERT threshold.`);
    }
  } else if (fa?.reason) {
    pieces.push(fa.reason);
  }
  $("forecastCaption").textContent = pieces.join(" ");
}

function render(next) {
  state = next;
  document.body.dataset.status = state.system_status;
  setModeBanner(state.simulated);
  const rehearsal = $("rehearsalBar");
  if (rehearsal) rehearsal.classList.toggle("show", Boolean(state.simulated));
  $("nodeA").className = `card node-a tone-${state.nodes["1"].status}`;
  $("nodeB").className = `card node-b tone-${state.nodes["2"].status}`;
  $("nodeA").innerHTML = nodeCard(state.nodes["1"]);
  $("nodeB").innerHTML = nodeCard(state.nodes["2"]);
  const summary = $("systemSummary");
  if (summary) summary.className = `summary ${state.system_status}`;

  const badgeNode = $("systemBadge");
  badgeNode.className = `badge ${state.system_status}`;
  badgeNode.textContent = state.system_status;
  const freshNodes = Object.values(state.nodes).filter((n) => n.seen && n.age_s !== null && n.age_s <= 5).length;
  const action = state.next_action || "";
  $("systemTitle").textContent = state.system_status === "NORMAL" ? "Healthy data" :
    state.system_status === "WATCH" ? "Attention needed" :
    state.system_status === "ALERT" ? "Inspection recommended" :
    action.includes("Baseline") ? "Live — capture baselines" :
    action.includes("Slider") ? "Live — calibrate slider" :
    freshNodes > 0 ? "One node stale" : "Data unavailable";
  $("nextAction").className = `next-action ${state.system_status}`;
  $("nextActionText").textContent = state.next_action;

  $("receiverState").textContent = state.simulated
    ? "Simulated"
    : !state.serial_connected ? "USB reconnecting" : `${freshNodes} / 2 fresh`;
  $("receiverDetail").textContent = state.simulated
    ? "No hardware connected"
    : state.serial_error || `${state.serial_port || "serial"} · ${state.dropped} rejected`;
  const ready = Object.values(state.ai).filter((item) => item.state !== "INACTIVE").length;
  $("aiReadiness").textContent = `${ready} / 2`;
  $("packetCount").textContent = state.database.packets.toLocaleString();

  $("ruleEvidence").textContent = `${state.nodes["1"].reason} ${state.nodes["2"].reason}`;
  $("comparison").textContent = state.compare;
  const forecast = state.forecast["1"].tilt;
  const eta = forecast.seconds_to_alert === null ? "" :
    ` If the recent fitted rate holds: ${fmt(forecast.seconds_to_alert, 1)} s to the tabletop ALERT threshold.`;
  $("mlEvidence").textContent =
    `${state.ai["1"].reason} ${state.ai["2"].reason} ${forecast.reason || ""}${eta}`;
  $("modelCards").innerHTML =
    modelCard(1, state.ai["1"], state.forecast["1"].tilt) +
    modelCard(2, state.ai["2"], state.forecast["2"].tilt);
  renderMlStack(state);
  renderPredictions(state);
  renderWorkflow(state.system_status);

  document.querySelectorAll("[data-action='train']").forEach((button) => {
    button.disabled = state.simulated;
  });
  const trainHint = $("trainHint");
  if (trainHint) {
    trainHint.textContent = state.simulated
      ? "Anomaly models are already loaded (tabletop prior). You do not need to wait 120 samples. Train A/B is only for a later live retrain."
      : "Priors are already loaded. Optional live retrain needs ≥120 NORMAL samples and no WATCH/ALERT.";
  }
  document.querySelectorAll("[data-scenario]").forEach((button) => {
    button.classList.toggle("selected", button.dataset.scenario === state.scenario);
  });
  const scenarioHelp = $("scenarioHelp");
  if (scenarioHelp && state.scenario) {
    scenarioHelp.textContent = SCENARIO_HELP[state.scenario] || scenarioHelp.textContent;
  }
  const clock = $("liveClock");
  if (clock) clock.textContent = new Date().toLocaleTimeString();
  const form = $("calibrationForm");
  if (form && !form.dataset.filled && state.calibration?.slider_ready) {
    ["adc0", "adc1", "mm0", "mm1"].forEach((key) => {
      if (form.elements[key] && state.calibration[key] != null) {
        form.elements[key].value = state.calibration[key];
      }
    });
    form.dataset.filled = "1";
  }

  const events = state.events || [];
  $("events").innerHTML = events.length ? events.map((event) => `
    <tr>
      <td class="numeric">${new Date(event.ts * 1000).toLocaleTimeString()}</td>
      <td>${event.node_id ? `Node ${event.node_id === 1 ? "A" : "B"}` : "System"}</td>
      <td>${escapeHtml(event.kind)}</td>
      <td>${escapeHtml(event.detail)}</td>
    </tr>`).join("") : `<tr><td colspan="4" class="muted">No events yet.</td></tr>`;
  currentChart();
}

async function poll() {
  try {
    render(await getJson("/api/state"));
  } catch (error) {
    $("receiverState").textContent = "Backend offline";
    $("receiverDetail").textContent = error.message;
  } finally {
    clearTimeout(pollTimer);
    pollTimer = setTimeout(poll, 1000);
  }
}

document.querySelectorAll("[data-chart]").forEach((button) => {
  button.addEventListener("click", () => {
    document.querySelectorAll("[data-chart]").forEach((item) => item.classList.remove("active"));
    button.classList.add("active");
    chartMetric = button.dataset.chart;
    lastChartKey = "";
    currentChart();
  });
});

document.querySelectorAll("[data-action]").forEach((button) => {
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const result = await postJson(`/api/${button.dataset.action}`, {
        node_id: Number(button.dataset.node),
      });
      toast(result.detail || "Saved.");
      await poll();
    } catch (error) {
      toast(error.message, true);
    } finally {
      if (!(button.dataset.action === "train" && state?.simulated)) {
        button.disabled = false;
      }
    }
  });
});

document.querySelectorAll("[data-scenario]").forEach((button) => {
  button.addEventListener("click", async () => {
    try {
      await postJson("/api/scenario", { scenario: button.dataset.scenario });
      toast(`Simulation: ${button.textContent}.`);
    } catch (error) {
      toast(error.message, true);
    }
  });
});

$("calibrationForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const values = Object.fromEntries(new FormData(event.currentTarget).entries());
  try {
    const result = await postJson("/api/calibration", values);
    toast(result.detail);
  } catch (error) {
    toast(error.message, true);
  }
});

function fillLiveAdc(field) {
  const adc = state?.nodes?.["1"]?.adc_raw;
  if (adc == null) {
    toast("No Node A slider ADC yet. Keep Node A powered near the receiver and twist the pot.", true);
    return;
  }
  const form = $("calibrationForm");
  if (form?.elements[field]) form.elements[field].value = adc;
  toast(`Copied live ADC ${adc} into ${field === "adc0" ? "point 1" : "point 2"}.`);
}

$("useLiveAdc0")?.addEventListener("click", () => fillLiveAdc("adc0"));
$("useLiveAdc1")?.addEventListener("click", () => fillLiveAdc("adc1"));

async function markInspectionDone(button) {
  if (button) button.disabled = true;
  try {
    const result = await postJson("/api/inspection-done", {});
    toast(result.detail || "Inspection done.");
    await poll();
  } catch (error) {
    toast(error.message, true);
    await poll();
  } finally {
    if (button) button.disabled = false;
  }
}

$("inspectionDone")?.addEventListener("click", (event) => {
  markInspectionDone(event.currentTarget);
});
$("inspectionDoneSidebar")?.addEventListener("click", (event) => {
  markInspectionDone(event.currentTarget);
});

window.addEventListener("resize", currentChart);
poll();
