import {
  $, fmt, getJson, postJson, setModeBanner, toast,
} from "/assets/common.js";

let connected = false;
let activeCommand = "stop";
let commandTimer = null;
let driveGeneration = 0;
let pollingTimer = null;

const keys = {
  w: "forward", ArrowUp: "forward",
  s: "backward", ArrowDown: "backward",
  a: "left", ArrowLeft: "left",
  d: "right", ArrowRight: "right",
};

function setPressed(command, pressed) {
  document.querySelectorAll("[data-drive]").forEach((button) => {
    button.classList.toggle("pressed", pressed && button.dataset.drive === command);
  });
}

async function send(command, quiet = false) {
  try {
    const result = await postJson(`/api/rover/${command}`);
    if (!quiet && result.simulated) toast(`Simulated rover: ${command.toUpperCase()}.`);
    return true;
  } catch (error) {
    if (!quiet) toast(error.message, true);
    return false;
  }
}

async function startDrive(command) {
  if (!connected) {
    toast("Rover is not connected. Join Mine-Rover-AP first.", true);
    return;
  }
  if (activeCommand === command) return;
  await stopDrive(true);
  activeCommand = command;
  const generation = ++driveGeneration;
  setPressed(command, true);
  $("controlMessage").textContent = `Holding ${command.toUpperCase()}. Release to STOP.`;
  const pulse = async () => {
    if (generation !== driveGeneration || activeCommand !== command) return;
    await send(command, true);
    if (generation === driveGeneration && activeCommand === command) {
      commandTimer = setTimeout(pulse, 170);
    }
  };
  pulse();
}

async function stopDrive(quiet = false) {
  driveGeneration += 1;
  clearTimeout(commandTimer);
  commandTimer = null;
  const wasMoving = activeCommand !== "stop";
  setPressed(activeCommand, false);
  activeCommand = "stop";
  $("controlMessage").textContent = "STOP command active.";
  if (wasMoving || !quiet) {
    await send("stop", quiet);
    // A second STOP wins over any already in-flight direction request.
    setTimeout(() => send("stop", true), 220);
  }
}

function render(state) {
  setModeBanner(state.simulated);
  const wrapper = state.rover || {};
  const data = wrapper.data || {};
  connected = Boolean(wrapper.ok);

  const roverBadge = $("roverBadge");
  roverBadge.className = `badge ${connected ? "NORMAL" : "UNKNOWN"}`;
  roverBadge.textContent = connected ? "Connected" : "Not connected";
  $("roverLink").textContent = connected
    ? (state.simulated ? "Simulation ready" : "Mine-Rover-AP ready")
    : "Rover unavailable";
  $("commandState").textContent = String(data.command || state.last_command || "stop").toUpperCase();
  const summary = $("roverSummary");
  if (summary) {
    summary.className = `summary ${
      data.ir_obstacle === true ? "ALERT" : connected ? "NORMAL" : "UNKNOWN"
    }`;
  }
  $("summaryDistance").textContent = `${fmt(data.distance_cm, 1)} cm`;
  $("summaryObstacle").textContent = data.ir_obstacle === true ? "Flagged" :
    data.ir_obstacle === false ? "Clear" : "Unknown";
  $("summaryObstacle").style.color = data.ir_obstacle === true ? "#c62828" : "";
  const wrap = $("distanceWrap");
  if (wrap) wrap.classList.toggle("tight", Number(data.distance_cm) < 25);
  const roverError = $("roverError");
  if (roverError) {
    roverError.textContent = connected
      ? (state.simulated ? "Simulation only — no motor command is leaving this laptop." : "")
      : (wrapper.error || "Join Wi-Fi Mine-Rover-AP, then keep this page open.");
  }

  $("distance").textContent = fmt(data.distance_cm, 1);
  const ir = data.ir || {};
  const irBadge = $("irBadge");
  const irFlagged = data.ir_obstacle === true;
  irBadge.className = `badge ${
    irFlagged ? "ALERT" : data.ir_obstacle === false ? "NORMAL" : "UNKNOWN"
  }`;
  irBadge.textContent =
    irFlagged ? "Flagged" : data.ir_obstacle === false ? "Clear" : "Unknown";
  const irCard = $("irCard");
  if (irCard) {
    irCard.classList.toggle("tone-ALERT", ir.agreement === "ir_only" || ir.agreement === "agree_near");
    irCard.classList.toggle("tone-WATCH", ir.agreement === "sonar_only" || ir.agreement === "ir_near_band");
  }
  const irHeadline = $("irHeadline");
  if (irHeadline) irHeadline.textContent = ir.headline || "Waiting for rover telemetry.";
  const irAdvice = $("irAdvice");
  if (irAdvice) {
    const extra = ir.sim_note && state.simulated ? ` ${ir.sim_note}` : "";
    irAdvice.textContent = `${ir.advice || ""}${extra}`.trim();
  }
  const irDrive = $("irDriveNote");
  if (irDrive) {
    const note = ir.drive_note || "";
    irDrive.hidden = !note;
    irDrive.textContent = note;
  }
  $("mq7Raw").textContent = data.mq7_raw ?? "—";
  $("mq7Level").textContent = data.mq7_level || "—";
  $("roverRoll").textContent = `${fmt(data.roll_deg)}°`;
  $("roverPitch").textContent = `${fmt(data.pitch_deg)}°`;
  $("roverVibration").textContent = `${fmt(data.vibration_g, 4)} g`;
  $("roverSeq").textContent = data.seq ?? "—";

  const driveBadge = $("driveBadge");
  const moving = Boolean(data.driving);
  driveBadge.className = `badge ${moving ? "WATCH" : connected ? "NORMAL" : "UNKNOWN"}`;
  driveBadge.textContent = moving ? "Moving" : connected ? "Stopped" : "Unavailable";
  if (activeCommand === "stop") {
    $("controlMessage").textContent = connected
      ? "Ready. Hold a direction button or use W/A/S/D. Release sends STOP."
      : "Waiting for rover connection. STOP remains available.";
  }
  document.querySelectorAll("[data-drive]:not([data-drive='stop'])").forEach((button) => {
    button.disabled = !connected;
  });
  if (!connected && activeCommand !== "stop") stopDrive(true);
  const clock = $("liveClock");
  if (clock) clock.textContent = new Date().toLocaleTimeString();
}

async function poll() {
  try {
    render(await getJson("/api/rover/state"));
  } catch (error) {
    connected = false;
    $("roverLink").textContent = "Backend offline";
    $("controlMessage").textContent = error.message;
  } finally {
    clearTimeout(pollingTimer);
    pollingTimer = setTimeout(poll, 500);
  }
}

document.querySelectorAll("[data-drive]").forEach((button) => {
  const command = button.dataset.drive;
  if (command === "stop") {
    button.addEventListener("click", () => stopDrive());
    return;
  }
  button.addEventListener("pointerdown", (event) => {
    event.preventDefault();
    button.setPointerCapture?.(event.pointerId);
    startDrive(command);
  });
  ["pointerup", "pointercancel", "lostpointercapture"].forEach((eventName) => {
    button.addEventListener(eventName, () => stopDrive(true));
  });
});

document.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement) return;
  if (event.target instanceof HTMLTextAreaElement) return;
  if (event.target.closest?.("#moleHelper")) return;
  if (event.code === "Space") {
    event.preventDefault();
    stopDrive();
    return;
  }
  const command = keys[event.key];
  if (command && !event.repeat) {
    event.preventDefault();
    startDrive(command);
  }
});

document.addEventListener("keyup", (event) => {
  if (event.target instanceof HTMLInputElement) return;
  if (event.target instanceof HTMLTextAreaElement) return;
  if (event.target.closest?.("#moleHelper")) return;
  if (keys[event.key]) {
    event.preventDefault();
    stopDrive(true);
  }
});

window.addEventListener("blur", () => stopDrive(true));
document.addEventListener("visibilitychange", () => {
  if (document.hidden) stopDrive(true);
});
window.addEventListener("beforeunload", () => {
  navigator.sendBeacon("/api/rover/stop");
});

$("inspectionDone")?.addEventListener("click", async (event) => {
  const button = event.currentTarget;
  button.disabled = true;
  try {
    await stopDrive(true);
    const result = await postJson("/api/inspection-done", {});
    toast(result.detail || "Inspection done.");
    window.location.href = "/monitoring";
  } catch (error) {
    toast(error.message, true);
    button.disabled = false;
  }
});

poll();
