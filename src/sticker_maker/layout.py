from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import yaml

def _mm(x):  # convenience
    return Mm(float(x))

def _table_align(s: str):
    s = (s or "left").lower()
    return {"left": WD_TABLE_ALIGNMENT.LEFT,
            "center": WD_TABLE_ALIGNMENT.CENTER,
            "right": WD_TABLE_ALIGNMENT.RIGHT}.get(s, WD_TABLE_ALIGNMENT.LEFT)

def _para_align(s: str):
    s = (s or "left").lower()
    return {"left": WD_ALIGN_PARAGRAPH.LEFT,
            "center": WD_ALIGN_PARAGRAPH.CENTER,
            "right": WD_ALIGN_PARAGRAPH.RIGHT}.get(s, WD_ALIGN_PARAGRAPH.LEFT)

def build_doc_flow(labels, config_path, out_docx):
    """
    Word: stack 1x1 label blocks vertically (Zebra style), centered text,
    4 lines with per-line sizes/bold from config.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    page = cfg["page"]
    label = cfg["label"]
    text = cfg["text"]
    lines_cfg = cfg.get("lines", [])
    word_cfg = cfg.get("word", {"block_type": "textbox", "align": "left"})

    doc = Document()

    # Page setup
    sec = doc.sections[0]
    sec.page_width = _mm(page["width_mm"])
    sec.page_height = _mm(page["height_mm"])
    m = page["margin_mm"]
    sec.top_margin = _mm(m["top"])
    sec.right_margin = _mm(m["right"])
    sec.bottom_margin = _mm(m["bottom"])
    sec.left_margin = _mm(m["left"])

    table_align = _table_align(word_cfg.get("align", "left"))
    para_align = _para_align(text.get("align", "left"))
    gap_mm = float(label.get("gap_mm", 0))
    line_spacing = text.get("line_spacing", 1.0)

    def add_line(paragraph, value, size_pt, bold=False):
        run = paragraph.add_run(value)
        run.font.name = text["font_name"]
        run.font.size = Pt(size_pt)
        run.bold = bool(bold)

    for lab in labels:
        # each sticker = 1x1 table (more predictable in Word than pure paragraphs)
        table = doc.add_table(rows=1, cols=1)
        table.alignment = table_align
        table.autofit = False
        cell = table.cell(0, 0)
        cell.width = _mm(label["width_mm"])

        # First line in the first paragraph
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.line_spacing = line_spacing
        p.alignment = para_align

        # line1
        l1 = lines_cfg[0] if len(lines_cfg) > 0 else {"show": True, "bold": False}
        if l1.get("show", True):
            add_line(p, lab["line1"], text.get("line1_size_pt", 12), l1.get("bold", False))

        # remaining lines (line2..line4)
        spec = [("line2", "line2_size_pt"), ("line3", "line3_size_pt"), ("line4", "line4_size_pt")]
        for idx, (fname, fsize) in enumerate(spec, start=2):
            cfg_line = lines_cfg[idx-1] if len(lines_cfg) >= idx else {"show": True, "bold": False}
            if cfg_line.get("show", True):
                p2 = cell.add_paragraph()
                p2.paragraph_format.space_before = Pt(0)
                p2.paragraph_format.space_after = Pt(0)
                p2.paragraph_format.line_spacing = line_spacing
                p2.alignment = para_align
                add_line(p2, lab.get(fname, ""), text.get(fsize, 10), cfg_line.get("bold", False))

        # vertical gap between labels
        if gap_mm > 0:
            spacer = doc.add_paragraph()
            spacer.paragraph_format.space_after = Pt(gap_mm * 2.83465)  # mm → pt

    doc.save(out_docx)
