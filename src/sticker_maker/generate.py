import os, yaml
from datetime import datetime
from .layout import build_doc_flow
from .pdfout import build_pdf_flow

def _today_hr():
    # format like 18.10.2025.
    return datetime.now().strftime("%d.%m.%Y.") 

def generate_dummy_flow(out_dir, config_path):
    """
    Produce DOCX/PDF with 4-line centered Zebra labels:
      line1: LOCATION
      line2: today's DATE
      line3: SOBA <room>
      line4: SKU (big/bold)
    """
    os.makedirs(out_dir, exist_ok=True)
    d = _today_hr()

    labels = [
        {"line1": "GOLIKOVA", "line2": d, "line3": "SOBA",      "line4": "W1490A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 341",  "line4": "CF400A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 341",  "line4": "CF401A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 341",  "line4": "CF402A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 341",  "line4": "CF403A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 110",  "line4": "CF280A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 413",  "line4": "CF226A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA 474",  "line4": "CF226A"},
        {"line1": "TSR",      "line2": d, "line3": "SOBA središnja dost.", "line4": "CF259A"},
    ]

    out_docx = os.path.join(out_dir, "stickers.docx")
    out_pdf  = os.path.join(out_dir, "stickers.pdf")

    with open(config_path, "r", encoding="utf-8") as f:
        _ = yaml.safe_load(f)

    build_doc_flow(labels, config_path, out_docx)
    build_pdf_flow(labels, config_path, out_pdf)
    return out_docx, out_pdf
