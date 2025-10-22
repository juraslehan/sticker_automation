from docx import Document
from docx.shared import Mm, Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
import yaml

def _mm(x):  # convenience
    return Mm(float(x))

def build_doc_flow(labels, config_path, out_docx):
    """
    Build a Word document that stacks labels vertically (Zebra-style).
    Each label is a 1x1 table sized to the 'label.width_mm' x 'label.height_mm'.
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    page = cfg["page"]
    label = cfg["label"]
    text = cfg["text"]
    behavior = cfg["behavior"]
    word_cfg = cfg.get("word", {})

    doc = Document()

    # Page size & margins
    sec = doc.sections[0]
    sec.page_width = _mm(page["width_mm"])
    sec.page_height = _mm(page["height_mm"])
    sec.top_margin = _mm(page["margin_mm"]["top"])
    sec.right_margin = _mm(page["margin_mm"]["right"])
    sec.bottom_margin = _mm(page["margin_mm"]["bottom"])
    sec.left_margin = _mm(page["margin_mm"]["left"])

    for i, lab in enumerate(labels):
        # 1x1 table representing a single sticker block
        table = doc.add_table(rows=1, cols=1)
        table.alignment = {
            "left": WD_TABLE_ALIGNMENT.LEFT,
            "center": WD_TABLE_ALIGNMENT.CENTER,
            "right": WD_TABLE_ALIGNMENT.RIGHT,
        }.get(word_cfg.get("align", "left"), WD_TABLE_ALIGNMENT.LEFT)

        # Prevent Word from auto-shrinking table
        table.autofit = False

        cell = table.cell(0, 0)
        # Set column width by setting cell width (approx control)
        cell.width = _mm(label["width_mm"])

        # Try to control height via paragraph spacing (approx). Row height exact control is limited in python-docx.
        # We pad with an empty line if needed to keep consistent visual height.
        p1 = cell.paragraphs[0]
        p1.paragraph_format.space_before = Pt(0)
        p1.paragraph_format.space_after = Pt(0)
        p1.paragraph_format.line_spacing = text.get("line_spacing", 1.0)
        p1.alignment = WD_ALIGN_PARAGRAPH.LEFT

        run1 = p1.add_run(lab["line1"])
        run1.font.name = text["font_name"]
        run1.font.size = Pt(text["line1_size_pt"])

        p2 = cell.add_paragraph()
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(0)
        p2.paragraph_format.line_spacing = text.get("line_spacing", 1.0)
        p2.alignment = WD_ALIGN_PARAGRAPH.LEFT

        run2 = p2.add_run(lab["line2"])
        run2.font.name = text["font_name"]
        run2.font.size = Pt(text["line2_size_pt"])

        # Optional border for debugging
        if cfg["label"].get("show_border", False):
            _add_cell_border(cell)

        # Add spacing between labels
        gap_mm = float(label.get("gap_mm", 0))
        if gap_mm > 0:
            spacer = doc.add_paragraph()
            spacer_format = spacer.paragraph_format
            # Convert mm to approx points (1 mm ≈ 2.83465 pt)
            spacer_format.space_after = Pt(gap_mm * 2.83465)

    doc.save(out_docx)

def _add_cell_border(cell):
    # Adds a thin border to a cell (debugging). Relies on XML.
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        tag = OxmlElement(f'w:{edge}')
        tag.set(qn('w:val'), 'single')
        tag.set(qn('w:sz'), '4')      # 0.5pt
        tag.set(qn('w:space'), '0')
        tag.set(qn('w:color'), '000000')
        tcBorders.append(tag)
    tcPr.append(tcBorders)
