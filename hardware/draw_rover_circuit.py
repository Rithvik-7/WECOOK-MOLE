"""Draw MOLE rover wiring. Pins match firmware/rover/rover.ino (frozen 9 Sep 2026)."""
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(r"C:\Users\brith\Desktop\mole\hardware\rover-circuit.png")

NAVY = (31, 73, 125)
ORANGE = (247, 150, 70)
TEAL = (75, 172, 198)
RED = (180, 45, 45)
BLK = (28, 35, 45)
GND = (40, 120, 70)
WHITE = (255, 255, 255)
OFF = (248, 250, 252)
LINE = (90, 100, 112)
IR = (120, 70, 140)


def font(size, bold=False):
    names = [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]
    for name in names:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def box(d, xy, title, lines, fill=NAVY):
    x0, y0, x1, y1 = xy
    d.rounded_rectangle(xy, 14, fill=WHITE, outline=fill, width=3)
    d.rectangle((x0, y0, x1, y0 + 36), fill=fill)
    d.text((x0 + 12, y0 + 7), title, font=font(16, True), fill=WHITE)
    y = y0 + 48
    for ln in lines:
        d.text((x0 + 12, y), ln, font=font(14), fill=BLK)
        y += 22


def main():
    w, h = 1680, 1280
    img = Image.new("RGB", (w, h), OFF)
    d = ImageDraw.Draw(img)

    d.text((40, 18), "MOLE rover  ·  frozen pin map  ·  tabletop wiring", font=font(28, True), fill=NAVY)
    d.text(
        (40, 54),
        "Classic ESP32-WROOM-32. Wi-Fi AP Mine-Rover-AP. GPIO19 is IR, not a motor pin.",
        font=font(16),
        fill=LINE,
    )

    box(
        d,
        (40, 96, 300, 270),
        "BATTERY  (motor pack)",
        ["+  to switch, then L298N 12V", "−  to common GND", "Typical 7.4 V (2S) or 6xAA", "NOT into ESP32 3.3V pin"],
        RED,
    )
    box(d, (340, 120, 520, 220), "SWITCH", ["Battery +  →  L298N 12V"], ORANGE)

    box(
        d,
        (560, 96, 1040, 400),
        "MOTOR MODULE  (L298N)",
        [
            "12V / VMS   ← battery + (via switch)",
            "GND         ← battery −  and ESP32 GND",
            "5V          unused for this ESP32",
            "",
            "OUT1 / OUT2  →  LEFT motor",
            "OUT3 / OUT4  →  RIGHT motor",
            "",
            "IN1  ← GPIO13    IN2  ← GPIO12",
            "IN3  ← GPIO14    IN4  ← GPIO27",
            "Leave ENA/ENB jumpers ON. Firmware stops by setting IN1–IN4 LOW.",
        ],
        NAVY,
    )

    box(d, (1080, 96, 1360, 220), "LEFT MOTOR", ["2 wires → OUT1, OUT2", "If FWD is backward,", "swap these two wires"], TEAL)
    box(d, (1080, 250, 1360, 374), "RIGHT MOTOR", ["2 wires → OUT3, OUT4", "If FWD is backward,", "swap these two wires"], TEAL)
    box(d, (1400, 170, 1640, 300), "CASTER", ["3rd wheel", "NO wires", "Must spin freely"], LINE)

    box(
        d,
        (40, 430, 620, 900),
        "ESP32-WROOM-32  (rover brain)",
        [
            "GND     → common ground (battery − and L298N GND)",
            "VIN/5V  → USB (bench) or 5V bank (demo)",
            "3.3V    → sensors only, never motors",
            "",
            "GPIO13  → L298N IN1     (left)",
            "GPIO12  → L298N IN2     (left)",
            "GPIO14  → L298N IN3     (right)",
            "GPIO27  → L298N IN4     (right)",
            "GPIO21 / 22 → MPU6050 SDA / SCL",
            "GPIO5   → HC-SR04 TRIG",
            "GPIO18  → Echo after 1k / 2k divider",
            "GPIO19  → IR OUT  (LOW = obstacle)",
            "GPIO36  → MQ-7 AO  (raw ADC, not ppm)",
            "",
            "Do not wire GPIO19 to L298N.",
        ],
        NAVY,
    )

    box(
        d,
        (660, 430, 1120, 720),
        "HC-SR04  (front ranging)",
        [
            "VCC   → 5V  (USB 5V on DevKit, not 3.3V)",
            "GND   → common GND",
            "TRIG  → GPIO5",
            "ECHO  → 1kΩ → GPIO18",
            "         GPIO18 → 2kΩ → GND",
            "",
            "ECHO is 5V. Divider required.",
            "Do not wire ECHO straight to ESP32.",
        ],
        ORANGE,
    )

    box(
        d,
        (1160, 430, 1640, 600),
        "ECHO DIVIDER",
        ["ECHO --1kΩ--+-- GPIO18", "             |", "           2kΩ", "             |", "            GND"],
        RED,
    )

    box(
        d,
        (1160, 620, 1640, 820),
        "IR OBSTACLE  (digital flag)",
        [
            "VCC → 5V or 3.3V (match the module)",
            "GND → common GND",
            "OUT → GPIO19  (INPUT_PULLUP)",
            "LOW = something close. Not centimetres.",
            "Does not stop motors. Ambient light can false-trip.",
        ],
        IR,
    )

    box(
        d,
        (660, 750, 1120, 900),
        "MPU6050 + MQ-7",
        [
            "MPU 3V3 / GND / SDA21 / SCL22 / 0x68",
            "MQ-7 AO → GPIO36 raw ADC. Not CO ppm.",
        ],
        TEAL,
    )

    box(
        d,
        (40, 930, 1640, 1060),
        "DRIVE  (after firmware)",
        [
            "FWD: IN1+IN3 HIGH     REV: IN2+IN4 HIGH     STOP: all IN LOW (also 400 ms watchdog)",
            "LEFT / RIGHT: opposite sides. Caster only balances. IR and ultrasonic are dashboard-only.",
            "Laptop joins Wi-Fi Mine-Rover-AP and uses http://192.168.4.1  — not the node ESP-NOW USB path.",
        ],
        GND,
    )

    d.text((40, 1090), "Common ground is mandatory. Motors never from 3.3V. Rover radio ≠ node S3-Zero USB.", font=font(18, True), fill=NAVY)
    d.text(
        (40, 1128),
        "GPIO19 is the IR flag. Older drawings that put GPIO19 on L298N IN4 are wrong for this firmware.",
        font=font(15),
        fill=RED,
    )
    d.text((40, 1164), "Tabletop demonstration only. Not mine-certified / not intrinsically safe.", font=font(14), fill=LINE)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, "PNG", optimize=True)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
