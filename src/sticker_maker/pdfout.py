from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import yaml, os

def _ensure_font(name: str) -> str:
    try:
        pdfmetrics.getFont(name)
        return name
    except Exception:
        pass
    # Register Windows Arial if requested
    if name.lower() == "arial":
        win_arial = r"C:\Windows\Fonts\arial.ttf"
        if os.path.exists(win_arial):
            try:
                pdfmetrics.registerFont(TTFont("Arial", win_arial))
                return "Arial"
            except Exception:
                pass
    return "Helvetica"

def build_pdf_flow(labels, config_path, out_pdf):
    """
    PDF: ONE STICKER PER PAGE (page size = label size).
    """
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    page  = cfg["page"]
    label = cfg["label"]
    text  = cfg["text"]
    lines = cfg.get("lines", [])

    # page size equals label size
    page_w = float(label["width_mm"]) * mm
    page_h = float(label["height_mm"]) * mm

    margins = page.get("margin_mm", {"top": 2, "right": 2, "bottom": 2, "left": 2})
    left = margins["left"] * mm
    right = margins["right"] * mm
    top = margins["top"] * mm
    bottom = margins["bottom"] * mm

    content_w = page_w - left - right
    content_h = page_h - top - bottom

    font_name = _ensure_font(text.get("font_name", "Helvetica"))
    l1 = text.get("line1_size_pt", 10)
    l2 = text.get("line2_size_pt", 9)
    l3 = text.get("line3_size_pt", 10)
    l4 = text.get("line4_size_pt", 14)

    # Create canvas with initial page size
    c = canvas.Canvas(out_pdf, pagesize=(page_w, page_h))

    def draw_centered_line(value, y, size_pt, bold=False):
        c.setFont(font_name, size_pt)
        w = c.stringWidth(value, font_name, size_pt)
        x = left + (content_w - w) / 2.0
        c.drawString(x, y, value)

    for i, lab in enumerate(labels):
        if i > 0:
            c.showPage()
            c.setPageSize((page_w, page_h))

        # Optional border (content area)
        if label.get("show_border", True):
            c.rect(left, bottom, content_w, content_h)

        # vertical layout: center block within content area
        # rough line heights
        gap = 3  # points between lines
        total_h = l1 + l2 + l3 + l4 + gap*3
        start_y = bottom + (content_h - total_h) / 2.0

        y = start_y + l4 + l3 + l2 + gap*3  # first baseline for line1
        if lines and lines[0].get("show", True):
            draw_centered_line(lab.get("line1", ""), y, l1, lines[0].get("bold", False))

        y -= (l2 + gap)
        if len(lines) >= 2 and lines[1].get("show", True):
            draw_centered_line(lab.get("line2", ""), y, l2, lines[1].get("bold", False))

        y -= (l3 + gap)
        if len(lines) >= 3 and lines[2].get("show", True):
            draw_centered_line(lab.get("line3", ""), y, l3, lines[2].get("bold", False))

        y -= (l4 + gap)
        if len(lines) >= 4 and lines[3].get("show", True):
            draw_centered_line(lab.get("line4", ""), y, l4, lines[3].get("bold", True))

    c.save()
