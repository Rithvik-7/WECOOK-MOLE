"""Build SIH26025 judge / viva Q&A book (DOCX + PDF)."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(r"C:\Users\brith\Desktop\mole")
PITCH = ROOT / "pitch"
sys.path.insert(0, str(PITCH))

from build_judge_document import (  # noqa: E402
    INK,
    MUTED,
    NAVY,
    NAVY_HEX,
    ORANGE,
    ORANGE_HEX,
    PALE,
    TEAL,
    TEAL_HEX,
    WHITE,
    add_table,
    bullets,
    callout,
    heading,
    page_break,
    para,
    prevent_row_split,
    set_cell_border,
    set_cell_text,
    set_run_font,
    setup_styles,
    shade_cell,
)
from qa_bank import ALWAYS_SAY, NEVER_SAY, RAPID_FIRE, SECTIONS  # noqa: E402

ASSETS = PITCH / "assets"
OUT_DOCX = PITCH / "SIH26025_WE_COOK_MOLE_Judge_QA.docx"
OUT_PDF = PITCH / "SIH26025_WE_COOK_MOLE_Judge_QA.pdf"
DOWNLOADS = Path.home() / "Downloads"

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


def make_banner() -> Path:
    ASSETS.mkdir(parents=True, exist_ok=True)
    w, h = 2400, 720
    img = Image.new("RGB", (w, h), (11, 44, 74))
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 28, h), fill=(244, 123, 32))
    d.text((72, 48), "SMART INDIA HACKATHON 2026", font=_font(36, True), fill=(244, 123, 32))
    d.text((72, 118), "Judge / viva voce crib  ·  not the 6-slide portal PDF", font=_font(28), fill=(210, 220, 230))
    n_q = sum(len(s["items"]) for s in SECTIONS)
    d.text((72, 210), "MOLE Q&A", font=_font(88, True), fill=(255, 255, 255))
    d.text((72, 330), f"{n_q} spoken answers  ·  traps marked  ·  rapid-fire card", font=_font(32, True), fill=(255, 255, 255))
    d.text((72, 420), "Team WE COOK   ·   Problem SIH26025", font=_font(30), fill=(244, 123, 32))
    d.text((72, 490), "Ministry of Coal   ·   Hardware   ·   Disaster Management", font=_font(26), fill=(210, 220, 230))
    d.text((72, 560), "Speak the short answer first. Do not invent collapse %, ppm, or autonomy.", font=_font(24), fill=(210, 220, 230))
    d.text((72, 630), "Tabletop demonstration  ·  9 September 2026", font=_font(22), fill=(168, 180, 194))
    path = ASSETS / "qa_cover_banner.png"
    img.save(path, "PNG")
    return path


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
    section.left_margin = Cm(1.8)
    section.right_margin = Cm(1.8)
    section.top_margin = Cm(2.1)
    section.bottom_margin = Cm(2.1)
    section.header_distance = Cm(0.7)
    section.footer_distance = Cm(0.7)

    header = section.header
    header.is_linked_to_previous = False
    hp = header.paragraphs[0]
    hp.clear()
    r = hp.add_run("WE COOK  ·  SIH26025  ·  MOLE judge / viva Q&A")
    set_run_font(r, size=9, bold=True, color=NAVY)
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "12")
    bottom.set(qn("w:space"), "4")
    bottom.set(qn("w:color"), NAVY_HEX)
    p_bdr.append(bottom)
    hp._p.get_or_add_pPr().append(p_bdr)

    footer = section.footer
    footer.is_linked_to_previous = False
    table = footer.add_table(1, 2, width=Cm(17.4))
    table.autofit = True
    left, right = table.rows[0].cells
    left.text = ""
    lp = left.paragraphs[0]
    lr = lp.add_run("Viva crib for the room  ·  not the 6-slide SIH portal PDF")
    set_run_font(lr, size=8, color=MUTED)
    right.text = ""
    rp = right.paragraphs[0]
    rp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    add_page_number(rp)


def add_picture(doc, path: Path, width_cm=17.0):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(4)
    p.add_run().add_picture(str(path), width=Cm(width_cm))


def keep_row(row):
    prevent_row_split(row)


def qa_block(doc, number: int, question: str, answer: str, *, trap: bool = False, push: str | None = None):
    table = doc.add_table(rows=2, cols=1)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    q_cell = table.rows[0].cells[0]
    a_cell = table.rows[1].cells[0]
    shade_cell(q_cell, "7A1F14" if trap else NAVY_HEX)
    set_cell_border(q_cell, "7A1F14" if trap else NAVY_HEX)
    shade_cell(a_cell, "F8EEEA" if trap else PALE)
    set_cell_border(a_cell, "7A1F14" if trap else "D5DEE8")
    keep_row(table.rows[0])
    keep_row(table.rows[1])

    q_cell.text = ""
    qp = q_cell.paragraphs[0]
    qp.paragraph_format.space_before = Pt(4)
    qp.paragraph_format.space_after = Pt(4)
    tag = "TRAP  ·  " if trap else ""
    r0 = qp.add_run(f"Q{number}  ·  {tag}")
    set_run_font(r0, size=10, bold=True, color=ORANGE if trap else ORANGE)
    r1 = qp.add_run(question)
    set_run_font(r1, size=11, bold=True, color=WHITE)

    a_cell.text = ""
    ap = a_cell.paragraphs[0]
    ap.paragraph_format.space_before = Pt(4)
    ap.paragraph_format.space_after = Pt(2)
    ap.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
    ar = ap.add_run(answer)
    set_run_font(ar, size=11, color=INK)
    if push:
        pp = a_cell.add_paragraph()
        pp.paragraph_format.space_before = Pt(2)
        pp.paragraph_format.space_after = Pt(4)
        pr = pp.add_run("If they push: " + push)
        set_run_font(pr, size=10, italic=True, color=TEAL)

    for row in table.rows:
        row.cells[0].width = Cm(17.4)
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_after = Pt(6)
    spacer.paragraph_format.space_before = Pt(0)


def count_questions() -> int:
    return sum(len(s["items"]) for s in SECTIONS)


def build_docx() -> Path:
    banner = make_banner()
    n_q = count_questions()
    n_traps = sum(1 for s in SECTIONS for it in s["items"] if it.get("trap"))
    doc = Document()
    setup_styles(doc)
    setup_header_footer(doc)
    core = doc.core_properties
    core.title = "MOLE — Judge / viva Q&A (SIH26025)"
    core.author = "Team WE COOK"
    core.subject = "Smart India Hackathon 2026 · SIH26025 · Ministry of Coal"
    core.category = "Hardware · Disaster Management"
    core.comments = "Spoken answers for judges. Tabletop only. Not a certified mine system."

    add_picture(doc, banner, 17.2)
    para(doc, "Spoken question-and-answer crib for institute screening and SIH judges", size=12, italic=True, color=MUTED, align="center")

    add_table(
        doc,
        ["Field", "Value"],
        [
            ["Event", "Smart India Hackathon 2026"],
            ["Official problem ID", "SIH26025  (never write SIH2026025)"],
            ["Problem title", PS_TITLE],
            ["Organisation / category / theme", "Ministry of Coal  ·  Hardware  ·  Disaster Management"],
            ["Team / idea", "WE COOK  ·  MOLE — Mine Observation & Live-alert Engine"],
            ["Questions in this book", f"{n_q} full answers  ·  {n_traps} marked TRAP  ·  {len(RAPID_FIRE)} rapid-fire lines"],
            ["Public code", "https://github.com/Rithvik-7/WECOOK-MOLE"],
            ["Document date", "9 September 2026"],
            ["Sister files", "6-slide idea PDF (portal)  ·  long judge document  ·  this viva crib"],
        ],
        col_widths=[4.5, 12.7],
    )

    callout(
        doc,
        "How to use this book in the room",
        "Read the question. Speak the answer in the navy box — 20 to 40 seconds. If the judge pushes, use the teal “If they push” line only when it exists. "
        "Red TRAP questions are where teams over-claim. Pause, then give the honest limit. Do not recast MOLE as a maze robot, a collapse-percentage app, or a certified mine instrument. "
        "Upload only the official 6-slide idea PDF on the SIH portal. This file stays with the team.",
    )
    callout(
        doc,
        "Honesty, in one paragraph",
        "MOLE is a working tabletop demonstration. Two fixed nodes watch tilt, vibration, and (on Node A) a crack slider. "
        "The laptop runs rule-based early warning plus Isolation Forest and a 30-second sensor forecast. An officer can then drive a rover to look more closely. "
        "Readings can show disturbance on this model. They do not prove a collapse, name its cause, or certify that a real mine is safe.",
        TEAL_HEX,
    )

    heading(doc, "Pocket card — always say / never say")
    add_table(
        doc,
        ["Always say", "Never say"],
        [[a, n] for a, n in zip(ALWAYS_SAY, NEVER_SAY[: len(ALWAYS_SAY)])],
        col_widths=[8.6, 8.6],
    )
    para(doc, "Remaining never-say lines:", bold=True, space_after=4)
    bullets(doc, NEVER_SAY[len(ALWAYS_SAY) :], size=10)

    heading(doc, "Pocket card — rapid-fire facts")
    para(
        doc,
        "If a judge fires one-word questions, answer from this table. Thresholds are tabletop demo numbers, not DGMS trigger levels.",
        align="justify",
    )
    add_table(doc, ["Cue", "Answer in one breath"], RAPID_FIRE, col_widths=[4.2, 13.0])

    heading(doc, "Contents")
    contents_rows = []
    n = 1
    for section in SECTIONS:
        contents_rows.append([section["title"], f"Q{n}–Q{n + len(section['items']) - 1}  ({len(section['items'])} questions)"])
        n += len(section["items"])
    contents_rows.append(["13. Closing pitch sentence", "Memorise this"])
    add_table(doc, ["Section", "Questions"], contents_rows, col_widths=[11.0, 6.2])

    n = 1
    for section in SECTIONS:
        page_break(doc)
        heading(doc, section["title"])
        if section.get("blurb"):
            para(doc, section["blurb"], italic=True, size=11, color=MUTED, align="justify")
        for item in section["items"]:
            qa_block(
                doc,
                n,
                item["q"],
                item["a"],
                trap=bool(item.get("trap")),
                push=item.get("push"),
            )
            n += 1

    page_break(doc)
    heading(doc, "13. Closing pitch sentence")
    para(
        doc,
        "Isolation Forest + LOF flag unusual combinations versus this rig’s learned normal. "
        "A joint forest watches A vs B residual. Holdout-selected sklearn regression forecasts the next 30 seconds of those same signals with MAE. "
        "Rules remain the independent early-warning latch. The rover is remote inspection, not autonomy.",
        bold=True,
        color=NAVY,
        align="justify",
    )
    heading(doc, "14. Pin freeze (if they ask a GPIO)")
    add_table(
        doc,
        ["Unit", "Frozen detail"],
        [
            ["Node A / B MPU", "SDA 21, SCL 22, 0x68, 3.3 V"],
            ["Node A slider", "10 kΩ linear, SIG → 1 kΩ → GPIO34, NODE_ID 1 HAS_POT 1"],
            ["Node B", "No slider, NODE_ID 2 HAS_POT 0, sliderRaw = −1"],
            ["Receiver", "Waveshare ESP32-S3-Zero, USB CDC On Boot Enabled, 115200 JSON"],
            ["Rover motors", "L298N IN1–IN4 = 13 / 12 / 14 / 27; ENA/ENB jumpers ON"],
            ["Rover inspect", "TRIG 5, ECHO 18 via 1k/2k, MQ-7 GPIO36 raw, IR GPIO19 LOW=near"],
            ["Rover radio", "Mine-Rover-AP, 192.168.4.1, not on the node USB path"],
        ],
        col_widths=[4.4, 12.8],
    )
    heading(doc, "15. Related files")
    bullets(
        doc,
        [
            "Portal upload: pitch/SIH26025_WE_COOK_IDEA.pdf (six slides only).",
            "Long technical write-up: pitch/SIH26025_WE_COOK_MOLE_Judge_Document.pdf.",
            "This viva crib: pitch/SIH26025_WE_COOK_MOLE_Judge_QA.pdf.",
            "Speaker crib for the six slides: pitch/SPEAKER-CRIB.md.",
            "As-built contract: AGENTS.md. How to run: README.md.",
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


def export_pdf(docx_path: Path, pdf_path: Path) -> Path:
    """Export via Microsoft Word COM (Office 16 is installed on this machine)."""
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    if pdf_path.exists():
        pdf_path.unlink()
    docx_abs = str(docx_path.resolve())
    pdf_abs = str(pdf_path.resolve())
    ps = f"""
$ErrorActionPreference = 'Stop'
$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
try {{
  $doc = $word.Documents.Open('{docx_abs.replace("'", "''")}')
  $wdExportFormatPDF = 17
  $wdExportOptimizeForPrint = 0
  $wdExportAllDocument = 0
  $doc.ExportAsFixedFormat(
    '{pdf_abs.replace("'", "''")}',
    $wdExportFormatPDF,
    $false,
    $wdExportOptimizeForPrint,
    $wdExportAllDocument
  )
  $doc.Close([ref]$false)
}} finally {{
  $word.Quit()
  [System.GC]::Collect()
  [System.GC]::WaitForPendingFinalizers()
}}
"""
    subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps],
        check=True,
        capture_output=True,
        text=True,
    )
    if not pdf_path.exists():
        raise FileNotFoundError(f"Word did not write {pdf_path}")
    return pdf_path


def copy_to_downloads(*paths: Path) -> None:
    DOWNLOADS.mkdir(parents=True, exist_ok=True)
    for path in paths:
        shutil.copy2(path, DOWNLOADS / path.name)


if __name__ == "__main__":
    docx = build_docx()
    print("saved", docx)
    pdf = export_pdf(docx, OUT_PDF)
    print("saved", pdf)
    copy_to_downloads(docx, pdf)
    print("copied to", DOWNLOADS)
