"""Simple 2-page A4 summary: hardware, software, ML, flowchart."""
from __future__ import annotations

import shutil
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\brith\Desktop\mole")
PITCH = ROOT / "pitch"
ASSETS = PITCH / "assets"
OUT_PDF = PITCH / "SIH26025_WE_COOK_MOLE_2page_summary.pdf"
PREVIEW = PITCH / "summary_preview"
DOWNLOADS = Path.home() / "Downloads"

# A4 at 200 dpi — readable print, exact 2 pages
W, H = 1654, 2339
M = 64

NAVY = (11, 44, 74)
NAVY2 = (15, 58, 98)
ORANGE = (244, 123, 32)
TEAL = (14, 124, 123)
GOLD = (196, 138, 18)
WHITE = (255, 255, 255)
INK = (26, 26, 26)
MUTED = (74, 85, 99)
PALE = (244, 247, 250)
PALE_TEAL = (232, 244, 244)
PALE_ORANGE = (255, 244, 232)
LINE = (213, 222, 232)
RED = (122, 31, 20)


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def rounded(d, box, r, fill, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def text_w(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[2] - b[0]


def text_h(d, text, fnt):
    b = d.textbbox((0, 0), text, font=fnt)
    return b[3] - b[1]


def wrap(d, text, fnt, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if text_w(d, trial, fnt) <= max_w:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def draw_wrapped(d, x, y, text, fnt, fill, max_w, line_gap=6):
    lines = wrap(d, text, fnt, max_w)
    yy = y
    for line in lines:
        d.text((x, yy), line, font=fnt, fill=fill)
        yy += text_h(d, line, fnt) + line_gap
    return yy


def centre(d, box, text, fnt, fill):
    x0, y0, x1, y1 = box
    tw, th = text_w(d, text, fnt), text_h(d, text, fnt)
    d.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - 2), text, font=fnt, fill=fill)


def arrow_right(d, x, y, color=ORANGE, size=16):
    d.polygon([(x, y - size), (x + size + 4, y), (x, y + size)], fill=color)


def header(d, page_title, page_no):
    d.rectangle((0, 0, 22, H), fill=ORANGE)
    d.rectangle((0, 0, W, 118), fill=NAVY)
    d.text((M, 18), "SMART INDIA HACKATHON 2026  ·  SIH26025", font=font(22, True), fill=ORANGE)
    d.text((M, 50), "MOLE", font=font(48, True), fill=WHITE)
    d.text((M + 210, 62), "Mine Observation & Live-alert Engine", font=font(26, True), fill=WHITE)
    right = f"{page_title}   ·   Team WE COOK   ·   {page_no} / 2"
    d.text((W - M - text_w(d, right, font(20, True)), 70), right, font=font(20, True), fill=(210, 220, 230))


def footer(d):
    d.rectangle((0, H - 56, W, H), fill=NAVY)
    t = "Tabletop demonstration  ·  not a certified mine  ·  Ministry of Coal  ·  Hardware  ·  Disaster Management"
    centre(d, (0, H - 56, W, H), t, font(18, True), WHITE)


def section(d, x, y, title, accent=ORANGE):
    d.rectangle((x, y + 8, x + 10, y + 34), fill=accent)
    d.text((x + 22, y), title, font=font(30, True), fill=NAVY)
    return y + 48


def hw_card(d, box, kicker, title, lines, fill):
    x0, y0, x1, y1 = box
    rounded(d, box, 18, fill)
    d.text((x0 + 22, y0 + 16), kicker, font=font(16, True), fill=(255, 255, 255, 220) if True else WHITE)
    d.text((x0 + 22, y0 + 40), title, font=font(26, True), fill=WHITE)
    yy = y0 + 84
    f = font(18)
    for line in lines:
        d.ellipse((x0 + 24, yy + 8, x0 + 36, yy + 20), fill=WHITE)
        d.text((x0 + 46, yy), line, font=f, fill=WHITE)
        yy += 32


def flow_box(d, box, title, sub, fill):
    rounded(d, box, 16, fill)
    x0, y0, x1, y1 = box
    d.text((x0 + 16, y0 + 14), title, font=font(20, True), fill=WHITE)
    draw_wrapped(d, x0 + 16, y0 + 46, sub, font(16), (230, 236, 242), x1 - x0 - 32, 3)


def page1() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    header(d, "What we built", "1")
    footer(d)

    y = 140
    rounded(d, (M, y, W - M, y + 118), 16, PALE)
    d.text((M + 24, y + 16), "One product, in one sentence", font=font(18, True), fill=ORANGE)
    draw_wrapped(
        d,
        M + 24,
        y + 48,
        "Two fixed nodes watch a tabletop model. The laptop warns from rules and machine learning. "
        "Then an officer can drive a rover to look — because a warning appeared. Readings show disturbance. They do not prove a collapse.",
        font(22),
        INK,
        W - 2 * M - 48,
        6,
    )

    y = 278
    jobs = [
        (NAVY, "1  MONITOR", "Node A + Node B keep watching"),
        (ORANGE, "2  WARN + PREDICT", "Rules latch  ·  Isolation Forest  ·  30 s forecast"),
        (TEAL, "3  INSPECT", "Remote rover after the officer decides"),
    ]
    gap = 18
    bw = (W - 2 * M - 2 * gap) / 3
    for i, (col, title, sub) in enumerate(jobs):
        x = M + i * (bw + gap)
        rounded(d, (x, y, x + bw, y + 110), 16, col)
        d.text((x + 18, y + 18), title, font=font(24, True), fill=WHITE)
        draw_wrapped(d, x + 18, y + 58, sub, font(18), WHITE, bw - 36, 4)
        if i < 2:
            arrow_right(d, x + bw + 1, y + 55, ORANGE, 12)

    y = section(d, M, 418, "Flowchart  —  two radios on purpose", ORANGE)

    # Monitor lane
    rounded(d, (M, y, W - M, y + 268), 20, PALE)
    d.rectangle((M, y, M + 14, y + 268), fill=NAVY)
    d.text((M + 32, y + 12), "MONITOR PATH   ·   ESP-NOW channel 1   ·   USB into the laptop", font=font(18, True), fill=NAVY)

    boxes = [
        (NAVY, "Node A", "MPU6050 + crack slider"),
        (NAVY, "Node B", "MPU6050 compare only"),
        (NAVY2, "S3-Zero USB", "ESP-NOW → JSON 115200"),
        (GOLD, "Laptop", "Rules + IF + 30 s forecast"),
        (NAVY, "Dashboard", "Reason · score · MAE"),
    ]
    inner = W - 2 * M - 48
    bgap = 12
    bw = (inner - 4 * bgap - 4 * 22) / 5
    by0 = y + 52
    bh = 188
    x = M + 32
    for i, (col, title, sub) in enumerate(boxes):
        flow_box(d, (x, by0, x + bw, by0 + bh), title, sub, col)
        if i < 4:
            arrow_right(d, x + bw + 2, by0 + bh / 2, ORANGE, 11)
        x += bw + bgap + 22

    y = y + 286
    rounded(d, (M, y, W - M, y + 200), 20, PALE_TEAL)
    d.rectangle((M, y, M + 14, y + 200), fill=TEAL)
    d.text((M + 32, y + 12), "INSPECT PATH   ·   separate Wi-Fi AP Mine-Rover-AP   ·   not on the USB radio", font=font(18, True), fill=TEAL)

    iboxes = [
        (TEAL, "Sees a warning", "WATCH or ALERT on monitoring"),
        (TEAL, "Decides to look", "Opens the rover page"),
        (NAVY2, "Rover ESP32", "Hold to move · release = STOP"),
        (TEAL, "Inspect sensors", "cm · IR flag · MQ-7 raw"),
    ]
    inner = W - 2 * M - 48
    bgap = 16
    bw = (inner - 3 * bgap - 3 * 22) / 4
    by0 = y + 48
    bh = 132
    x = M + 32
    for i, (col, title, sub) in enumerate(iboxes):
        flow_box(d, (x, by0, x + bw, by0 + bh), title, sub, col)
        if i < 3:
            arrow_right(d, x + bw + 2, by0 + bh / 2, ORANGE, 11)
        x += bw + bgap + 22

    y = section(d, M, 1008, "Hardware we built  —  four boards", TEAL)

    cards = [
        (NAVY, "FIXED NODE", "Node A", ["Classic ESP32-WROOM-32", "MPU6050 on GPIO 21 / 22", "Crack slider on GPIO 34", "NODE_ID 1"]),
        (NAVY2, "FIXED NODE", "Node B", ["Same ESP32 + MPU6050", "No slider — comparison", "Not a surveyed reference", "NODE_ID 2"]),
        (GOLD, "RECEIVER", "S3-Zero", ["Waveshare ESP32-S3-Zero", "ESP-NOW → USB-C JSON", "No sensors on this board", "115200 baud"]),
        (TEAL, "MOBILE", "Rover", ["Classic ESP32 + L298N", "HC-SR04, IR, MQ-7 raw", "Own Wi-Fi: Mine-Rover-AP", "Remote drive — not autonomous"]),
    ]
    gap = 18
    cw = (W - 2 * M - gap) / 2
    ch = 248
    for i, (col, kicker, title, lines) in enumerate(cards):
        col_i, row = i % 2, i // 2
        x = M + col_i * (cw + gap)
        yy = y + row * (ch + gap)
        hw_card(d, (x, yy, x + cw, yy + ch), kicker, title, lines, col)

    y = 1008 + 48 + 2 * 248 + 18 + 18
    rounded(d, (M, y, W - M, y + 78), 14, PALE_ORANGE)
    d.text((M + 22, y + 12), "Simple split", font=font(20, True), fill=ORANGE)
    draw_wrapped(
        d,
        M + 22,
        y + 42,
        "ESP32 boards measure and send. The laptop calibrates, stores, runs rules and ML, and draws the website. Rover driving is remote, not autonomous.",
        font(20),
        INK,
        W - 2 * M - 44,
        4,
    )

    y = section(d, M, y + 96, "How we show it on the table", TEAL)
    demo = [
        (TEAL, "1  Still", "Both nodes quiet"),
        (NAVY, "2  Tilt A", "Keep Node B quieter"),
        (ORANGE, "3  Warn", "WATCH then ALERT"),
        (GOLD, "4  Drive", "Open rover page"),
        (NAVY2, "5  Keep", "History still lists it"),
    ]
    gap = 16
    dw = (W - 2 * M - 4 * gap - 4 * 20) / 5
    dh = 150
    x = M
    for i, (col, title, sub) in enumerate(demo):
        rounded(d, (x, y, x + dw, y + dh), 16, col)
        d.text((x + 16, y + 22), title, font=font(22, True), fill=WHITE)
        draw_wrapped(d, x + 16, y + 70, sub, font(18), WHITE, dw - 32, 4)
        if i < 4:
            arrow_right(d, x + dw + 2, y + dh / 2, ORANGE, 11)
        x += dw + gap + 20
    return img


def page2() -> Image.Image:
    img = Image.new("RGB", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    header(d, "Software + ML", "2")
    footer(d)

    y = section(d, M, 140, "Software we built  —  one local website", ORANGE)

    left = (M, y, M + 760, y + 430)
    right = (M + 778, y, W - M, y + 430)
    rounded(d, left, 18, PALE)
    rounded(d, right, 18, PALE)

    d.text((M + 24, y + 16), "Laptop stack", font=font(24, True), fill=NAVY)
    stack = [
        "Python + Flask  ·  no login, no cloud",
        "SQLite history + CSV export",
        "Pages: /monitoring  and  /rover",
        "Simulate = labelled rehearsal",
        "Live USB never silently fakes data",
        "If USB drops → UNKNOWN, not green",
        "Run: python app.py --mode simulate",
        "Live: python app.py --mode live --serial auto",
    ]
    yy = y + 60
    for line in stack:
        d.ellipse((M + 28, yy + 8, M + 42, yy + 22), fill=ORANGE)
        d.text((M + 54, yy), line, font=font(20), fill=INK)
        yy += 42

    d.text((M + 802, y + 16), "What the officer sees", font=font(24, True), fill=NAVY)
    rounded(d, (M + 802, y + 60, W - M - 24, y + 230), 14, NAVY)
    d.text((M + 822, y + 76), "Monitoring + AI", font=font(22, True), fill=WHITE)
    draw_wrapped(
        d,
        M + 822,
        y + 114,
        "Node cards, WATCH / ALERT reason, Isolation Forest score, 30 s chart with MAE. No drive buttons here.",
        font(18),
        WHITE,
        700,
        4,
    )
    rounded(d, (M + 802, y + 250, W - M - 24, y + 410), 14, TEAL)
    d.text((M + 822, y + 266), "Rover Inspection", font=font(22, True), fill=WHITE)
    draw_wrapped(
        d,
        M + 822,
        y + 304,
        "Hold FWD / REV / LEFT / RIGHT. Release = STOP. Distance, IR flag, MQ-7 raw. Open this page after a warning.",
        font(18),
        WHITE,
        700,
        4,
    )

    y = section(d, M, 640, "Machine learning  —  core product, on the laptop", GOLD)

    ml = [
        (
            NAVY,
            "Isolation Forest + LOF",
            "Is this unusual vs this table’s quiet normal?",
            [
                "Features: tilt change, vibration, rate, Node A mm",
                "Shows score, top feature, train count",
                "Cannot clear a rule ALERT",
            ],
        ),
        (
            GOLD,
            "Joint A vs B forest",
            "Did one node move, or the whole model?",
            [
                "Uses |A−B| tilt and vibration",
                "QUIET / LOCAL_A / LOCAL_B / COMMON",
                "Not a geology model",
            ],
        ),
        (
            ORANGE,
            "30 s sensor forecast",
            "The hackathon “prediction”",
            [
                "Next 30 s of tilt / vibration / crack mm",
                "Holdout MAE picks Ridge / Huber / linear",
                "Label: not a collapse prediction",
            ],
        ),
    ]
    gap = 18
    mw = (W - 2 * M - 2 * gap) / 3
    mh = 340
    for i, (col, title, sub, lines) in enumerate(ml):
        x = M + i * (mw + gap)
        rounded(d, (x, y, x + mw, y + mh), 18, col)
        d.text((x + 20, y + 18), title, font=font(22, True), fill=WHITE)
        draw_wrapped(d, x + 20, y + 58, sub, font(18), (255, 236, 210) if col == ORANGE else (230, 236, 242), mw - 40, 4)
        yy = y + 130
        for line in lines:
            d.ellipse((x + 24, yy + 8, x + 38, yy + 22), fill=WHITE)
            draw_wrapped(d, x + 50, yy, line, font(17), WHITE, mw - 74, 2)
            yy += 58

    y = section(d, M, 1048, "Rules that latch  (tabletop numbers, not mine standards)", ORANGE)
    rules = [
        (TEAL, "NORMAL", "Fresh data, below the watch line"),
        (ORANGE, "WATCH", "3° tilt or 2 mm gap, 3 samples"),
        (RED, "ALERT", "6° or 4 mm, 3 samples — stays on"),
        (MUTED, "UNKNOWN", "No packet for 5 s, or not calibrated"),
    ]
    gap = 16
    rw = (W - 2 * M - 3 * gap) / 4
    for i, (col, title, sub) in enumerate(rules):
        x = M + i * (rw + gap)
        rounded(d, (x, y, x + rw, y + 128), 14, col)
        d.text((x + 16, y + 16), title, font=font(22, True), fill=WHITE)
        draw_wrapped(d, x + 16, y + 56, sub, font(17), WHITE, rw - 32, 3)

    y = 1048 + 48 + 128 + 28
    rounded(d, (M, y, W - M, y + 70), 12, PALE)
    d.text(
        (M + 22, y + 22),
        "Ack = I saw it.  Clear needs 3 NORMAL samples.  Isolation Forest cannot turn ALERT off.",
        font=font(20, True),
        fill=NAVY,
    )

    y = section(d, M, y + 92, "Simple honesty", TEAL)
    yes = [
        "NORMAL / WATCH / ALERT / UNKNOWN on this rig",
        "Unusual vs this tabletop’s normal + MAE",
        "30 s forecast of the same signals",
        "MQ-7 raw ADC  ·  IR is a near flag",
        "Remote drive  ·  operator inspects",
    ]
    no = [
        "“The mine is safe / certified”",
        "Collapse or subsidence probability",
        "“Roof fails in N minutes”",
        "CO ppm  ·  auto-brake  ·  lidar",
        "Autonomous rover  ·  camera AI  ·  LoRa",
    ]
    mid = (W - 2 * M - 18) / 2
    rounded(d, (M, y, M + mid, y + 268), 16, (226, 242, 236))
    rounded(d, (M + mid + 18, y, W - M, y + 268), 16, (255, 236, 232))
    d.text((M + 22, y + 14), "We do say", font=font(22, True), fill=TEAL)
    d.text((M + mid + 40, y + 14), "We do not say", font=font(22, True), fill=RED)
    yy1 = y + 56
    for line in yes:
        d.text((M + 22, yy1), "✓  " + line, font=font(18), fill=INK)
        yy1 += 40
    yy2 = y + 56
    for line in no:
        d.text((M + mid + 40, yy2), "✗  " + line, font=font(18), fill=INK)
        yy2 += 40

    y = y + 286
    rounded(d, (M, y, W - M, y + 196), 16, NAVY)
    d.text((M + 24, y + 16), "Spoken close", font=font(18, True), fill=ORANGE)
    draw_wrapped(
        d,
        M + 24,
        y + 50,
        "Isolation Forest flags unusual combinations versus this rig’s learned normal. A joint forest watches A vs B. "
        "Holdout-selected regression forecasts the next 30 seconds of those same signals with MAE. Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy.",
        font(20),
        WHITE,
        W - 2 * M - 48,
        6,
    )
    return img


def build() -> Path:
    p1, p2 = page1(), page2()
    PREVIEW.mkdir(parents=True, exist_ok=True)
    p1.save(PREVIEW / "page_01.png", "PNG")
    p2.save(PREVIEW / "page_02.png", "PNG")
    rgb1, rgb2 = p1.convert("RGB"), p2.convert("RGB")
    rgb1.save(OUT_PDF, "PDF", resolution=200.0, save_all=True, append_images=[rgb2])
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    shutil.copy2(OUT_PDF, DOWNLOADS / OUT_PDF.name)
    return OUT_PDF


if __name__ == "__main__":
    path = build()
    print("saved", path)
    print("copied", DOWNLOADS / path.name)
