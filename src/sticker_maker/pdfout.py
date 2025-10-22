from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import yaml, os

def _ensure_font(name: str) -> str:
    """Try to use requested font; if not available, register Arial from Windows or fall back to Helvetica."""
    try:
        pdfmetrics.getFont(name)
        return name
    except Exception:
        pass
    # Try registering Arial if requested and available on Windows
    if name.lower() == "arial":
        win_arial = r"C:\Windows\Fonts\arial.ttf"
        if os.path.exists(win_arial):
            try:
                pdfmetrics.registerFont(TTFont("Arial", win_arial))
                return "Arial"
            except Exception:
                pass
    # Final fallback
    return "Helvetica"

def build_pdf_flow(labels, config_path, out_pdf):
    with open(config_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    page = cfg["page"]
    label = cfg["label"]
    text = cfg["text"]

    font_name = _ensure_font(text.get("font_name", "Helvetica"))
    line1_size = text.get("line1_size_pt", 11)
    line2_size = text.get("line2_size_pt", 10)

    c = canvas.Canvas(out_pdf, pagesize=(page["width_mm"] * mm, page["height_mm"] * mm))

    # Page margins
    left = page["margin_mm"]["left"] * mm
    top = page["margin_mm"]["top"] * mm
    bottom = page["margin_mm"]["bottom"] * mm

    # Label geometry
    lw = label["width_mm"] * mm
    lh = label["height_mm"] * mm
    gap = label.get("gap_mm", 0) * mm

    # Starting position (top-left of first label area)
    x = left
    y = (page["height_mm"] * mm) - top - lh

    for lab in labels:
        # New page if we run out of vertical space
        if y < bottom:
            c.showPage()
            y = (page["height_mm"] * mm) - top - lh

        # Optional debug border
        if label.get("show_border", False):
            c.rect(x, y, lw, lh)

        # Padding inside label
        pad = label.get("padding_mm", {})
        pad_top = pad.get("top", 2) * mm
        pad_left = pad.get("left", 2) * mm

        # Line 1
        c.setFont(font_name, line1_size)
        c.drawString(x + pad_left, y + lh - pad_top - line1_size, lab["line1"])

        # Line 2 (a few points below line1)
        c.setFont(font_name, line2_size)
        c.drawString(x + pad_left, y + lh - pad_top - (line1_size + 4 + line2_size), lab["line2"])

        # Next label position
        y -= (lh + gap)

    c.save()
