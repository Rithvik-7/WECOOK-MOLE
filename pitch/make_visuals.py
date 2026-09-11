"""PNG icons + flowcharts for the official 6-slide SIH idea deck. No fake metrics."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:\Users\brith\Desktop\mole\pitch\assets")
OUT.mkdir(parents=True, exist_ok=True)

NAVY = (11, 44, 74)
NAVY2 = (15, 58, 98)
ORANGE = (244, 123, 32)
TEAL = (14, 124, 123)
WHITE = (255, 255, 255)
INK = (26, 26, 26)
MUTED = (74, 85, 99)
PALE = (244, 247, 250)
LINE = (213, 222, 232)
GOLD = (196, 138, 18)


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf",
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def save(img, name):
    path = OUT / name
    img.save(path, "PNG", optimize=True)
    print("wrote", path)
    return path


def rounded(draw, box, r, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)


def centre_text(draw, xy, text, fnt, fill=WHITE):
    x0, y0, x1, y1 = xy
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x0 + (x1 - x0 - tw) / 2, y0 + (y1 - y0 - th) / 2 - 1), text, font=fnt, fill=fill)


def icon_base(color):
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((8, 8, 248, 248), 48, fill=color)
    return img, d


def icon_nodes():
    img, d = icon_base(NAVY)
    d.ellipse((58, 70, 118, 130), outline=WHITE, width=10)
    d.ellipse((138, 70, 198, 130), outline=WHITE, width=10)
    d.line((118, 100, 138, 100), fill=WHITE, width=8)
    d.rectangle((88, 150, 168, 198), outline=WHITE, width=8)
    return save(img, "icon_nodes.png")


def icon_warn():
    img, d = icon_base(ORANGE)
    d.polygon([(128, 48), (210, 198), (46, 198)], outline=WHITE, width=10)
    d.rectangle((120, 100, 136, 150), fill=WHITE)
    d.ellipse((118, 162, 138, 182), fill=WHITE)
    return save(img, "icon_warn.png")


def icon_inspect():
    img, d = icon_base(TEAL)
    d.rounded_rectangle((70, 88, 186, 168), 18, outline=WHITE, width=10)
    d.ellipse((96, 108, 160, 160), outline=WHITE, width=8)
    d.polygon([(186, 150), (220, 184), (204, 200), (170, 166)], fill=WHITE)
    d.rectangle((88, 178, 168, 198), fill=WHITE)
    return save(img, "icon_inspect.png")


def icon_usb():
    img, d = icon_base(NAVY2)
    d.rectangle((108, 40, 148, 88), fill=WHITE)
    d.rectangle((96, 88, 160, 168), outline=WHITE, width=10)
    d.rectangle((118, 168, 138, 210), fill=WHITE)
    return save(img, "icon_usb.png")


def icon_ml():
    img, d = icon_base(GOLD)
    pts = [(80, 80), (176, 80), (176, 176), (80, 176)]
    for x, y in pts:
        d.ellipse((x - 14, y - 14, x + 14, y + 14), fill=WHITE)
    d.line((80, 80, 176, 80), fill=WHITE, width=6)
    d.line((176, 80, 176, 176), fill=WHITE, width=6)
    d.line((176, 176, 80, 176), fill=WHITE, width=6)
    d.line((80, 176, 80, 80), fill=WHITE, width=6)
    d.line((80, 80, 176, 176), fill=WHITE, width=6)
    return save(img, "icon_ml.png")


def icon_dash():
    img, d = icon_base(NAVY)
    d.rounded_rectangle((56, 64, 200, 168), 16, outline=WHITE, width=10)
    d.rectangle((72, 88, 184, 112), fill=WHITE)
    d.rectangle((72, 128, 112, 148), fill=WHITE)
    d.rectangle((124, 128, 184, 148), fill=ORANGE)
    d.rectangle((96, 176, 160, 198), fill=WHITE)
    return save(img, "icon_dash.png")


def solution_flow():
    w, h = 2200, 420
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    steps = [
        (NAVY, "1  MONITOR", "Node A tilt + crack", "Node B comparison IMU", "ESP-NOW → S3-Zero USB"),
        (ORANGE, "2  WARN + PREDICT", "Rules latch WATCH / ALERT", "Isolation Forest = unusual", "Ridge = next 30 s of signals"),
        (TEAL, "3  INSPECT", "Officer decides first", "Remote FWD REV LEFT RIGHT STOP", "Distance · IR flag · MQ-7 raw"),
    ]
    gap = 40
    box_w = 640
    x = 40
    f_t, f_b = font(36, True), font(24)
    for i, (col, title, a, b, c) in enumerate(steps):
        rounded(d, (x, 36, x + box_w, 384), 28, col)
        d.text((x + 28, 56), title, font=f_t, fill=WHITE)
        for j, line in enumerate((a, b, c)):
            d.ellipse((x + 36, 140 + j * 70, x + 60, 164 + j * 70), fill=WHITE)
            d.text((x + 76, 134 + j * 70), line, font=f_b, fill=WHITE)
        if i < 2:
            ax = x + box_w + 6
            ay = 210
            d.polygon([(ax, ay - 18), (ax + 28, ay), (ax, ay + 18)], fill=ORANGE)
        x += box_w + gap
    d.text((40, 6), "Proposed solution  ·  one product, three jobs  ·  rover is not the monitor", font=font(22, True), fill=NAVY)
    return save(img, "solution_flow.png")


def tech_flow():
    w, h = 2400, 520
    img = Image.new("RGB", (w, h), PALE)
    d = ImageDraw.Draw(img)
    d.text((36, 16), "Working prototype path  ·  tabletop, local laptop, no venue cloud", font=font(28, True), fill=NAVY)

    boxes = [
        (NAVY, "Node A + Node B", "ESP32-WROOM-32\nMPU6050 · 1 Hz summary"),
        (NAVY2, "S3-Zero USB", "ESP-NOW ch 1\nJSON 115200"),
        (GOLD, "Laptop validate", "Schema · freshness\nbaseline features"),
        (ORANGE, "Rules + ML", "Latch + Isolation Forest\n+ 30 s Ridge"),
        (NAVY, "Dashboard", "127.0.0.1 Flask\nreason + MAE"),
        (TEAL, "Rover AP", "Mine-Rover-AP\nremote inspect"),
    ]
    n = len(boxes)
    bw, bh = 330, 300
    gap = 28
    total = n * bw + (n - 1) * gap
    x = (w - total) / 2
    y = 80
    f_t, f_b = font(26, True), font(20)
    for i, (col, title, body) in enumerate(boxes):
        rounded(d, (x, y, x + bw, y + bh), 24, col)
        centre_text(d, (x, y + 24, x + bw, y + 90), title, f_t, WHITE)
        lines = body.split("\n")
        yy = y + 120
        for ln in lines:
            bbox = d.textbbox((0, 0), ln, font=f_b)
            tw = bbox[2] - bbox[0]
            d.text((x + (bw - tw) / 2, yy), ln, font=f_b, fill=WHITE)
            yy += 40
        if i < n - 1:
            ax = x + bw + 4
            ay = y + bh / 2
            d.polygon([(ax, ay - 14), (ax + 20, ay), (ax, ay + 14)], fill=ORANGE)
        x += bw + gap

    d.text(
        (36, 430),
        "Rover radio is separate. Rover IMU never enters Node A/B Isolation Forest. Live USB never silently fakes data.",
        font=font(22, True),
        fill=MUTED,
    )
    return save(img, "tech_flow.png")


def method_flow():
    w, h = 2400, 280
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    steps = [
        ("1", "Usable?", "Fresh · valid · known ID"),
        ("2", "Delta", "Tilt / vib / mm vs baseline"),
        ("3", "Persist", "3 samples — not one tap"),
        ("4", "Decide", "Rules latch; ML cannot clear"),
        ("5", "Show", "Reason · score · MAE"),
        ("6", "Inspect", "Rover only if officer sends it"),
    ]
    bw = 350
    gap = 30
    x = 40
    for i, (n, t, s) in enumerate(steps):
        col = ORANGE if i >= 4 else NAVY
        rounded(d, (x, 36, x + bw, 250), 20, col)
        d.ellipse((x + 20, 56, x + 70, 106), fill=WHITE)
        centre_text(d, (x + 20, 56, x + 70, 106), n, font(28, True), col)
        d.text((x + 86, 62), t, font=font(28, True), fill=WHITE)
        d.text((x + 24, 140), s, font=font(22), fill=WHITE)
        if i < 5:
            d.polygon(
                [(x + bw + 4, 140), (x + bw + 22, 152), (x + bw + 4, 164)],
                fill=ORANGE,
            )
        x += bw + gap
    d.text((40, 4), "Method on every accepted node packet", font=font(22, True), fill=NAVY)
    return save(img, "method_flow.png")


def icon_ok():
    img, d = icon_base(TEAL)
    d.line((72, 128, 112, 168), fill=WHITE, width=14)
    d.line((112, 168, 190, 88), fill=WHITE, width=14)
    return save(img, "icon_ok.png")


def icon_stop():
    img, d = icon_base(ORANGE)
    d.ellipse((56, 56, 200, 200), outline=WHITE, width=12)
    d.rectangle((88, 116, 168, 140), fill=WHITE)
    return save(img, "icon_stop.png")


def icon_wifi():
    img, d = icon_base(NAVY)
    d.arc((64, 70, 192, 198), 200, 340, fill=WHITE, width=12)
    d.arc((88, 96, 168, 176), 200, 340, fill=WHITE, width=12)
    d.ellipse((118, 150, 138, 170), fill=WHITE)
    return save(img, "icon_wifi.png")


def demo_loop():
    w, h = 2400, 290
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    d.text((16, 2), "How we show it works  (one loop on the table)", font=font(26, True), fill=NAVY)
    steps = [
        (TEAL, "1  Still", "Both nodes quiet"),
        (NAVY, "2  Tilt", "Move Node A a little"),
        (ORANGE, "3  Warn", "WATCH then ALERT"),
        (GOLD, "4  Drive", "Open rover page"),
        (NAVY2, "5  Keep", "Event stays in history"),
    ]
    x = 16
    bw = 428
    for i, (col, title, sub) in enumerate(steps):
        rounded(d, (x, 42, x + bw, 278), 22, col)
        d.text((x + 22, 64), title, font=font(32, True), fill=WHITE)
        d.text((x + 22, 150), sub, font=font(24), fill=WHITE)
        if i < 4:
            _arrow(d, x + bw + 6, 160)
        x += bw + 44
    return save(img, "demo_loop.png")


def threshold_graph():
    """Honest demo thresholds, not mine data."""
    w, h = 1400, 596
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    rounded(d, (8, 8, w - 8, h - 8), 24, PALE)
    d.text((28, 16), "Demo graph  ·  when the light changes", font=font(26, True), fill=NAVY)
    d.text((28, 50), "Table model only. Not a mine safety chart.", font=font(18), fill=MUTED)

    ax, ay, bx, by = 88, 88, 1348, 430
    def y_at(deg):
        return by - (deg / 8.0) * (by - ay)

    d.rectangle((ax, y_at(8), bx, y_at(6)), fill=(232, 214, 214))
    d.rectangle((ax, y_at(6), bx, y_at(3)), fill=(255, 232, 210))
    d.rectangle((ax, y_at(3), bx, y_at(0)), fill=(210, 236, 222))

    d.line((ax, y_at(3), bx, y_at(3)), fill=ORANGE, width=3)
    d.line((ax, y_at(6), bx, y_at(6)), fill=(192, 57, 43), width=3)
    d.line((ax, by, bx, by), fill=NAVY, width=3)
    d.line((ax, ay, ax, by), fill=NAVY, width=3)

    d.text((20, y_at(8) - 6), "8°", font=font(18, True), fill=NAVY)
    d.text((20, y_at(6) - 10), "6°", font=font(18, True), fill=(192, 57, 43))
    d.text((20, y_at(3) - 10), "3°", font=font(18, True), fill=ORANGE)
    d.text((20, y_at(0) - 10), "0°", font=font(18, True), fill=NAVY)
    d.text((ax + 16, y_at(1.2) - 8), "OK", font=font(22, True), fill=TEAL)
    d.text((ax + 16, y_at(4.4) - 8), "WATCH", font=font(22, True), fill=ORANGE)
    d.text((ax + 16, y_at(7.1) - 8), "ALERT", font=font(22, True), fill=(192, 57, 43))

    pts_deg = [
        (0.04, 0.6),
        (0.18, 0.7),
        (0.32, 0.8),
        (0.42, 2.2),
        (0.52, 3.4),
        (0.62, 4.0),
        (0.74, 6.4),
        (0.88, 6.8),
        (0.96, 6.9),
    ]
    pts = [(ax + t * (bx - ax), y_at(deg)) for t, deg in pts_deg]
    d.line(pts, fill=NAVY, width=6)
    for x, y in pts:
        d.ellipse((x - 6, y - 6, x + 6, y + 6), fill=NAVY)

    d.text((ax, 440), "quiet", font=font(18), fill=MUTED)
    d.text((ax + 460, 440), "tilt Node A", font=font(18), fill=MUTED)
    d.text((ax + 920, 440), "keep it tilted", font=font(18), fill=MUTED)

    d.text((28, 478), "Need 3 readings in a row. One tap is not a warning.", font=font(20), fill=INK)
    d.text((28, 510), "No packet for 5 s → UNKNOWN. Never fake a green light.", font=font(20), fill=INK)
    d.text((28, 542), "AI cannot turn a red warning back to green.", font=font(20, True), fill=NAVY)
    return save(img, "threshold_graph.png")


def _arrow(draw, x, y):
    draw.polygon([(x, y - 12), (x + 22, y), (x, y + 12)], fill=ORANGE)


def architecture_lanes():
    """Two radios. Node A and Node B both broadcast into the S3-Zero."""
    w, h = 2400, 700
    img = Image.new("RGB", (w, h), WHITE)
    d = ImageDraw.Draw(img)
    f_h, f_t, f_b = font(26, True), font(30, True), font(22)

    rounded(d, (20, 16, w - 20, 360), 28, PALE)
    d.rectangle((20, 16, 28, 360), fill=NAVY)
    d.text((48, 28), "MONITOR PATH   ·   both nodes broadcast ESP-NOW ch1   ·   USB into the laptop", font=f_h, fill=NAVY)

    rounded(d, (48, 78, 418, 198), 20, NAVY)
    d.text((68, 92), "Node A", font=f_t, fill=WHITE)
    d.text((68, 138), "MPU 21/22  ·  slider GPIO34", font=f_b, fill=WHITE)
    rounded(d, (48, 218, 418, 338), 20, NAVY)
    d.text((68, 232), "Node B", font=f_t, fill=WHITE)
    d.text((68, 278), "MPU 21/22  ·  compare only", font=f_b, fill=WHITE)

    d.line((418, 138, 500, 138), fill=ORANGE, width=6)
    d.line((418, 278, 500, 278), fill=ORANGE, width=6)
    d.line((500, 138, 500, 278), fill=ORANGE, width=6)
    d.line((500, 208, 548, 208), fill=ORANGE, width=6)
    _arrow(d, 548, 208)

    rest = [
        (NAVY2, "S3-Zero USB", "ESP-NOW RX", "JSON 115200"),
        (GOLD, "Laptop", "Validate + store", "Rules · IF · Ridge"),
        (NAVY, "Dashboard", "127.0.0.1 Flask", "Reason · score · MAE"),
    ]
    x = 580
    for i, (col, title, a, b) in enumerate(rest):
        rounded(d, (x, 88, x + 500, 328), 22, col)
        d.text((x + 24, 108), title, font=f_t, fill=WHITE)
        d.text((x + 24, 178), a, font=font(24), fill=WHITE)
        d.text((x + 24, 230), b, font=font(24), fill=WHITE)
        if i < 2:
            _arrow(d, x + 508, 208)
        x += 540

    rounded(d, (20, 384, w - 20, 680), 28, (232, 246, 245))
    d.rectangle((20, 384, 28, 680), fill=TEAL)
    d.text((48, 396), "INSPECT PATH   ·   separate Wi-Fi AP Mine-Rover-AP   ·   not on the node USB radio", font=f_h, fill=TEAL)

    inspect = [
        (GOLD, "Officer", "Sees WATCH / ALERT", "Then decides to inspect"),
        (TEAL, "Laptop proxy", "Hold FWD / REV / LEFT / RIGHT", "Release sends STOP"),
        (TEAL, "Rover ESP32", "L298N 13 / 12 / 14 / 27", "Remote — not autonomous"),
        (NAVY2, "Inspect sensors", "HC-SR04 cm  ·  IR flag", "MQ-7 raw  ·  rover IMU only"),
    ]
    x = 48
    y = 452
    bw, bh = 520, 190
    for i, (col, title, a, b) in enumerate(inspect):
        rounded(d, (x, y, x + bw, y + bh), 22, col)
        d.text((x + 22, y + 16), title, font=f_t, fill=WHITE)
        d.text((x + 22, y + 78), a, font=f_b, fill=WHITE)
        d.text((x + 22, y + 122), b, font=f_b, fill=WHITE)
        if i < 3:
            _arrow(d, x + bw + 8, y + bh / 2)
        x += bw + 40

    return save(img, "architecture_lanes.png")


if __name__ == "__main__":
    icon_nodes()
    icon_warn()
    icon_inspect()
    icon_usb()
    icon_ml()
    icon_dash()
    solution_flow()
    tech_flow()
    method_flow()
    icon_ok()
    icon_stop()
    icon_wifi()
    demo_loop()
    threshold_graph()
    architecture_lanes()
