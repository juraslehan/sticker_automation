import os
import yaml
from .layout import build_doc_flow
from .pdfout import build_pdf_flow

def generate_dummy_flow(out_dir, config_path):
    """
    Produce a DOCX and PDF stacking labels (Zebra-style) from dummy data
    so you can verify spacing and fonts before wiring PDF parsing.
    """
    os.makedirs(out_dir, exist_ok=True)
    labels = [
        {"line1": "TSR 341", "line2": "CF226A"},
        {"line1": "TSR 342", "line2": "CF259A"},
        {"line1": "AVDUB 10", "line2": "CF400A"},
        {"line1": "AVDUB 10", "line2": "CF401A"},
        {"line1": "AVDUB 10", "line2": "CF402A"},
        {"line1": "AVDUB 10", "line2": "CF403A"},
    ]
    out_docx = os.path.join(out_dir, "stickers.docx")
    out_pdf = os.path.join(out_dir, "stickers.pdf")

    # Load to validate config exists; not strictly needed otherwise
    with open(config_path, "r", encoding="utf-8") as f:
        _ = yaml.safe_load(f)

    build_doc_flow(labels, config_path, out_docx)
    build_pdf_flow(labels, config_path, out_pdf)
    return out_docx, out_pdf
