"""Build the formal SIH26025 judge document (DOCX). Export PDF with Word COM."""
from __future__ import annotations

from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\brith\Desktop\mole")
PITCH = ROOT / "pitch"
ASSETS = PITCH / "assets"
OUT_DOCX = PITCH / "SIH26025_WE_COOK_MOLE_Judge_Document.docx"
OUT_DL = Path(r"C:\Users\brith\Downloads\SIH26025_WE_COOK_MOLE_Judge_Document.docx")

NAVY = RGBColor(0x0B, 0x2C, 0x4A)
ORANGE = RGBColor(0xF4, 0x7B, 0x20)
TEAL = RGBColor(0x0E, 0x7C, 0x7B)
INK = RGBColor(0x1A, 0x1A, 0x1A)
MUTED = RGBColor(0x4A, 0x55, 0x63)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
PALE = "F4F7FA"
NAVY_HEX = "0B2C4A"
ORANGE_HEX = "F47B20"
TEAL_HEX = "0E7C7B"

PS_TITLE = (
    "Development of an AI-enabled Low Cost Real Time Mine Subsidence "
    "Monitoring, Prediction and Early Warning System for Underground "
    "Coal Mines in India"
)


def _font(size, bold=False):
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


def make_cover_banner() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    w, h = 2400, 720
    img = Image.new("RGB", (w, h), (11, 44, 74))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 28, h), fill=(244, 123, 32))
    d.text((72, 48), "SMART INDIA HACKATHON 2026", font=_font(36, True), fill=(244, 123, 32))
    d.text((72, 120), "Formal technical document for judges", font=_font(28), fill=(210, 220, 230))
    d.text((72, 220), "MOLE", font=_font(96, True), fill=(255, 255, 255))
    d.text(
        (72, 340),
        "Mine Observation & Live-alert Engine",
        font=_font(36, True),
        fill=(255, 255, 255),
    )
    d.text((72, 420), "Team WE COOK   ·   Problem SIH26025", font=_font(30), fill=(244, 123, 32))
    d.text(
        (72, 490),
        "Ministry of Coal   ·   Hardware   ·   Disaster Management",
        font=_font(26),
        fill=(210, 220, 230),
    )
    d.text(
        (72, 560),
        "Node A + Node B + laptop ML + remote rover + one local dashboard",
        font=_font(24),
        fill=(210, 220, 230),
    )
    d.text((72, 630), "Tabletop demonstration  ·  9 September 2026", font=_font(22), fill=(168, 180, 194))
    path = ASSETS / "cover_banner.png"
    img.save(path, "PNG")
    return path


def set_run_font(run, *, size=11, bold=False, italic=False, color=INK, name="Calibri"):
    run.font.name = name
    run._element.rPr.rFonts.set(qn("w:eastAsia"), name)
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def shade_cell(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    for child in list(tcPr):
        if child.tag == qn("w:shd"):
            tcPr.remove(child)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:fill"), hex_color)
    shd.set(qn("w:val"), "clear")
    tcPr.append(shd)


def set_cell_border(cell, color="D5DEE8") -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{edge}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), color)
        tcBorders.append(el)
    tcPr.append(tcBorders)


def set_cell_text(cell, text, *, size=10, bold=False, color=INK, align="left"):
    cell.text = ""
    p = cell.paragraphs[0]
    p.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }.get(align, WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, color=color)


def prevent_row_split(row) -> None:
    tr = row._tr
    trPr = tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit")
    trPr.append(cant)


def add_table(doc, headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, h in enumerate(headers):
        cell = table.rows[0].cells[i]
        shade_cell(cell, NAVY_HEX)
        set_cell_border(cell)
        set_cell_text(cell, h, size=10, bold=True, color=WHITE)
    prevent_row_split(table.rows[0])
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            cell = table.rows[r + 1].cells[c]
            shade_cell(cell, "FFFFFF" if r % 2 == 0 else PALE)
            set_cell_border(cell)
            set_cell_text(cell, value, size=10, bold=c == 0)
        prevent_row_split(table.rows[r + 1])
    if col_widths:
        for row in table.rows:
            for i, width in enumerate(col_widths):
                row.cells[i].width = Cm(width)
    doc.add_paragraph()
    return table


def para(
    doc,
    text,
    *,
    size=11,
    bold=False,
    italic=False,
    color=INK,
    space_after=8,
    align="left",
):
    p = doc.add_paragraph()
    p.alignment = {
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "right": WD_ALIGN_PARAGRAPH.RIGHT,
    }.get(align, WD_ALIGN_PARAGRAPH.LEFT)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    run = p.add_run(text)
    set_run_font(run, size=size, bold=bold, italic=italic, color=color)
    return p


def bullets(doc, items, *, size=11):
    for item in items:
        p = doc.add_paragraph(item, style="List Bullet")
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.left_indent = Cm(1.0)
        for run in p.runs:
            set_run_font(run, size=size)


def caption(doc, text):
    para(doc, text, size=9, italic=True, color=MUTED, space_after=12, align="center")


def add_picture(doc, path: Path, width_cm=16.5):
    if not path.exists():
        para(doc, f"[Figure missing: {path.name}]", italic=True, color=MUTED)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run()
    run.add_picture(str(path), width=Cm(width_cm))


def heading(doc, text, level=1):
    p = doc.add_heading(text, level=level)
    for run in p.runs:
        run.font.color.rgb = NAVY
        run.font.name = "Calibri"
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    return p


def page_break(doc):
    doc.add_page_break()


def add_page_number(paragraph):
    run1 = paragraph.add_run("Page ")
    set_run_font(run1, size=9, color=MUTED)
    fld1 = OxmlElement("w:fldChar")
    fld1.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = " PAGE "
    fld2 = OxmlElement("w:fldChar")
    fld2.set(qn("w:fldCharType"), "end")
    r2 = paragraph.add_run()
    r2._r.append(fld1)
    r2._r.append(instr)
    r2._r.append(fld2)
    set_run_font(r2, size=9, color=MUTED)
    run3 = paragraph.add_run(" of ")
    set_run_font(run3, size=9, color=MUTED)
    fld3 = OxmlElement("w:fldChar")
    fld3.set(qn("w:fldCharType"), "begin")
    instr2 = OxmlElement("w:instrText")
    instr2.set(qn("xml:space"), "preserve")
    instr2.text = " NUMPAGES "
    fld4 = OxmlElement("w:fldChar")
    fld4.set(qn("w:fldCharType"), "end")
    r4 = paragraph.add_run()
    r4._r.append(fld3)
    r4._r.append(instr2)
    r4._r.append(fld4)
    set_run_font(r4, size=9, color=MUTED)


def setup_header_footer(doc):
    section = doc.sections[0]
    section.different_first_page_header_footer = True
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.left_margin = Cm(2.0)
    section.right_margin = Cm(2.0)
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.header_distance = Cm(0.8)
    section.footer_distance = Cm(0.8)

    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.clear()
    r = hp.add_run("WE COOK  ·  SIH26025  ·  MOLE — Mine Observation & Live-alert Engine")
    set_run_font(r, size=9, bold=True, color=NAVY)

    footer = section.footer
    footer.is_linked_to_previous = False
    table = footer.add_table(1, 2, width=Cm(17.0))
    table.autofit = True
    left, right = table.rows[0].cells
    left.text = ""
    lp = left.paragraphs[0]
    lr = lp.add_run("Formal document for judges  ·  not the 6-slide SIH portal PDF")
    set_run_font(lr, size=8, color=MUTED)
    right.text = ""
    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_page_number(rp)

    # Colour the footer number area with a simple navy line via header bottom border
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), NAVY_HEX)
    pBdr.append(bottom)
    hp._p.get_or_add_pPr().append(pBdr)


def setup_styles(doc):
    styles = doc.styles
    normal = styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(11)
    normal.font.color.rgb = INK
    normal.paragraph_format.space_after = Pt(8)
    for name, size in (("Heading 1", 16), ("Heading 2", 13), ("Heading 3", 12)):
        st = styles[name]
        st.font.name = "Calibri"
        st.font.bold = True
        st.font.color.rgb = NAVY
        st.font.size = Pt(size)


def add_toc(doc):
    para(doc, "Contents", size=16, bold=True, color=NAVY, space_after=6)
    p = doc.add_paragraph()
    run = p.add_run()
    fldBegin = OxmlElement("w:fldChar")
    fldBegin.set(qn("w:fldCharType"), "begin")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = r' TOC \o "1-2" \h \z \u '
    fldSeparate = OxmlElement("w:fldChar")
    fldSeparate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Right-click and choose Update Field if the list is empty."
    fldEnd = OxmlElement("w:fldChar")
    fldEnd.set(qn("w:fldCharType"), "end")
    run._r.append(fldBegin)
    run._r.append(instr)
    run._r.append(fldSeparate)
    run._r.append(placeholder)
    run._r.append(fldEnd)


def callout(doc, title, body, hex_color=ORANGE_HEX):
    table = doc.add_table(rows=1, cols=1)
    cell = table.rows[0].cells[0]
    shade_cell(cell, PALE)
    set_cell_border(cell, hex_color)
    cell.text = ""
    p1 = cell.paragraphs[0]
    r1 = p1.add_run(title)
    set_run_font(r1, size=11, bold=True, color=NAVY)
    p2 = cell.add_paragraph()
    r2 = p2.add_run(body)
    set_run_font(r2, size=10, color=INK)
    doc.add_paragraph()


def build() -> Path:
    banner = make_cover_banner()
    doc = Document()
    setup_styles(doc)
    setup_header_footer(doc)
    core = doc.core_properties
    core.title = "MOLE — Formal Technical Document for Judges (SIH26025)"
    core.author = "Team WE COOK"
    core.subject = "Smart India Hackathon 2026 · SIH26025 · Ministry of Coal"
    core.category = "Hardware · Disaster Management"
    core.comments = "Tabletop demonstration. Not a certified mine system."

    # --- Cover ---
    add_picture(doc, banner, width_cm=17.0)
    para(doc, "Idea / prototype document for institute screening and SIH judges", size=12, italic=True, color=MUTED, align="center")

    add_table(
        doc,
        ["Field", "Value"],
        [
            ["Event", "Smart India Hackathon 2026"],
            ["Official problem ID", "SIH26025  (never write SIH2026025)"],
            ["Problem title", PS_TITLE],
            ["Organisation", "Ministry of Coal"],
            ["Category", "Hardware"],
            ["Theme", "Disaster Management"],
            ["Team name (portal)", "WE COOK"],
            ["Team ID", "To be filled from the SIH portal after nomination"],
            ["Idea name", "MOLE — Mine Observation & Live-alert Engine"],
            ["Public code", "https://github.com/Rithvik-7/WECOOK-MOLE"],
            ["Document date", "9 September 2026"],
            ["Related portal file", "PDF of the official 6-slide idea template only"],
        ],
        col_widths=[4.5, 12.0],
    )

    callout(
        doc,
        "How to submit",
        "Upload only the official 6-slide idea PDF on the SIH portal. This longer document is for judges, the institute SPOC, and the team. It explains the same product in full. It is not a seventh slide and it is not a substitute for the template PDF.",
    )
    callout(
        doc,
        "Honesty, in one paragraph",
        "MOLE is a working tabletop demonstration. Two fixed nodes watch tilt, vibration, and (on Node A) a crack slider. The laptop runs rule-based early warning plus Isolation Forest and a 30-second sensor forecast. An officer can then drive a rover to look more closely. Readings can show disturbance on this model. They do not prove a collapse, name its cause, or certify that a real mine is safe.",
        TEAL_HEX,
    )

    page_break(doc)
    add_toc(doc)

    # --- 1 ---
    heading(doc, "1. Identification")
    para(
        doc,
        "This document describes MOLE as built for Smart India Hackathon 2026. "
        "The catalogue ID is SIH26025. That is SIH 2026 problem 025. "
        "Judges, catalogues, and the six-slide template match SIH26025. "
        "The string SIH2026025 is not the official ID and must not appear on the portal or the idea PPT.",
        align="justify",
    )
    para(
        doc,
        "The team name registered for this idea is WE COOK. The GitHub repository name is WECOOK-MOLE. "
        "Team ID is issued by the SIH portal after institute nomination and should be written on the title slide when it exists. "
        "Member names are not required on the official six-slide PPT. A roster table is in Annex D for institute use.",
        align="justify",
    )

    heading(doc, "2. Executive summary")
    para(
        doc,
        "Underground mining can change the ground above it. Officers need a simple way to notice a change, see the evidence, and inspect without walking in first. "
        "MOLE answers that need on a tabletop model.",
        align="justify",
    )
    para(doc, "The product is one system, not a pile of parts:", align="justify")
    bullets(
        doc,
        [
            "Node A (fixed): tilt, vibration, and a crack slider.",
            "Node B (fixed): comparison tilt and vibration. It is not a surveyed geodetic reference.",
            "USB receiver: Waveshare ESP32-S3-Zero. It only forwards node packets as JSON.",
            "Laptop ML and rules: Isolation Forest + Local Outlier Factor, a joint A–B forest, and a 30-second sensor-trend forecast. Rules latch the early warning. ML cannot clear a red warning.",
            "Dashboard: one local website on the laptop. No login. No cloud.",
            "Rover (core unit): remote drive and inspect on its own Wi-Fi access point. Not autonomous. Not on the node USB radio.",
        ],
    )
    para(
        doc,
        "Pitch order for judges: show continuous monitoring and evidence first, then drive the rover because a warning appeared. "
        "Do not pitch MOLE as a gas-car maze robot. Do not pitch sensors with a decorative “AI” badge. Machine learning is a core pillar of SIH26025 (AI-enabled and prediction).",
        align="justify",
    )

    heading(doc, "3. Official problem statement")
    para(doc, "Title (as catalogued):", bold=True, space_after=4)
    para(doc, PS_TITLE, italic=True, size=12, color=NAVY)
    add_table(
        doc,
        ["PS word", "What the problem asks", "What MOLE shows on the table"],
        [
            ["AI-enabled", "Use AI, not only raw sensors", "Named sklearn models, features, score, and a written reason from numbers"],
            ["Low cost", "A practical student / field-style kit", "ESP32-class boards the team already has; no cloud bill"],
            ["Real time", "Live readings, not a later report", "About one summarised packet per second per node; dashboard updates live"],
            ["Monitoring", "Watch the site continuously", "Two fixed nodes; rover does not replace them"],
            ["Prediction", "Look a short way ahead", "Next 30 seconds of tilt / vibration / crack millimetres, with MAE — not collapse %"],
            ["Early warning", "A clear alarm the officer can act on", "WATCH then latched ALERT from rules; AI cannot clear the latch"],
            ["Underground coal mines", "A mine safety context", "Ministry of Coal PS; demonstration is a tabletop model, not a certified mine"],
        ],
        col_widths=[3.2, 6.4, 6.9],
    )

    heading(doc, "4. Proposed solution")
    para(
        doc,
        "MOLE helps a mine safety officer notice a concerning change, understand the evidence, and inspect remotely on a tabletop model. "
        "Fixed nodes keep watching while the rover, if used, looks in a different place.",
        align="justify",
    )
    add_picture(doc, ASSETS / "solution_flow.png", 16.8)
    caption(doc, "Figure 1. Three jobs, one product: monitor, warn and predict, then inspect.")

    heading(doc, "4.1 How it works, in plain steps")
    bullets(
        doc,
        [
            "Node A and Node B sample their MPU6050 about 80 times a second and send one summary packet per second over ESP-NOW channel 1.",
            "The Waveshare ESP32-S3-Zero receives those packets and prints one JSON object per line on USB at 115200 baud. It has no sensors and does not run AI.",
            "The laptop checks that the packet is usable (fresh, valid ID, valid IMU, Node A slider calibrated).",
            "The laptop compares tilt with the officer’s baseline: sqrt((roll−roll0)² + (pitch−pitch0)²). Node A slider ADC becomes millimetres after a two-point ruler calibration.",
            "Rules need three readings in a row. WATCH is 3° or 2 mm. ALERT is 6° or 4 mm and it latches. No packet for 5 seconds is UNKNOWN — never a fake green light.",
            "Isolation Forest + LOF say whether this combination looks unusual versus this rig’s normal. A joint forest watches A versus B. A holdout-selected regression forecasts the next 30 seconds of the same signals and shows MAE.",
            "The monitoring page explains both the rule and the models. Drive controls stay on a separate rover page so monitoring is not a gamepad.",
            "If the officer decides to inspect, the laptop joins Mine-Rover-AP and proxies hold-to-move commands. The rover reports distance, an IR flag, MQ-7 raw ADC, and rover IMU. Rover vibration is never treated as Node B.",
        ],
    )

    heading(doc, "4.2 What we do not claim")
    add_table(
        doc,
        ["Allowed on this demo", "Not allowed"],
        [
            ["NORMAL / WATCH / ALERT / UNKNOWN on this rig", "“The mine is safe / certified / collapse imminent”"],
            ["Isolation Forest score and top feature versus this tabletop’s normal", "Collapse or subsidence probability"],
            ["30 s forecast of tilt / vibration / crack mm + MAE", "“Roof will fail in N minutes” as a geotech claim"],
            ["MQ-7 raw ADC and a local NORMAL/HIGH flag", "CO ppm from an uncalibrated MQ-7"],
            ["IR digital flag (LOW = near). It does not stop motors", "Collision avoidance, lidar, or auto-brake"],
            ["Remote FWD / REV / LEFT / RIGHT / STOP", "Autonomous navigation"],
            ["Operator-driven inspection", "Camera vision, LLM geology, login, cloud, or LoRa"],
        ],
        col_widths=[8.2, 8.3],
    )

    heading(doc, "5. Innovation and uniqueness")
    bullets(
        doc,
        [
            "One product, two radios. Nodes use ESP-NOW into USB. The rover uses its own Wi-Fi AP. Mixing those paths would poison the comparison story and the ML features.",
            "Rules and ML sit side by side. The latch is independent. Isolation Forest cannot talk a red warning back to green.",
            "Prediction is honest. The dashboard label is a 30-second sensor-trend forecast, not a collapse prediction. MAE is visible.",
            "Node B is a comparison location, not a fake surveyed monument. Joint Isolation Forest uses |A−B| tilt and vibration, not a geology model.",
            "Green means fresh valid data and no configured tabletop trigger. It does not certify a mine.",
            "Simulation is permanently labelled and cannot persist-train Isolation Forest. Live USB never silently fakes data.",
        ],
    )

    heading(doc, "6. System architecture")
    para(
        doc,
        "Intelligence is split on purpose. ESP32 boards measure and send. The laptop calibrates, stores, compares A with B, runs rules and ML, and draws the website. Rover driving is remote, not autonomous.",
        align="justify",
    )
    add_picture(doc, ASSETS / "architecture_lanes.png", 16.8)
    caption(doc, "Figure 2. Monitor path (ESP-NOW → S3-Zero USB → laptop) is separate from inspect path (Mine-Rover-AP).")

    heading(doc, "7. Hardware")
    para(
        doc,
        "The team already has the parts. This freeze is the as-built contract. Do not invent a different board, pin, or radio for the pitch.",
        align="justify",
    )
    add_table(
        doc,
        ["Unit", "MCU", "Job", "Radio"],
        [
            ["Node A", "Classic ESP32-WROOM-32 DevKit", "Tilt + vibration + crack slider", "ESP-NOW channel 1 broadcast"],
            ["Node B", "Same DevKit", "Comparison tilt + vibration, no slider", "ESP-NOW channel 1 broadcast"],
            ["Receiver", "Waveshare ESP32-S3-Zero (ESP32-S3FH4R2)", "ESP-NOW → USB-C JSON 115200. No sensors", "STA, channel 1"],
            ["Rover", "Classic ESP32-WROOM-32 DevKit", "Drive + inspect", "Wi-Fi AP Mine-Rover-AP only"],
        ],
        col_widths=[2.8, 4.6, 5.4, 3.7],
    )
    para(
        doc,
        "The receiver is not a classic ESP32 and not an ESP32-S2. In Arduino IDE choose Waveshare ESP32-S3-Zero or ESP32S3 Dev Module, and set USB CDC On Boot = Enabled. Native USB, not a CH340 adapter.",
        align="justify",
    )

    heading(doc, "7.1 Node A and Node B")
    para(
        doc,
        "Same sketch family: firmware/node/node.ino (A) and firmware/node_b/node.ino (B). Firmware does not compute millimetres, alerts, or AI.",
        align="justify",
    )
    add_table(
        doc,
        ["Function", "Detail"],
        [
            ["MPU6050", "I²C 0x68, SDA GPIO21, SCL GPIO22, 3.3 V, AD0 to GND"],
            ["Node A slider", "10 kΩ linear pot, SIG → 1 kΩ → GPIO34 (ADC1). Never 5 V into the ADC. NODE_ID=1, HAS_POT=1"],
            ["Node B slider", "Not fitted. sliderRaw = −1. NODE_ID=2, HAS_POT=0"],
            ["Sample rate", "MPU about 80 Hz (SAMPLE_US 12500); one summarised packet per second"],
            ["Broadcast", "ESP-NOW FF:FF:FF:FF:FF:FF on channel 1. Unencrypted. Tabletop range only"],
            ["valid bitmask", "IMU=1, potentiometer=2, vibration window=4. Healthy A=7, healthy B=5. Invalid fields are JSON null, never 0"],
            ["Tilt on the laptop", "sqrt((roll−roll0)² + (pitch−pitch0)²) after the officer captures a baseline"],
            ["Orientation in firmware", "Gravity roll/pitch. Trustworthy only when the mount is approximately still"],
            ["vibration_g", "RMS residual around the one-second mean. Not a calibrated seismic measure"],
        ],
        col_widths=[4.0, 12.5],
    )

    heading(doc, "7.2 USB receiver")
    bullets(
        doc,
        [
            "Sketch: firmware/receiver_s3/receiver_s3.ino.",
            "Wi-Fi STA forced to channel 1, ESP-NOW receive, size / version / node_id check.",
            "Prints one JSON object per line on USB Serial 115200. May add gateway_ms.",
            "Does not compute tilt-delta, millimetres, rules, or AI.",
            "If upload fails: hold BOOT, tap RESET, release BOOT, then upload.",
        ],
    )

    heading(doc, "7.3 Rover (core unit; radio stays separate)")
    para(
        doc,
        "Sketch: firmware/rover/rover.ino. Access point SSID Mine-Rover-AP, IP 192.168.4.1, open AP in firmware (no password). "
        "Leave L298N ENA/ENB jumpers ON. Firmware stops by setting IN1–IN4 LOW, plus a 400 ms watchdog if no repeated command. "
        "GPIO19 is the IR flag, not a motor pin.",
        align="justify",
    )
    add_table(
        doc,
        ["Function", "Pin / note"],
        [
            ["L298N IN1 / IN2 (left)", "GPIO13 / GPIO12"],
            ["L298N IN3 / IN4 (right)", "GPIO14 / GPIO27"],
            ["MPU6050", "SDA 21 / SCL 22 / 0x68 / 3.3 V"],
            ["HC-SR04 TRIG", "GPIO5"],
            ["HC-SR04 ECHO", "GPIO18 after a 1 kΩ / 2 kΩ divider. ECHO is 5 V — never wire straight in"],
            ["MQ-7 analog", "GPIO36, raw 12-bit ADC. Local HIGH if raw ≥ 2500. Not ppm"],
            ["IR OUT", "GPIO19, INPUT_PULLUP, LOW = obstacle, majority-of-3 debounce. Does not stop motors"],
        ],
        col_widths=[5.5, 11.0],
    )
    add_table(
        doc,
        ["Command", "IN1 IN2 IN3 IN4"],
        [
            ["STOP", "0 0 0 0"],
            ["FWD", "1 0 1 0"],
            ["REV", "0 1 0 1"],
            ["LEFT", "0 1 1 0"],
            ["RIGHT", "1 0 0 1"],
        ],
        col_widths=[6.0, 10.5],
    )
    para(
        doc,
        "If a side runs backward, swap that motor’s two wires. Do not invent new GPIOs. "
        "Rover HTTP GET: /forward /backward /left /right /stop /telemetry /.",
        align="justify",
    )

    heading(doc, "8. Communication design")
    para(
        doc,
        "Node path and rover path must stay separate. The S3-Zero USB path does not carry rover commands or video. "
        "The laptop must join Mine-Rover-AP to drive. Live USB drop is retried every 2 s; nodes become UNKNOWN after 5 s without a valid packet. Live mode never falls back to simulation.",
        align="justify",
    )
    add_table(
        doc,
        ["Path", "Medium", "Payload", "Must not"],
        [
            ["Nodes → laptop", "ESP-NOW ch1 → S3-Zero → USB JSON 115200", "Node A/B summaries", "Carry rover drive or video"],
            ["Laptop → rover", "Wi-Fi AP Mine-Rover-AP, HTTP", "Drive commands + inspect telemetry", "Enter node ML features"],
        ],
        col_widths=[3.6, 5.4, 4.2, 3.3],
    )

    heading(doc, "9. Software")
    para(
        doc,
        "Stack: Python 3, Flask, SQLite, scikit-learn on the laptop only, pyserial, joblib, pytest. No accounts, no npm, no CDN required. Charts are canvas, not Chart.js from the internet. Server binds 127.0.0.1:5000.",
        align="justify",
    )
    add_table(
        doc,
        ["Module", "Responsibility"],
        [
            ["app.py", "Flask app, USB thread, rover poll thread, HTTP routes"],
            ["engine.py", "Lock, ingest, freshness, baselines, snapshot JSON, forecast cache"],
            ["models.py", "Telemetry / RoverTelemetry, schema 1 parse"],
            ["serial_reader.py", "COM port, readline JSON, auto / COMx"],
            ["simulate.py", "Node scenarios + SimulatedRover"],
            ["database.py", "SQLite packets/events, CSV export tagged live/sim"],
            ["calibration.py", "Two-point ADC → mm"],
            ["rules.py", "WATCH / ALERT / UNKNOWN, persist 3, latch, ack ≠ clear"],
            ["features.py", "Per-node vectors + joint residual vector"],
            ["anomaly.py", "Per-node Isolation Forest + LOF; prior/live joblib"],
            ["forecast.py", "Ridge / Huber / LinearRegression vs persistence; 30-point horizon"],
            ["explain.py", "Template reasons from numbers (not an LLM)"],
            ["rover_client.py", "HTTP to http://192.168.4.1"],
            ["rover_sense.py", "Honest IR vs ultrasonic copy (stops_motors: false)"],
            ["train_prior.py", "Shipped tabletop *.prior.joblib files"],
            ["helper.py", "Optional local FAQ / Ollama helper named Pip. Not the product mine-AI"],
        ],
        col_widths=[3.6, 12.9],
    )
    para(
        doc,
        "Pages: Monitoring + AI at /monitoring (also /). Rover Inspection at /rover. Drive controls must not appear on the monitoring page. "
        "Simulate shows a permanent Rehearsal bar and cannot POST /api/train. Tabletop prior models still load so Isolation Forest can be READY without waiting 120 live samples. "
        "Those priors describe a quiet tabletop, not a real mine, and the UI labels them as a tabletop prior.",
        align="justify",
    )
    para(
        doc,
        "Pip, if shown, answers from a local handbook and FAQ. Product AI remains sklearn. A helper chatbot is not the SIH “AI-enabled” claim.",
        align="justify",
    )

    heading(doc, "9.1 HTTP API (laptop)")
    add_table(
        doc,
        ["Method", "Path", "Notes"],
        [
            ["GET", "/  /monitoring  /rover", "HTML pages"],
            ["GET", "/api/state", "Full monitoring snapshot"],
            ["GET", "/api/export.csv", "History, tagged live or sim"],
            ["POST", "/api/baseline", "{node_id: 1 or 2}"],
            ["POST", "/api/ack", "Awareness only; does not erase history"],
            ["POST", "/api/clear", "Needs 3 recovered NORMAL samples; 409 if not"],
            ["POST", "/api/train", "Live only; ≥120 NORMAL; blocked if WATCH/ALERT/UNKNOWN/sim"],
            ["POST", "/api/calibration", "adc0, adc1, mm0, mm1 — distinct ADC"],
            ["POST", "/api/scenario", "Simulate only: normal, rising, watch, alert, offline, sensor_fault"],
            ["POST", "/api/rover/<cmd>", "forward, backward, left, right, stop"],
            ["GET", "/api/rover/state", "Rover telemetry + IR explanation"],
        ],
        col_widths=[2.4, 4.6, 9.5],
    )

    heading(doc, "10. Early-warning rules")
    para(
        doc,
        "These numbers are tabletop demo thresholds. They are not DGMS trigger levels and they are not a scientific mine rule.",
        align="justify",
    )
    add_picture(doc, ASSETS / "threshold_graph.png", 16.0)
    caption(doc, "Figure 3. Demo tilt bands used on the table. Not a mine safety chart.")
    add_table(
        doc,
        ["Rule", "Tabletop setting"],
        [
            ["WATCH", "Tilt ≥ 3° or crack ≥ 2 mm, 3 consecutive samples"],
            ["ALERT", "Tilt ≥ 6° or crack ≥ 4 mm, 3 consecutive samples; ALERT latches"],
            ["UNKNOWN", "Stale > 5 s, unseen node, invalid IMU, or Node A slider not millimetre-calibrated"],
            ["Ack", "Records that the officer saw it. Does not clear the latch"],
            ["Clear", "Needs 3 fresh NORMAL samples"],
            ["Independence", "Node B never cancels Node A. Isolation Forest cannot clear a rule alert"],
        ],
        col_widths=[4.0, 12.5],
    )

    heading(doc, "11. Machine learning (core product, laptop only)")
    para(
        doc,
        "SIH26025 asks for AI-enabled monitoring and prediction. MOLE puts that on the laptop with scikit-learn. "
        "There is no camera vision model and no LLM geology. Rover IMU, IR, ultrasonic, and MQ-7 are not ML features.",
        align="justify",
    )

    heading(doc, "11.1 Isolation Forest + Local Outlier Factor")
    bullets(
        doc,
        [
            "sklearn IsolationForest (contamination 0.05) + LocalOutlierFactor, with StandardScaler.",
            "Features: tilt_change_deg, vibration_g, d_tilt, and Node A relative_mm once calibrated.",
            "States: INACTIVE / READY / UNUSUAL. The officer sees score, LOF vote, top standardised feature, feature names, and train count.",
            "Optional live retrain writes nodeN.joblib after ≥120 NORMAL samples in live mode. Simulate cannot persist-train.",
            "Shipped artifacts/node1.prior.joblib, node2.prior.joblib, and joint.prior.joblib describe quiet-tabletop NORMAL so a demo can start READY.",
        ],
    )

    heading(doc, "11.2 Joint A–B forest")
    para(
        doc,
        "A third Isolation Forest uses [abs(A_tilt−B_tilt), abs(A_vib−B_vib)]. Patterns such as QUIET / LOCAL_A / LOCAL_B / COMMON help the officer see local versus common motion. This is not a geology model.",
        align="justify",
    )

    heading(doc, "11.3 Thirty-second sensor forecast (the hackathon “prediction”)")
    bullets(
        doc,
        [
            "Window of recent ~1 Hz samples. Candidates: Ridge, HuberRegressor, LinearRegression, versus a persistence baseline.",
            "Holdout MAE picks the winner. Horizon is the next 30 samples of tilt, vibration, and Node A gap.",
            "UI: solid measured line, dashed forecast, error band, MAE, quality, surprise z. Time-to-WATCH/ALERT only if the fitted slope heads toward the threshold.",
            "Quiet data can let LinearRegression win with MAE near 0. That is a flat signal, not magic. Huber may fail to converge; it is a candidate, not sacred.",
            "On-screen label: 30 s sensor trend forecast — not a collapse prediction.",
        ],
    )

    heading(doc, "12. Rover inspection")
    para(
        doc,
        "The rover exists so the officer can look after a warning, not so the product becomes a maze robot. Hold-to-move; release or Space sends STOP. The laptop sends STOP twice to beat in-flight races. Firmware also stops after about 400 ms.",
        align="justify",
    )
    add_table(
        doc,
        ["Sensor", "What the officer sees", "Limit"],
        [
            ["HC-SR04", "Distance ahead in centimetres", "Hobby ultrasonic, not lidar"],
            ["IR", "Digital near flag", "Not a range; does not auto-brake; can disagree with ultrasonic"],
            ["MQ-7", "Raw ADC and local NORMAL/HIGH", "Not carbon monoxide ppm"],
            ["Rover MPU", "Roll / pitch / vibration on the rover", "Never merged into Node B or node ML"],
        ],
        col_widths=[3.2, 6.6, 6.7],
    )
    para(
        doc,
        "In simulation, IR can trip under about 12 cm while ultrasonic “tight” is 25 cm, so they can disagree on purpose. On live hardware the pins are independent.",
        align="justify",
    )

    heading(doc, "13. Operator interface")
    bullets(
        doc,
        [
            "Monitoring + AI: node cards with tilt from baseline, rule status and reason, Isolation Forest evidence, forecast chart with MAE, joint A–B note, event history, CSV export.",
            "Rover Inspection: hold FWD/REV/LEFT/RIGHT, STOP, centimetres, IR explanation, MQ-7 raw, rover IMU, connection status.",
            "Train A/B buttons are disabled in simulate.",
            "Rehearsal “Rising trend” climbs Node A while Node B stays quieter — a judge-friendly forecast and localisation demo.",
        ],
    )
    add_picture(doc, ASSETS / "demo_loop.png", 16.8)
    caption(doc, "Figure 4. One demonstration loop on the table.")

    heading(doc, "14. Data honesty and safety of claims")
    para(
        doc,
        "Green / NORMAL means fresh valid data and no configured tabletop trigger. It does not certify a mine. "
        "Tilt measures orientation change from a captured baseline. It is not vertical ground settlement in centimetres. "
        "Hobby ESP32 / MPU6050 electronics are not intrinsically safe and are not DGMS-approved underground instruments. "
        "ESP-NOW on this model is unencrypted and short-range. Do not claim LoRa, mesh, or colliery networking.",
        align="justify",
    )

    heading(doc, "15. Feasibility and viability")
    para(
        doc,
        "The idea is feasible as a Smart India Hackathon Hardware demonstration this week: boards are with the team, firmware sketches and the local website are in the repository, and simulation works with no hardware. "
        "Mine certification, intrinsically safe equipment, and surveyed geodetic mounts are out of scope.",
        align="justify",
    )
    add_table(
        doc,
        ["Check", "Status"],
        [
            ["Boards for A, B, rover, S3-Zero", "Available with the team"],
            ["Firmware", "In repo (flashing on hardware day still required)"],
            ["Laptop website", "Flask, local, no login, no cloud"],
            ["ML without a long wait", "Tabletop priors load READY; optional live retrain later"],
            ["Demo without boards", "--mode simulate, permanently labelled"],
            ["Radio", "ESP-NOW tabletop; rover AP across the table, not through rock"],
            ["If USB dies", "UNKNOWN. Never fake green"],
            ["If rover Wi-Fi dies", "Motors stop in about 0.4 s"],
        ],
        col_widths=[6.0, 10.5],
    )

    heading(doc, "16. Risks and how we handle them")
    add_table(
        doc,
        ["Risk", "Why it is real", "What we do"],
        [
            ["Over-claiming the PS", "Tilt is not settlement in cm; Isolation Forest is not collapse probability", "Honesty table on the dashboard and in this document"],
            ["Mixing rover with nodes", "A moving IMU would poison Node B and node ML", "device_id rover; never in node models"],
            ["False comfort from a dead sensor", "Silence can look “fine”", "Stale >5 s → UNKNOWN; ML cannot clear a latch"],
            ["Uncalibrated slider", "ADC is not millimetres until two-point cal", "Node A cannot show NORMAL until calibrated"],
            ["IR disagrees with ultrasonic", "Cheap IR is a flag, not a tape measure", "Dashboard explains; IR does not cut motors"],
            ["Hobby electronics underground", "Not approved for a real mine atmosphere", "Table model only. Field needs approved gear"],
        ],
        col_widths=[4.0, 6.3, 6.2],
    )

    heading(doc, "17. Impact and benefits")
    para(
        doc,
        "The user on demo day is a mine safety officer on a tabletop model. The Ministry of Coal owns the problem statement. "
        "Impact we can defend is notice + evidence + a remote look — not disaster-prevention numbers we cannot prove.",
        align="justify",
    )
    add_table(
        doc,
        ["Benefit a judge can verify", "How", "Not a benefit we invent"],
        [
            ["See A vs B at the same time", "Two node cards, joint forest", "A real mine network"],
            ["See why a warning latched", "Rule reason in words from numbers", "Certified early warning"],
            ["See AI evidence", "Model names, features, score, MAE", "Collapse %"],
            ["Inspect without entering the model tunnel first", "Open rover page after a warning", "Autonomous rescue robot"],
            ["Keep a record", "Ack, history, CSV", "Erasing the event by clicking Ack"],
            ["Run without venue internet", "127.0.0.1 Flask; USB nodes still work if Wi-Fi is bad", "Cloud operations centre"],
        ],
        col_widths=[5.2, 5.4, 5.9],
    )

    heading(doc, "18. Demonstration protocol for judges")
    bullets(
        doc,
        [
            "Start simulate or live. Show both nodes updating. State SIH26025: monitor → warn → inspect.",
            "Show model names, train count or “Tabletop prior”, features, forecast MAE. Say it is not collapse %.",
            "Use Rising trend, or physically tilt Node A. Keep Node B quieter. That is localised evidence.",
            "WATCH then ALERT with the measured reason. Rules and ML side by side.",
            "Open Rover Inspection because a warning appeared.",
            "Raise wheels first. Hold FWD, then STOP. Show centimetres, IR flag, MQ-7 raw. IR does not auto-brake.",
            "Ack. Recover the mounts. Clear after three NORMAL samples. History still lists the event.",
        ],
    )
    para(
        doc,
        "Spoken close: Isolation Forest + LOF flag unusual combinations versus this rig’s learned normal. "
        "A joint forest watches A vs B residual. Holdout-selected sklearn regression forecasts the next 30 seconds of those same signals with MAE. "
        "Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy.",
        align="justify",
    )

    heading(doc, "19. Implementation status (9 September 2026)")
    add_table(
        doc,
        ["Done in this repository", "Still required on hardware day"],
        [
            ["Firmware sketches for four boards", "Wire to the frozen pin map (especially echo divider and GPIO19 = IR)"],
            ["Flask two-page website", "Flash four sketches in Arduino IDE"],
            ["Rules, IF+LOF+joint, holdout forecast, priors", "Serial Monitor on S3-Zero: JSON for node_id 1 and 2 at 115200"],
            ["Simulate scenarios, rover proxy, IR honesty, CSV", "python app.py --mode live --serial auto (or COMx)"],
            ["Contract tests (25) in test_app.py and test_complete.py", "Baseline A/B + slider two-point calibration"],
            ["Official 6-slide idea PPT + this document", "Join Mine-Rover-AP, polarity test, STOP watchdog, IR/ultrasonic sanity"],
        ],
        col_widths=[8.2, 8.3],
    )
    para(
        doc,
        "SIH26025 is a Hardware problem. Extra sklearn does not replace working boards. Firmware exists in the repo but was not necessarily already flashed on the team’s boards when this document was written.",
        align="justify",
    )

    heading(doc, "20. How to run the prototype")
    para(doc, "Without hardware (rehearsal):", bold=True, space_after=4)
    para(doc, "cd software", size=10)
    para(doc, "python -m pip install -r requirements.txt", size=10)
    para(doc, "python app.py --mode simulate", size=10)
    para(doc, "Then open http://127.0.0.1:5000/monitoring and http://127.0.0.1:5000/rover", size=10, space_after=10)
    para(doc, "With hardware:", bold=True, space_after=4)
    bullets(
        doc,
        [
            "Flash Node A, Node B, S3-Zero (USB CDC On Boot Enabled), and rover.",
            "Confirm JSON for node_id 1 and 2 in Serial Monitor at 115200. Close Serial Monitor before starting Python.",
            "python app.py --mode live --serial auto   (or --serial COM5).",
            "Capture Baseline A and Baseline B while still. Calibrate the Node A slider with two ruler points.",
            "Join Mine-Rover-AP. Raise wheels. Test FWD/STOP. Confirm centimetres, IR, MQ-7 raw.",
        ],
    )
    para(doc, "python -m pytest -q   from the software folder runs the contract tests.", size=11)

    heading(doc, "21. Research and references")
    para(
        doc,
        "Only items we actually use, plus published mine-safety context labelled as context only. No invented accident statistics.",
        align="justify",
    )
    add_table(
        doc,
        ["Item", "Why it is here", "Citation / link"],
        [
            ["PS SIH26025", "Official catalogue ID", "SIH 2026 portal · Ministry of Coal · Hardware · Disaster Management"],
            ["Isolation Forest", "Anomaly versus this rig’s normal", "Liu, Ting, Zhou — Isolation Forest, IEEE ICDM 2008"],
            ["30 s forecast", "Short-horizon prediction of measured signals", "scikit-learn Ridge / Huber / LinearRegression; holdout MAE"],
            ["MPU6050", "Gravity tilt + RMS vibration proxy", "InvenSense MPU-6000/6050 Product Specification"],
            ["ESP-NOW + ADC1", "Node radio ch1; slider on GPIO34", "Espressif ESP-NOW User Guide; ESP32 ADC notes (ADC1, not ADC2 with Wi-Fi)"],
            ["ESP32-S3-Zero", "USB CDC receiver, no sensors", "Waveshare ESP32-S3-Zero wiki"],
            ["MQ-7 / IR", "Rover inspect only", "MQ-7 datasheet — raw ADC, not ppm. IR = digital LOW flag"],
            ["Implementation", "Working software + firmware in this repo", "https://github.com/Rithvik-7/WECOOK-MOLE"],
            ["Domain context only", "Why mines care about movement", "Coal Mines Regulations, 2017; DGMS (S&T) Circ. 01/2017 cl. 6.1 — not implemented here"],
        ],
        col_widths=[3.4, 5.4, 7.7],
    )

    heading(doc, "22. Glossary")
    add_table(
        doc,
        ["Term", "Meaning in MOLE"],
        [
            ["MOLE", "Mine Observation & Live-alert Engine — the whole system"],
            ["Node A / Node B", "Fixed tabletop sensors. A has the slider; B is comparison only"],
            ["S3-Zero", "Waveshare ESP32-S3 USB receiver. Not a monitoring node"],
            ["Latch", "ALERT stays until a proper clear; ML cannot cancel it"],
            ["MAE", "Mean absolute error of the 30 s signal forecast"],
            ["Tabletop prior", "Shipped quiet-table joblib. Not a real-mine model"],
            ["UNKNOWN", "We do not know; never shown as healthy green"],
            ["Mine-Rover-AP", "Rover Wi-Fi name. Separate from node ESP-NOW"],
        ],
        col_widths=[4.0, 12.5],
    )

    heading(doc, "Annex A — Short text for the SIH portal idea box")
    para(
        doc,
        "MOLE is a tabletop mine-monitoring and inspection system for SIH26025. Two fixed ESP32 nodes measure tilt, vibration, and (on Node A) a crack slider, and send ESP-NOW to a Waveshare ESP32-S3-Zero USB receiver. A local laptop website stores every reading, latches WATCH/ALERT from simple rules, and runs Isolation Forest plus a 30-second sensor-trend forecast with MAE. After a warning, the officer remotely drives a separate rover on Wi-Fi AP Mine-Rover-AP to inspect. Measurements show disturbance on this model. They do not prove a collapse or certify a mine. No cloud, login, camera vision, LoRa, CO ppm, or autonomous driving.",
        align="justify",
    )

    heading(doc, "Annex B — Node packet and USB JSON")
    para(doc, "On air (packed C struct):", bold=True, space_after=4)
    para(
        doc,
        "version (1), nodeId (1 or 2), sequence, uptimeMs, roll, pitch, vibration, sliderRaw (Node B always −1), flags (IMU=1, POT=2, VIB=4).",
        size=10,
    )
    para(doc, "USB example, Node A:", bold=True, space_after=4)
    para(
        doc,
        '{"type":"telemetry","schema":1,"node_id":1,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":7,"roll_deg":0.12,"pitch_deg":-0.08,"vibration_g":0.004,"adc_raw":2048}',
        size=9,
    )
    para(doc, "USB example, Node B:", bold=True, space_after=4)
    para(
        doc,
        '{"type":"telemetry","schema":1,"node_id":2,"seq":17,"uptime_ms":17000,"gateway_ms":18500,"valid":5,"roll_deg":0.03,"pitch_deg":0.06,"vibration_g":0.003,"adc_raw":null}',
        size=9,
    )
    para(doc, "node_id 1 and 2 are reserved. Rover uses device_id \"rover\" over HTTP, not this USB schema.", align="justify")

    heading(doc, "Annex C — Flash map")
    add_table(
        doc,
        ["Unit", "Sketch", "Arduino board setting"],
        [
            ["Node A", "firmware/node/node.ino", "ESP32 Dev Module; NODE_ID 1, HAS_POT 1"],
            ["Node B", "firmware/node_b/node.ino", "ESP32 Dev Module; NODE_ID 2, HAS_POT 0"],
            ["Receiver", "firmware/receiver_s3/receiver_s3.ino", "Waveshare ESP32-S3-Zero or ESP32S3 Dev Module; USB CDC On Boot = Enabled"],
            ["Rover", "firmware/rover/rover.ino", "ESP32 Dev Module; AP Mine-Rover-AP"],
        ],
        col_widths=[3.0, 6.5, 7.0],
    )

    heading(doc, "Annex D — Team roster (institute use)")
    para(
        doc,
        "Official six-slide PPT does not require a member table. Fill this for college nomination if the SPOC asks. Do not invent names on the idea PPT.",
        align="justify",
    )
    add_table(
        doc,
        ["#", "Name", "Suggested role on this build"],
        [
            ["1", "", "Node A wiring, mount, slider calibration"],
            ["2", "", "Node B and tabletop mechanics (movable surface)"],
            ["3", "", "S3-Zero USB receiver and node radio"],
            ["4", "", "Rover mechanics, motors, inspect payload"],
            ["5", "", "Laptop ingest, rules, storage, rover proxy"],
            ["6", "", "Dashboard, ML evidence, demo script, pitch"],
        ],
        col_widths=[1.5, 6.5, 8.5],
    )
    para(doc, "Team ID (portal): ______________________     Institute SPOC: ______________________", size=11)

    heading(doc, "Annex E — Related files in this repository")
    bullets(
        doc,
        [
            "Official idea PPT/PDF: pitch/SIH26025_WE_COOK_IDEA.pptx and .pdf (upload the PDF of 6 slides).",
            "This document: pitch/SIH26025_WE_COOK_MOLE_Judge_Document.docx / .pdf.",
            "Speaker crib for the 6 slides: pitch/SPEAKER-CRIB.md.",
            "As-built contract: AGENTS.md.",
            "How to run: README.md.",
            "Firmware: firmware/README.md. Telemetry examples: software/TELEMETRY.md.",
        ],
    )

    para(
        doc,
        "Close: nodes detect → rules latch → Isolation Forest + Ridge explain → rover inspects. "
        "Team WE COOK · SIH26025 · tabletop only.",
        bold=True,
        color=NAVY,
        align="center",
        space_after=0,
    )

    OUT_DOCX.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT_DOCX))
    return OUT_DOCX


if __name__ == "__main__":
    path = build()
    print("saved", path)
