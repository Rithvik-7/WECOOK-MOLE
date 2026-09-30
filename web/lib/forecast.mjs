// Shadow forecasts only. Operational alerts continue to come from the API.
export function predictChannel(history, channel, model) {
  const unavailable = (reason) => ({ available: false, reason, points: [] });
  if (channel === "ir")
    return unavailable("IR is a discrete input; no continuous forecast.");
  if (!model?.coefficients)
    return unavailable("Forecast model is loading or unavailable.");
  const rows = history.slice(-model.window);
  if (rows.length < model.window)
    return unavailable("Needs 20 consecutive one-second readings.");
  if (
    rows.some(
      (r) => r.valid === false || r.stale || !Number.isFinite(r[channel]),
    )
  )
    return unavailable(
      "Invalid, missing or stale readings in the forecast window.",
    );
  if (new Set(rows.map((r) => `${r.session_id}/${r.origin}`)).size > 1)
    return unavailable("A continuous session is required.");
  const stamps = rows.map((r) => Date.parse(r.sample_time));
  if (
    stamps.some((t) => !Number.isFinite(t)) ||
    stamps.some(
      (t, i) => i && (t - stamps[i - 1] < 800 || t - stamps[i - 1] > 1200),
    )
  )
    return unavailable(
      "Recorded cadence is too sparse. Use one-second telemetry or play the live demo.",
    );
  if (channel === "gas_raw" && !rows.at(-1).gas_ready)
    return unavailable("MQ-2 warm-up is incomplete.");
  const values = rows.map((r) => r[channel]),
    last = values.at(-1);
  const mean = values.reduce((a, b) => a + b, 0) / values.length;
  const scale = Math.max(
    0.01,
    Math.sqrt(values.reduce((a, b) => a + (b - mean) ** 2, 0) / values.length),
  );
  const features = [1, ...values.map((v) => (v - last) / scale)];
  const points = model.horizons_seconds.map((s, j) => {
    const estimate =
      last +
      features.reduce((sum, v, i) => sum + v * model.coefficients[i][j], 0) *
        scale;
    const radius = model.residual_radius[j] * scale;
    return {
      seconds: s,
      time: stamps.at(-1) + s * 1000,
      value: estimate,
      lower: estimate - radius,
      upper: estimate + radius,
    };
  });
  return {
    available: true,
    points,
    model: model.version,
    reason: "Synthetic-trained ridge · experimental, not a safety prediction",
  };
}

export function demoReading(id, t, start) {
  const wave = Math.sin(t / 24),
    slow = Math.sin(t / 57),
    base = { A: 0.35, B: 0.6, C: 0.28, D: 0.23 }[id] || 0.3;
  const tilt =
    base +
    (id === "B"
      ? 1.65 + 0.35 * slow + 0.12 * wave
      : 0.035 * wave + 0.012 * Math.sin(t / 5));
  const r = {
    sample_time: new Date(start + t * 1000).toISOString(),
    session_id: "browser-live-demo",
    sequence: t,
    origin: "simulated",
    valid: true,
    stale: false,
    tilt_deg: tilt,
    vibration: 0.2 + 0.05 * Math.sin(t / 12) + (id === "B" ? 0.25 : 0),
  };
  if (id === "A") r.potentiometer_raw = 415 + 4 * slow + Math.sin(t / 7);
  if (id === "C")
    Object.assign(r, {
      potentiometer_raw: 380 + 3 * slow,
      linear_raw: null,
      gas_raw: 240 + 8 * wave,
      gas_ready: true,
    });
  if (id === "D")
    Object.assign(r, {
      temperature_c: 27.4 + 0.16 * slow,
      humidity_pct: 61 + 0.6 * wave,
      pressure_hpa: 1008 + 0.3 * slow,
    });
  return r;
}
