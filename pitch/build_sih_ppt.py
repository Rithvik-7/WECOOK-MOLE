"""Fill official SIH 2026 6-slide template. Do not invent a 7th idea slide."""

from copy import deepcopy
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.oxml.ns import nsmap, qn
from pptx.util import Emu, Inches, Pt
from lxml import etree
from pathlib import Path

SRC = Path(r"c:\Users\brith\Downloads\SIH2026-IDEA-Presentation-Format_.pptx")
OUT = Path(r"c:\Users\brith\Desktop\mole\pitch\SIH26025_WE_COOK_IDEA.pptx")

NAVY = RGBColor(0x0B, 0x2C, 0x4A)
ORANGE = RGBColor(0xF4, 0x7B, 0x20)
TEAL = RGBColor(0x0E, 0x7C, 0x7B)
RED = RGBColor(0xC0, 0x39, 0x2B)
GREEN = RGBColor(0x1E, 0x7A, 0x46)
GOLD = RGBColor(0xC4, 0x8A, 0x12)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x4A, 0x55, 0x63)
PALE = RGBColor(0xF4, 0xF7, 0xFA)
LINE = RGBColor(0xD5, 0xDE, 0xE8)


def set_run(run, text, size=12, bold=False, color=INK, font="Calibri"):
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    run.font.name = font


def fill_shape_text(shape, lines, size=13, bold=False, color=INK, align=PP_ALIGN.LEFT):
    tf = shape.text_frame
    tf.clear()
    tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(4)
        set_run(p.add_run(), line, size=size, bold=bold, color=color)


def hide_shape(shape):
    shape.left = Emu(0)
    shape.top = Emu(0)
    shape.width = Emu(1)
    shape.height = Emu(1)
    if shape.has_text_frame:
        shape.text_frame.clear()


def add_box(slide, l, t, w, h, fill, line=None):
    sh = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, l, t, w, h)
    sh.adjustments[0] = 0.08
    sh.fill.solid()
    sh.fill.fore_color.rgb = fill
    sh.line.color.rgb = line or fill
    sh.line.width = Pt(0.75)
    return sh


def add_text_box(slide, l, t, w, h, lines, size=11, bold=False, color=INK, align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(l, t, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    tf.auto_size = None
    try:
        tb.text_frame._txBody.bodyPr.set("anchor", {MSO_ANCHOR.TOP: "t", MSO_ANCHOR.MIDDLE: "ctr", MSO_ANCHOR.BOTTOM: "b"}[anchor])
    except Exception:
        pass
    tf.clear()
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.space_after = Pt(2)
        set_run(p.add_run(), line, size=size, bold=bold, color=color)
    return tb


def add_table(slide, l, t, w, h, rows):
    n_rows = len(rows)
    n_cols = len(rows[0])
    table_shape = slide.shapes.add_table(n_rows, n_cols, l, t, w, h)
    table = table_shape.table
    col_w = int(w / n_cols)
    for c in range(n_cols):
        table.columns[c].width = col_w
    for r, row in enumerate(rows):
        for c, val in enumerate(row):
            cell = table.cell(r, c)
            cell.text = ""
            p = cell.text_frame.paragraphs[0]
            p.alignment = PP_ALIGN.LEFT
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            is_head = r == 0
            set_run(
                p.add_run(),
                val,
                size=10 if is_head else 10,
                bold=is_head or c == 0,
                color=WHITE if is_head else INK,
            )
            cell.fill.solid()
            if is_head:
                cell.fill.fore_color.rgb = NAVY
            elif r % 2 == 0:
                cell.fill.fore_color.rgb = PALE
            else:
                cell.fill.fore_color.rgb = WHITE
    return table_shape


def delete_slide(prs, index):
    sldIdLst = prs.slides._sldIdLst
    sldId = list(sldIdLst)[index]
    rId = sldId.get(qn("r:id"))
    prs.part.drop_rel(rId)
    sldIdLst.remove(sldId)


def set_team_oval(slide, name="WE COOK"):
    for sh in slide.shapes:
        if sh.has_text_frame and "Your Team Name" in sh.text_frame.text:
            fill_shape_text(sh, [name], size=12, bold=True, color=WHITE, align=PP_ALIGN.CENTER)


def fill_slide1(prs):
    s = prs.slides[0]
    for sh in s.shapes:
        if sh.has_text_frame and "Problem Statement ID" in sh.text_frame.text:
            tf = sh.text_frame
            tf.clear()
            tf.word_wrap = True
            fields = [
                ("Problem Statement ID", "SIH26025"),
                ("Problem Statement Title", "Development of an AI-enabled Low Cost Real Time Mine Subsidence Monitoring, Prediction and Early Warning System for Underground Coal Mines in India"),
                ("Theme", "Disaster Management"),
                ("PS Category", "Hardware"),
                ("Organisation", "Ministry of Coal"),
                ("Team ID", "[fill after SIH portal]"),
                ("Team Name", "WE COOK"),
                ("Idea", "MOLE — monitor the model, warn from evidence, inspect on command"),
            ]
            first = True
            for label, val in fields:
                p = tf.paragraphs[0] if first else tf.add_paragraph()
                first = False
                p.space_after = Pt(8)
                r1 = p.add_run()
                set_run(r1, label + "  ", size=13, bold=True, color=ORANGE)
                r2 = p.add_run()
                set_run(r2, val, size=13, bold=False, color=WHITE)


def fill_slide2(prs):
    s = prs.slides[1]
    set_team_oval(s)
    for sh in s.shapes:
        if sh.has_text_frame and "IDEA TITLE" in sh.text_frame.text:
            fill_shape_text(sh, ["MOLE — Proposed Solution"], size=28, bold=True, color=NAVY)
        if sh.has_text_frame and "Proposed Solution" in sh.text_frame.text:
            hide_shape(sh)

    add_text_box(
        s,
        Inches(0.35),
        Inches(1.15),
        Inches(12.6),
        Inches(0.38),
        ["One product: two fixed nodes + laptop ML + one dashboard + a remote rover. Officer sees a change, understands the numbers, then inspects."],
        size=13,
        bold=True,
        color=NAVY,
    )

    cols = [
        (NAVY, "1. MONITOR", "Node A: tilt + crack slider\nNode B: comparison IMU\nESP-NOW → S3-Zero USB JSON"),
        (TEAL, "2. WARN + PREDICT", "Rules latch WATCH / ALERT\nIsolation Forest = unusual\nRidge = next 30 s of signals"),
        (ORANGE, "3. INSPECT", "Operator decides\nRover: FWD REV LEFT RIGHT STOP\nDistance, IR, MQ-7 raw, rover IMU"),
    ]
    x = Inches(0.35)
    for fill, title, body in cols:
        box = add_box(s, x, Inches(1.55), Inches(4.05), Inches(1.55), fill)
        add_text_box(s, x + Inches(0.12), Inches(1.6), Inches(3.8), Inches(0.32), [title], size=13, bold=True, color=WHITE)
        add_text_box(s, x + Inches(0.12), Inches(1.92), Inches(3.8), Inches(1.1), body.split("\n"), size=12, color=WHITE)
        x += Inches(4.2)

    add_text_box(s, Inches(0.35), Inches(3.18), Inches(12.6), Inches(0.28), ["How this maps the PS (honest, tabletop)"], size=12, bold=True, color=NAVY)
    add_table(
        s,
        Inches(0.35),
        Inches(3.46),
        Inches(12.6),
        Inches(2.55),
        [
            ["PS word", "What MOLE actually does", "What we do not claim"],
            ["Monitoring", "Live Node A + Node B, source-tagged, timed", "Rover IMU is not Node B"],
            ["Early warning", "Rules: 3 samples → WATCH/ALERT; stale → UNKNOWN", "Green = healthy data, not a certified-safe mine"],
            ["AI-enabled", "Isolation Forest on this rig’s NORMAL samples; score + top feature on screen", "No LLM, no collapse %, no camera vision"],
            ["Prediction", "Ridge: next 30 s of tilt/vibration/crack + MAE", "Not a mine-subsidence or roof-fall forecast"],
            ["Uniqueness", "Rules cannot be cleared by ML. A vs B residual = local vs whole-table motion. Rover only after a warning.", "Not a gas-car maze robot; not LoRa; not autonomous drive"],
        ],
    )


def fill_slide3(prs):
    s = prs.slides[2]
    set_team_oval(s)
    for sh in s.shapes:
        if sh.has_text_frame and "Technologies to be used" in sh.text_frame.text:
            hide_shape(sh)

    add_text_box(s, Inches(0.35), Inches(1.12), Inches(12.6), Inches(0.26), ["Technologies + method (what is built vs what is claimed)"], size=12, bold=True, color=NAVY)

    add_table(
        s,
        Inches(0.35),
        Inches(1.38),
        Inches(12.6),
        Inches(1.55),
        [
            ["Layer", "Stack", "Role"],
            ["Nodes A/B", "Classic ESP32-WROOM-32, MPU6050 I²C 0x68, Node A 10 kΩ slider GPIO34", "Measure tilt, vibration proxy, crack ADC"],
            ["Receiver", "Waveshare ESP32-S3-Zero, ESP-NOW ch1, USB-C JSON 115200", "Bridge only — no sensors, no ML"],
            ["Laptop ML", "Python, Flask, SQLite, scikit-learn IsolationForest + Ridge, joblib", "Validate, store, warn, explain"],
            ["Rover", "Classic ESP32, L298N, HC-SR04, IR, MQ-7 raw, Wi-Fi AP Mine-Rover-AP", "Remote inspect; separate radio"],
        ],
    )

    # flow boxes
    labels = [
        (NAVY, "Node A\nNode B"),
        (TEAL, "S3-Zero\nUSB JSON"),
        (NAVY, "Validate\n+ features"),
        (TEAL, "Rules +\nIF + Ridge"),
        (ORANGE, "Dashboard\n127.0.0.1"),
        (GOLD, "Rover AP\ninspect"),
    ]
    y = Inches(3.08)
    x = Inches(0.35)
    for i, (fill, txt) in enumerate(labels):
        add_box(s, x, y, Inches(1.7), Inches(0.72), fill)
        add_text_box(s, x, y + Inches(0.08), Inches(1.7), Inches(0.6), txt.split("\n"), size=11, bold=True, color=WHITE, align=PP_ALIGN.CENTER)
        if i < len(labels) - 1:
            add_text_box(s, x + Inches(1.62), y + Inches(0.18), Inches(0.28), Inches(0.35), ["→"], size=16, bold=True, color=NAVY, align=PP_ALIGN.CENTER)
        x += Inches(2.05)

    add_table(
        s,
        Inches(0.35),
        Inches(3.92),
        Inches(12.6),
        Inches(2.1),
        [
            ["Engine", "Input (after validation)", "Output shown to officer"],
            ["Rules (latch)", "tilt_change, crack mm, freshness, 3 consecutive samples", "NORMAL / WATCH (3° or 2 mm) / ALERT (6° or 4 mm) / UNKNOWN (>5 s)"],
            ["Isolation Forest", "≥120 live NORMAL samples/node; tilt, vib, d_tilt, optional mm, A–B residual", "INACTIVE | READY | UNUSUAL + score + top feature"],
            ["Ridge 30 s", "Last ~30 accepted points of the same series", "Dashed forecast + MAE. Label: Sensor forecast (30 s). Not a collapse prediction."],
        ],
    )


def fill_slide4(prs):
    s = prs.slides[3]
    set_team_oval(s)
    for sh in s.shapes:
        if sh.has_text_frame and "Analysis of the feasibility" in sh.text_frame.text:
            hide_shape(sh)

    add_text_box(
        s,
        Inches(0.35),
        Inches(1.12),
        Inches(12.6),
        Inches(0.4),
        ["Feasible as a tabletop SIH hardware demo: parts in hand, firmware + local website in repo. Field mine certification is out of scope."],
        size=13,
        bold=True,
        color=NAVY,
    )

    add_table(
        s,
        Inches(0.35),
        Inches(1.55),
        Inches(6.15),
        Inches(2.35),
        [
            ["Feasibility check", "Status"],
            ["Boards + sensors for A, B, rover, S3-Zero", "Available"],
            ["Node radio", "ESP-NOW ch1, tabletop range only"],
            ["ML on venue laptop", "Train 2 min quiet NORMAL before judges"],
            ["Operator UI", "Local Flask, no cloud, no login"],
            ["Demo loop", "Quiet → disturb → WATCH/ALERT → rover → ack"],
        ],
    )

    add_table(
        s,
        Inches(6.7),
        Inches(1.55),
        Inches(6.25),
        Inches(2.35),
        [
            ["If this happens", "Fallback"],
            ["ESP-NOW / USB drop", "UNKNOWN, never fake-green"],
            ["Not enough NORMAL samples", "AI stays INACTIVE; rules still run"],
            ["Need UI without hardware", "--mode simulate, banner on"],
            ["Rover page dies", "Firmware STOP if no cmd ~400 ms"],
            ["Slider uncalibrated", "Node A mm omitted; no fake gap"],
        ],
    )

    add_text_box(s, Inches(0.35), Inches(4.0), Inches(12.6), Inches(0.26), ["Risks and how we contain them (no budget theatre)"], size=12, bold=True, color=NAVY)
    add_table(
        s,
        Inches(0.35),
        Inches(4.28),
        Inches(12.6),
        Inches(1.75),
        [
            ["Risk", "Why it is real", "Strategy"],
            ["Over-claiming the PS", "Tilt ≠ settlement in cm; IF ≠ collapse probability", "Fixed honesty table on dashboard + this PPT"],
            ["Mixing rover with nodes", "Moving IMU would poison Node B / IF", "device_id rover; never in node models"],
            ["False comfort", "Disconnected sensor looking healthy", "Stale >5 s → UNKNOWN; ML cannot clear a latch"],
            ["Radio is unencrypted broadcast", "Fine for a model; not a mine network", "Say tabletop only; no LoRa / mesh claim"],
        ],
    )


def fill_slide5(prs):
    s = prs.slides[4]
    set_team_oval(s)
    for sh in s.shapes:
        if sh.has_text_frame and "Potential impact" in sh.text_frame.text:
            hide_shape(sh)

    add_text_box(
        s,
        Inches(0.35),
        Inches(1.12),
        Inches(12.6),
        Inches(0.45),
        ["Target on demo day: a mine safety officer on a tabletop model. Ministry of Coal is the PS owner. Impact = better notice + evidence + remote look — not disaster prevention numbers we cannot prove."],
        size=13,
        bold=True,
        color=NAVY,
    )

    boxes = [
        (NAVY, "Who", "Officer sees Node A vs Node B, rule reason, AI score, forecast MAE, then drives the rover because a warning appeared."),
        (TEAL, "Social", "Fewer unnecessary entries into the model tunnel; decision stays with the human. Ack records awareness; it does not wipe history."),
        (ORANGE, "Operational", "One laptop website. USB nodes still work if venue Wi-Fi is bad. Rover uses its own AP."),
        (GREEN, "Environment / limits", "Hobby electronics on a model. Not intrinsically safe, not DGMS-approved, not a real underground vehicle."),
    ]
    x = Inches(0.35)
    for fill, title, body in boxes:
        add_box(s, x, Inches(1.65), Inches(3.05), Inches(2.35), fill)
        add_text_box(s, x + Inches(0.12), Inches(1.72), Inches(2.8), Inches(0.35), [title], size=14, bold=True, color=WHITE)
        add_text_box(s, x + Inches(0.12), Inches(2.12), Inches(2.8), Inches(1.75), [body], size=12, color=WHITE)
        x += Inches(3.2)

    add_table(
        s,
        Inches(0.35),
        Inches(4.15),
        Inches(12.6),
        Inches(1.9),
        [
            ["Benefit we can show", "How a judge verifies it", "Not a benefit we invent"],
            ["Earlier notice of disturbance", "Tilt/slider move → WATCH then latched ALERT in ~3 s", "Lives saved / disasters averted"],
            ["Evidence, not a vibe", "Charts + A-vs-B sentence + IF feature + Ridge MAE", "87% collapse risk"],
            ["Inspect without replacing monitors", "Rover telemetry while A/B keep streaming", "Autonomous rescue robot"],
            ["Honest scale path", "Same workflow; surveyed mounts + labelled events later", "This prototype already predicts subsidence"],
        ],
    )


def fill_slide6(prs):
    s = prs.slides[5]
    set_team_oval(s)
    for sh in s.shapes:
        if sh.has_text_frame and "Details / Links of the reference" in sh.text_frame.text:
            hide_shape(sh)

    add_text_box(
        s,
        Inches(0.35),
        Inches(1.12),
        Inches(12.6),
        Inches(0.4),
        ["References used to design the demo — not proof that MOLE is a certified mine instrument."],
        size=13,
        bold=True,
        color=NAVY,
    )

    add_table(
        s,
        Inches(0.35),
        Inches(1.52),
        Inches(12.6),
        Inches(3.55),
        [
            ["Item", "Why it is here", "Link / citation"],
            ["PS SIH26025", "Official catalogue ID (not SIH2026025)", "SIH 2026 portal / Ministry of Coal, Hardware, Disaster Management"],
            ["Isolation Forest", "Anomaly vs this rig’s normal", "Liu, Ting, Zhou — Isolation Forest, IEEE ICDM 2008"],
            ["Ridge forecast", "Short-horizon prediction of measured signals", "scikit-learn Ridge; MAE on a held recent window"],
            ["MPU6050", "Gravity tilt + RMS vibration proxy", "InvenSense MPU-6000/6050 Product Specification"],
            ["ESP-NOW", "Node radio on channel 1, tabletop", "Espressif ESP-NOW User Guide"],
            ["ESP32-S3-Zero", "USB CDC receiver, no sensors", "Waveshare ESP32-S3-Zero wiki"],
            ["MQ-7", "Rover inspection only, raw ADC", "Winsen/Hanwei MQ-7 datasheet — we do not output ppm"],
            ["Problem domain", "Why coal mines care about movement", "Ministry of Coal / DGMS published guidance on subsidence & strata — context only"],
        ],
    )

    add_box(s, Inches(0.35), Inches(5.18), Inches(12.6), Inches(0.85), PALE, LINE)
    add_text_box(
        s,
        Inches(0.5),
        Inches(5.25),
        Inches(12.3),
        Inches(0.72),
        [
            "One-line close: MOLE is a working tabletop loop — nodes detect, rules latch, Isolation Forest + Ridge explain, rover inspects.",
            "Upload as PDF. Team ID: fill after portal. Delete no extra slides — this file is already 6.",
        ],
        size=12,
        color=NAVY,
    )


def main():
    prs = Presentation(str(SRC))
    fill_slide1(prs)
    fill_slide2(prs)
    fill_slide3(prs)
    fill_slide4(prs)
    fill_slide5(prs)
    fill_slide6(prs)
    delete_slide(prs, 6)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUT))
    print("saved", OUT, "slides", len(prs.slides))


if __name__ == "__main__":
    main()
