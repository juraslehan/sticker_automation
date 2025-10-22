from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import yaml, os

REG_NAME = "TimesNewRoman"
BOLD_NAME = "TimesNewRoman-Bold"

def _register_times_new_roman():
    # Try Windows font files
    win_reg = r"C:\Windows\Fonts\times.ttf"
    win_bold = r"C:\Windows\Fonts\timesbd.ttf"
    ok_reg = ok_bold = False
    if os.path.exists(win_reg):
        try:
            pdfmetrics.registerFont(TTFont(REG_NAME, win_reg))
            ok_reg = True
        except Exception:
            pass
    if os.path.exists(win_bold):
        try:
            pdfmetrics.registerFont(TTFont(BOLD_NAME, win_bold))
            ok_bold = True
        except Exception:
            pass
    # Fallback to built-ins if needed
    if not ok_reg:
        pdfmetrics.registerFont(TTFont(REG_NAME, win_reg)) if os.path.exists(win_reg) else None
    return ok_reg and ok_bold

def build_pdf_flow(labels, config_path, out_pdf):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    page  = cfg["page"]
    label = cfg["label"]
    text  = cfg["text"]
    lines = cfg.get("lines", [])

    _register_times_new_roman()

    # page size equals label size
    page_w = float(label["width_mm"]) * mm
    page_h = float(label["height_mm"]) * mm

    m = page.get("margin_mm", {"top": 2, "right": 2, "bottom": 2, "left": 2})
    left = m["left"] * mm
    right = m["right"] * mm
    top = m["top"] * mm
    bottom = m["bottom"] * mm

    content_w = page_w - left - right
    content_h = page_h - top - bottom

    l1 = text.get("line1_size_pt", 14)
    l2 = text.get("line2_size_pt", 14)
    l3 = text.get("line3_size_pt", 14)
    l4 = text.get("line4_size_pt", 22)

    c = canvas.Canvas(out_pdf, pagesize=(page_w, page_h))

    def draw_centered_line(value, y, size_pt, bold=False):
        font = BOLD_NAME if bold else REG_NAME
        # If Times not found, ReportLab will raise; fallback to Helvetica family
        try:
            c.setFont(font, size_pt)
        except Exception:
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size_pt)
        w = c.stringWidth(value, font if font in pdfmetrics.getRegisteredFontNames() else "Helvetica", size_pt)
        x = left + (content_w - w) / 2.0
        c.drawString(x, y, value)

    for i, lab in enumerate(labels):
        if i > 0:
            c.showPage()
            c.setPageSize((page_w, page_h))

        # NO border: keep the page clean like expected output

        # vertical layout: center block within content area
        gap = 2  # points between lines
        total_h = l1 + l2 + l3 + l4 + gap*3
        start_y = bottom + (content_h - total_h) / 2.0

        y = start_y + l4 + l3 + l2 + gap*3
        if len(lines) >= 1 and lines[0].get("show", True):
            draw_centered_line(lab.get("line1", ""), y, l1, True)

        y -= (l2 + gap)
        if len(lines) >= 2 and lines[1].get("show", True):
            draw_centered_line(lab.get("line2", ""), y, l2, False)

        y -= (l3 + gap)
        if len(lines) >= 3 and lines[2].get("show", True):
            draw_centered_line(lab.get("line3", ""), y, l3, False)

        y -= (l4 + gap)
        if len(lines) >= 4 and lines[3].get("show", True):
            draw_centered_line(lab.get("line4", ""), y, l4, True)

    c.save()
