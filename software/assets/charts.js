const COLORS = {
  a: "#c45c3e",
  b: "#3d7a78",
  grid: "#cfc3b3",
  text: "#5c534b",
  watch: "#c67a12",
  alert: "#c62828",
  bandA: "rgba(196,92,62,.14)",
  bandB: "rgba(61,122,120,.12)",
};

function usable(values) {
  return values.filter((v) => v !== null && v !== undefined && Number.isFinite(Number(v))).map(Number);
}

function path(ctx, points, x, y, color, dashed = false) {
  ctx.save();
  ctx.strokeStyle = color;
    ctx.lineWidth = dashed ? 2.2 : 3;
  ctx.setLineDash(dashed ? [7, 5] : []);
  ctx.beginPath();
  let started = false;
  points.forEach((value, index) => {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
      started = false;
      return;
    }
    const px = x(index);
    const py = y(Number(value));
    if (!started) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
    started = true;
  });
  ctx.stroke();
  ctx.restore();
}

function confidenceBand(ctx, lower, upper, x, y, color) {
  if (!lower?.length || lower.length !== upper?.length) return;
  ctx.save();
  ctx.fillStyle = color;
  ctx.beginPath();
  lower.forEach((v, i) => {
    const px = x(i);
    const py = y(v);
    if (i === 0) ctx.moveTo(px, py);
    else ctx.lineTo(px, py);
  });
  for (let i = upper.length - 1; i >= 0; i -= 1) {
    ctx.lineTo(x(i), y(upper[i]));
  }
  ctx.closePath();
  ctx.fill();
  ctx.restore();
}

export function drawForecastChart(canvas, {
  seriesA = [],
  seriesB = [],
  forecastA = null,
  forecastB = null,
  unit = "",
  watch = null,
  alert = null,
}) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const width = Math.max(420, Math.round(rect.width));
  const height = Math.max(220, Math.round(rect.height));
  canvas.width = Math.round(width * dpr);
  canvas.height = Math.round(height * dpr);
  const ctx = canvas.getContext("2d");
  ctx.scale(dpr, dpr);
  ctx.clearRect(0, 0, width, height);

  const left = 54, right = 16, top = 18, bottom = 38;
  const plotW = width - left - right;
  const plotH = height - top - bottom;
  const historyN = Math.max(seriesA.length, seriesB.length, 1);
  const futureN = Math.max(forecastA?.points?.length || 0, forecastB?.points?.length || 0);
  const totalN = historyN + futureN;
  const all = usable([
    ...seriesA, ...seriesB,
    ...(forecastA?.lower || []), ...(forecastA?.upper || []),
    ...(forecastB?.lower || []), ...(forecastB?.upper || []),
    watch, alert,
  ]);
    let min = all.length ? Math.min(...all) : 0;
  let max = all.length ? Math.max(...all) : 1;
  min = Math.min(0, min);
  if (alert != null && Number.isFinite(alert)) max = Math.max(max, Number(alert) * 1.35);
  if (max - min < 0.001) max = min + 1;
  const pad = (max - min) * 0.08;
  max += pad;

  const x = (i) => left + (plotW * i) / Math.max(totalN - 1, 1);
  const y = (v) => top + plotH - (plotH * (v - min)) / (max - min);

  ctx.font = "12px Segoe UI, sans-serif";
  ctx.textBaseline = "middle";
  ctx.strokeStyle = COLORS.grid;
  ctx.fillStyle = COLORS.text;
  for (let i = 0; i <= 4; i += 1) {
    const value = min + ((max - min) * i) / 4;
    const py = y(value);
    ctx.beginPath();
    ctx.moveTo(left, py);
    ctx.lineTo(width - right, py);
    ctx.stroke();
    ctx.textAlign = "right";
    ctx.fillText(`${value.toFixed(max < 0.1 ? 3 : 1)}${unit ? ` ${unit}` : ""}`, left - 8, py);
  }

  function threshold(value, color, label) {
    if (value === null || value === undefined) return;
    const py = y(value);
    ctx.save();
    ctx.strokeStyle = color;
    ctx.globalAlpha = 0.7;
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.moveTo(left, py);
    ctx.lineTo(width - right, py);
    ctx.stroke();
    ctx.fillStyle = color;
    ctx.textAlign = "left";
    ctx.fillText(label, left + 5, py - 9);
    ctx.restore();
  }
  threshold(watch, COLORS.watch, "WATCH");
  threshold(alert, COLORS.alert, "ALERT");

  const boundaryX = x(historyN - 1);
  if (futureN) {
    ctx.fillStyle = "rgba(61,122,120,.08)";
    ctx.fillRect(boundaryX, top, width - right - boundaryX, plotH);
    ctx.fillStyle = COLORS.text;
    ctx.textAlign = "left";
    ctx.fillText("forecast +30 s", boundaryX + 7, top + 11);
  }

  const a = seriesA.slice(-historyN);
  const b = seriesB.slice(-historyN);
  path(ctx, a, x, y, COLORS.a);
  path(ctx, b, x, y, COLORS.b);

  function drawFuture(history, forecast, color, bandColor) {
    if (!forecast?.points?.length || !history.length) return;
    const last = usable(history).at(-1);
    if (last === undefined) return;
    const fx = (i) => x(historyN - 1 + i);
    const lows = [last, ...(forecast.lower || [])];
    const highs = [last, ...(forecast.upper || [])];
    confidenceBand(ctx, lows, highs, fx, y, bandColor);
    path(ctx, [last, ...forecast.points], fx, y, color, true);
  }
  drawFuture(a, forecastA, COLORS.a, COLORS.bandA);
  drawFuture(b, forecastB, COLORS.b, COLORS.bandB);

  ctx.fillStyle = COLORS.text;
  ctx.textAlign = "left";
  ctx.fillText(`-${historyN - 1} s`, left, height - 15);
  ctx.textAlign = "center";
  ctx.fillText("now", boundaryX, height - 15);
  if (futureN) {
    ctx.textAlign = "right";
    ctx.fillText(`+${futureN} s`, width - right, height - 15);
  }
}
