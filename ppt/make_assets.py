"""Generate labelled PNG diagrams for the SIH MOLE deck. Text is drawn in Pillow so it stays readable."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:\Users\brith\Desktop\mole\ppt\assets")
OUT.mkdir(parents=True, exist_ok=True)

NAVY = (31, 73, 125)
NAVY_DARK = (20, 48, 84)
ORANGE = (247, 150, 70)
BLUE = (79, 129, 189)
TEAL = (75, 172, 198)
GREEN = (86, 150, 90)
RED = (192, 80, 77)
WHITE = (255, 255, 255)
OFF = (248, 250, 252)
INK = (28, 35, 45)
MUTED = (90, 100, 112)
LINE = (210, 218, 228)


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def centre(draw, xy, text, fnt, fill=WHITE):
    x0, y0, x1, y1 = xy
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - 1), text, font=fnt, fill=fill)


def wrap_centre(draw, xy, text, fnt, fill=WHITE, gap=4):
    x0, y0, x1, y1 = xy
    words = text.split()
    lines, cur = [], ""
    max_w = x1 - x0 - 16
    for w in words:
        trial = (cur + " " + w).strip()
        if draw.textbbox((0, 0), trial, font=fnt)[2] <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    total = sum(draw.textbbox((0, 0), ln, font=fnt)[3] for ln in lines) + gap * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for ln in lines:
        bbox = draw.textbbox((0, 0), ln, font=fnt)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
        draw.text((x0 + (x1 - x0 - tw) / 2, y), ln, font=fnt, fill=fill)
        y += th + gap


def save(img, name):
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print("wrote", path)
    return path


def workflow():
    w, h = 1600, 280
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    steps = [
        (NAVY, "Node A + B", "Continuous monitoring"),
        (BLUE, "Rules + AI", "Anomaly detection — not collapse %"),
        (ORANGE, "Dashboard", "Evidence and warning"),
        (NAVY_DARK, "Operator", "Decide to inspect"),
        (TEAL, "Rover", "Secondary inspection"),
    ]
    box_w, box_h, gap = 250, 168, 28
    total = 5 * box_w + 4 * (gap + 36)
    x = (w - total) / 2
    y = 46
    f_title, f_sub = font(22, True), font(16)
    for i, (color, title, sub) in enumerate(steps):
        rounded(d, (x, y, x + box_w, y + box_h), 18, color)
        centre(d, (x, y + 18, x + box_w, y + 70), title, f_title, WHITE)
        wrap_centre(d, (x + 10, y + 70, x + box_w - 10, y + box_h - 12), sub.replace("\n", " "), f_sub, WHITE)
        if i < 4:
            ax = x + box_w + 6
            ay = y + box_h / 2
            d.polygon([(ax, ay - 10), (ax + 28, ay), (ax, ay + 10)], fill=ORANGE)
        x += box_w + gap + 36
    d.text((40, 10), "Early anomaly detection is the precursor stage toward prediction. Isolation Forest does not output a collapse probability.", font=font(18, True), fill=NAVY)
    return save(img, "workflow.png")


def architecture():
    w, h = 1400, 780
    img = Image.new("RGB", (w, h), OFF)
    d = ImageDraw.Draw(img)
    layers = [
        ("1  FIELD HARDWARE", NAVY, [
            ("NODE A", "ESP32-WROOM-32\nMPU6050 tilt"),
            ("NODE B", "ESP32-WROOM-32\nMPU6050 vibration"),
            ("ROVER", "Motors + driver\nremote inspect"),
        ]),
        ("2  COMMUNICATION", BLUE, [
            ("ESP-NOW", "Surface nodes A/B\nto USB gateway"),
            ("GATEWAY", "ESP32 USB\ninfrastructure"),
            ("ROVER LINK", "Separate path\nnot node radio"),
        ]),
        ("3  LAPTOP PROCESSING", ORANGE, [
            ("PYTHON", "Local dashboard\nbaseline delta"),
            ("SQLITE", "Event history\non the laptop"),
            ("AI + RULES", "Isolation Forest\nanomaly, not forecast"),
        ]),
        ("4  OPERATOR INTERFACE", TEAL, [
            ("STATUS", "N / W / A\nUnknown"),
            ("EVIDENCE", "Charts, reason\nevent history"),
            ("CONTROL", "Rover pad\nacknowledge"),
        ]),
    ]
    d.text((36, 18), "Technical architecture  ·  four layers, one dashboard", font=font(32, True), fill=NAVY)
    d.text((36, 56), "Gateway is not a fourth monitoring node. Rover vibration is never treated as Node B.", font=font(20), fill=MUTED)
    top = 96
    for li, (label, color, cards) in enumerate(layers):
        y = top + li * 165
        rounded(d, (28, y, w - 28, y + 150), 16, WHITE, LINE, 2)
        d.rectangle((28, y, 18 + 28, y + 150), fill=color)
        # rotate-like side label
        d.text((56, y + 16), label, font=font(22, True), fill=color)
        cw = 380
        gap = 24
        start = 70
        for ci, (t, s) in enumerate(cards):
            cx = start + ci * (cw + gap)
            rounded(d, (cx, y + 48, cx + cw, y + 132), 12, color)
            centre(d, (cx, y + 52, cx + cw, y + 86), t, font(22, True), WHITE)
            wrap_centre(d, (cx + 8, y + 84, cx + cw - 8, y + 128), s.replace("\n", " · "), font(18), WHITE)
    return save(img, "architecture.png")


def process():
    w, h = 1500, 220
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    steps = [
        "1  Usable data?",
        "2  Baseline delta",
        "3  Persist over time",
        "4  Rules + AI",
        "5  Show & inspect",
    ]
    notes = [
        "Fresh, valid, calibrated",
        "Tilt / vibration / gap",
        "Not one noisy sample",
        "Never let AI clear a rule",
        "Reason + rover evidence",
    ]
    n = 5
    box_w = 250
    gap = 30
    x = (w - (n * box_w + (n - 1) * gap)) / 2
    for i, (t, nte) in enumerate(zip(steps, notes)):
        rounded(d, (x, 36, x + box_w, 184), 14, NAVY if i < 3 else ORANGE)
        wrap_centre(d, (x + 8, 48, x + box_w - 8, 110), t, font(20, True), WHITE)
        wrap_centre(d, (x + 10, 108, x + box_w - 10, 170), nte, font(15), WHITE)
        if i < n - 1:
            d.polygon(
                [(x + box_w + 4, 110), (x + box_w + 24, 120), (x + box_w + 4, 130)],
                fill=ORANGE,
            )
        x += box_w + gap
    d.text((40, 8), "Implementation method  ·  each accepted node report  ·  firmware design 1 Hz", font=font(18, True), fill=NAVY)
    return save(img, "process.png")


def dashboard():
    w, h = 1400, 780
    img = Image.new("RGB", (w, h), (18, 28, 42))
    d = ImageDraw.Draw(img)
    rounded(d, (16, 16, w - 16, h - 16), 18, (28, 40, 58))
    d.rectangle((16, 16, w - 16, 78), fill=NAVY)
    d.text((36, 28), "MOLE dashboard  ·  interface concept  ·  not a live mine feed", font=font(28, True), fill=WHITE)
    d.text((1088, 34), "ILLUSTRATIVE UI", font=font(20, True), fill=ORANGE)

    cards = [
        (36, 98, "NODE A", "Tilt from baseline", "WATCH", ORANGE, "Persistent change"),
        (430, 98, "NODE B", "Vibration RMS", "NORMAL", GREEN, "Near baseline"),
        (824, 98, "ROVER", "Inspection unit", "READY", TEAL, "Idle until requested"),
    ]
    watch_badge = None
    for x, y, title, sub, status, col, val in cards:
        rounded(d, (x, y, x + 370, y + 150), 14, (36, 50, 70))
        d.text((x + 18, y + 16), title, font=font(26, True), fill=WHITE)
        d.text((x + 18, y + 54), sub, font=font(18), fill=(180, 190, 200))
        badge = (x + 200, y + 14, x + 350, y + 62)
        rounded(d, badge, 12, col)
        centre(d, badge, status, font(20, True), WHITE)
        d.text((x + 18, y + 100), val, font=font(24, True), fill=WHITE)
        if status == "WATCH":
            watch_badge = badge

    bx0, by0, bx1, by1 = watch_badge
    mid = (bx0 + bx1) / 2
    d.line((mid, by1, mid, 268), fill=ORANGE, width=6)
    d.polygon([(mid - 12, 268), (mid + 12, 268), (mid, 286)], fill=ORANGE)
    rounded(d, (36, 282, 1364, 348), 12, ORANGE)
    d.text((56, 298), "Stale/missing telemetry  →  UNKNOWN, never false NORMAL.", font=font(26, True), fill=WHITE)

    rounded(d, (36, 368, 780, 752), 14, (36, 50, 70))
    d.text((56, 388), "Status + evidence panels", font=font(24, True), fill=WHITE)
    d.text((56, 432), "Node A  WATCH   ·   Node B  NORMAL", font=font(22), fill=ORANGE)
    d.text((56, 478), "3 consecutive samples above Watch", font=font(22), fill=WHITE)
    d.text((56, 524), "Rover idle until the operator decides", font=font(22), fill=WHITE)
    d.text((56, 570), "Acknowledge does not erase the event", font=font(22), fill=WHITE)
    d.text((56, 640), "Green means healthy data.", font=font(22, True), fill=GREEN)
    d.text((56, 686), "It does not mean a certified-safe mine.", font=font(22, True), fill=WHITE)

    rounded(d, (804, 368, 1364, 752), 14, (36, 50, 70))
    d.text((824, 388), "Why this warning", font=font(24, True), fill=WHITE)
    reasons = [
        "Persistent tilt at Node A",
        "Rule latch, not a one-off tap",
        "Node B still near baseline",
        "Local change, not whole table",
        "Rover = secondary inspection",
    ]
    yy = 440
    for r in reasons:
        rounded(d, (824, yy, 1344, yy + 50), 8, (48, 64, 86))
        d.text((844, yy + 12), r, font=font(20), fill=WHITE)
        yy += 58
    return save(img, "dashboard.png")


def scale_path():
    w, h = 1100, 470
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    stages = [
        (NAVY, "NOW", "Tabletop nodes + rover + local dashboard"),
        (BLUE, "NEXT", "More calibrated nodes + spatial visualization + extended validation"),
        (
            ORANGE,
            "FIELD",
            "Surveyed mounts, site-calibrated thresholds, DGMS-approved/certified sensing and communications, mine monitoring integration",
        ),
    ]
    d.text((20, 12), "Future path  ·  prototype ≠ field system", font=font(18, True), fill=NAVY)
    y = 48
    for i, (c, t, s) in enumerate(stages):
        rounded(d, (20, y, 1080, y + 118), 14, c)
        d.text((40, y + 14), t, font=font(18, True), fill=WHITE)
        wrap_centre(d, (36, y + 44, 1064, y + 108), s, font(16), WHITE)
        y += 132
    return save(img, "scale.png")


def ps_checks():
    w, h = 1500, 150
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    items = [
        ("Monitor", "Node A tilt + Node B vibration, continuous"),
        ("Anomaly", "Anomaly detection — not collapse %"),
        ("Warn", "Watch / Alert latch + written reason"),
        ("Low cost", "ESP32-class tabletop hardware"),
        ("Inspect", "Rover is secondary, after operator"),
    ]
    d.text((20, 8), "SIH26025 mapping  ·  what the prototype actually does", font=font(18, True), fill=NAVY)
    bw = 278
    x = 16
    for title, sub in items:
        rounded(d, (x, 40, x + bw, 140), 12, NAVY)
        d.ellipse((x + 12, 52, x + 36, 76), fill=ORANGE)
        d.line((x + 18, 64, x + 23, 70), fill=WHITE, width=3)
        d.line((x + 23, 70, x + 32, 56), fill=WHITE, width=3)
        d.text((x + 44, 50), title, font=font(18, True), fill=WHITE)
        wrap_centre(d, (x + 8, 78, x + bw - 8, 132), sub, font(15), WHITE)
        x += bw + 16
    return save(img, "ps_checks.png")


def science_bar():
    w, h = 1500, 140
    img = Image.new("RGB", (w, h), OFF)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 8, w - 8, h - 8), 12, WHITE, LINE, 2)
    d.rectangle((8, 8, 22, h - 8), fill=ORANGE)
    d.text((36, 14), "Scientific basis  ·  low-cost proxy, not a geophone array", font=font(20, True), fill=NAVY)
    d.text(
        (36, 44),
        "MPU6050 tilt/vibration measure mounting-surface micro-movement. They are not equivalent to professional microseismic/geophone systems.",
        font=font(16),
        fill=INK,
    )
    d.text(
        (36, 72),
        "Published mining research: strata movement and microseismic event-rate changes can precede roof/ground failure (Sivakumar et al., 2005, Rajendra/SECL).",
        font=font(16),
        fill=INK,
    )
    d.text(
        (36, 100),
        "DGMS (S&T) Tech. Circular 01 of 2017, cl. 6.1: longwall strata plans use surface geophones. That is the field-grade method — not this tabletop prototype.",
        font=font(16),
        fill=INK,
    )
    return save(img, "science_bar.png")


def metrics_row():
    w, h = 1500, 168
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    cards = [
        ("Node report rate", "1 Hz", "Firmware design — not a field-measured IMU rate"),
        ("Sensor → dashboard latency", "TBD", "TBD – validation test pending"),
        ("Node → gateway range", "TBD", "TBD – validation test pending  ·  not through rock"),
        ("Prototype BOM", "₹4,000", "Node+gateway kit ceiling  ·  rover owned/borrowed  ·  full 3-unit total TBD"),
    ]
    d.text((16, 6), "Prototype metrics  ·  measured, sourced, or labelled TBD  ·  no theoretical underground range", font=font(15, True), fill=NAVY)
    bw = 354
    x = 16
    for title, val, note in cards:
        rounded(d, (x, 34, x + bw, 160), 12, NAVY)
        wrap_centre(d, (x + 8, 40, x + bw - 8, 72), title, font(14, True), ORANGE)
        centre(d, (x, 68, x + bw, 116), val, font(28, True), WHITE)
        wrap_centre(d, (x + 8, 114, x + bw - 8, 154), note, font(15), WHITE)
        x += bw + 16
    return save(img, "metrics_row.png")


def comms_callout():
    w, h = 1500, 100
    img = Image.new("RGB", (w, h), OFF)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 8, 730, 92), 12, NAVY)
    d.text((24, 18), "PROTOTYPE comms", font=font(15, True), fill=ORANGE)
    d.text((24, 44), "Surface nodes: ESP-NOW → USB gateway. Rover: separate control path.", font=font(14), fill=WHITE)
    d.text((24, 66), "Not claimed: underground Wi-Fi/ESP-NOW range through rock.", font=font(13), fill=WHITE)
    rounded(d, (760, 8, 1492, 92), 12, BLUE)
    d.text((776, 18), "FIELD comms  (after RF survey)", font=font(15, True), fill=WHITE)
    d.text((776, 44), "Select architecture on site: LoRa / mesh / repeater / leaky-feeder", font=font(14), fill=WHITE)
    d.text((776, 66), "or mine-approved infrastructure. Future work — not this demo.", font=font(13), fill=WHITE)
    return save(img, "comms_callout.png")


def tilt_chart():
    w, h = 1100, 520
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 8, w - 8, h - 8), 14, OFF, LINE, 2)
    d.text((28, 18), "Tabletop tilt vs time", font=font(20, True), fill=NAVY)
    d.text((28, 48), "ILLUSTRATIVE — replace with test-run data before judging", font=font(16, True), fill=RED)
    ax, ay, bx, by = 90, 90, 1040, 430
    d.rectangle((ax, ay, bx, by), fill=WHITE, outline=LINE, width=2)
    # threshold lines: watch 3 deg, alert 6 deg on 0-8 scale
    def y_of(deg):
        return by - (by - ay - 10) * (deg / 8.0)

    yw, ya = y_of(3), y_of(6)
    d.line((ax, yw, bx, yw), fill=ORANGE, width=2)
    d.line((ax, ya, bx, ya), fill=RED, width=2)
    d.text((ax + 8, yw - 22), "Watch rule  3°  (demo threshold)", font=font(13, True), fill=ORANGE)
    d.text((ax + 8, ya - 22), "Alert rule  6°  (demo threshold)", font=font(13, True), fill=RED)
    # illustrative series: stays low, then rises through watch
    pts = [(0, 0.4), (8, 0.5), (16, 0.3), (24, 0.6), (32, 2.2), (40, 3.4), (48, 3.8), (56, 4.1), (64, 3.9)]
    mapped = []
    for i, (t, deg) in enumerate(pts):
        mx = ax + (bx - ax) * (t / 64)
        my = y_of(deg)
        mapped.append((mx, my))
    d.line(mapped, fill=NAVY, width=4)
    for p in mapped:
        d.ellipse((p[0] - 5, p[1] - 5, p[0] + 5, p[1] + 5), fill=NAVY)
    # mark watch event at t=40
    wx, wy = mapped[5]
    d.ellipse((wx - 10, wy - 10, wx + 10, wy + 10), outline=ORANGE, width=3)
    d.text((wx + 12, wy - 28), "Watch marked", font=font(13, True), fill=ORANGE)
    d.text((ax, by + 12), "Time  →", font=font(14), fill=MUTED)
    d.text((16, 240), "Tilt from", font=font(13), fill=MUTED)
    d.text((16, 258), "baseline (°)", font=font(13), fill=MUTED)
    d.text((28, 470), "Not experimental evidence. Swap for CSV from a calibrated live run.", font=font(13), fill=MUTED)
    return save(img, "tilt_chart.png")


if __name__ == "__main__":
    workflow()
    architecture()
    process()
    dashboard()
    scale_path()
    ps_checks()
    science_bar()
    metrics_row()
    comms_callout()
    tilt_chart()
