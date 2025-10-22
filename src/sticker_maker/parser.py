from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
import pdfplumber

# Header synonyms (Croatian + English-ish)
HDR_MAP = {
    "product": {
        "boja - šifra", "boja-šifra", "boja - sifra", "boja- sifra",
        "boja", "šifra", "sifra", "product"
    },
    "room": {"soba", "prostorija", "room"},
    "printer": {"pisač", "pisac", "printer", "model"},
    # intentionally ignore "Ured" (department) for stickers
}

# ---------- small helpers ----------
def _norm(x: Any) -> str:
    return (str(x or "")).strip()

def _lower_no_accents(s: str) -> str:
    repl = (
        ("š","s"),("Š","S"),("ć","c"),("Ć","C"),
        ("č","c"),("Č","C"),("ž","z"),("Ž","Z"),
        ("đ","d"),("Đ","D")
    )
    t = s
    for a,b in repl:
        t = t.replace(a,b)
    return t.lower()

def _header_key(cell: Any) -> Optional[str]:
    name = _lower_no_accents(_norm(cell))
    for key, variants in HDR_MAP.items():
        for v in variants:
            if name == _lower_no_accents(v):
                return key
    if name in ("product", "room", "printer"):
        return name
    return None

def _current_location_from_text(txt: str) -> Optional[str]:
    """
    Extract location from e.g. 'Lokacija: Područni ured Trešnjevka'
    (uses a simple regex on page text).
    """
    if not txt:
        return None
    m = re.search(r"Lokacija:\s*(.+)", txt, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None

# ---------- main ----------
def parse_orders(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse your orders PDF into rows:
      - location: taken from page header 'Lokacija: ...'
      - product:  'Boja - Šifra'
      - room:     'Soba'
      - qty:      1 (no explicit column in examples)
      - printer:  'Pisač' (kept so we can infer komplet family)
      - komplet_family: detected from product text if present
    Returns: list[ {location, product, qty, room, printer?, komplet_family?} ]
    """
    rows: List[Dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            current_location = _current_location_from_text(page_text) or ""

            tables = page.extract_tables(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                    "intersection_tolerance": 5,
                    "snap_tolerance": 3,
                    "edge_min_length": 10,
                    "join_tolerance": 3,
                    "text_x_tolerance": 2,
                    "text_y_tolerance": 2,
                }
            ) or []

            for tbl in tables:
                if not tbl or len(tbl) < 2:
                    continue

                header = [ _norm(c) for c in tbl[0] ]
                body   = tbl[1:]

                # map columns
                colmap: Dict[int, str] = {}
                for idx, h in enumerate(header):
                    key = _header_key(h)
                    if key:
                        colmap[idx] = key

                if not any(v in ("product", "room", "printer") for v in colmap.values()):
                    continue

                for r in body:
                    if not any(r):
                        continue

                    prod, room, printer = "", "", ""
                    for i, val in enumerate(r):
                        key = colmap.get(i)
                        if key == "product":
                            prod = _norm(val)
                        elif key == "room":
                            room = _norm(val)
                        elif key == "printer":
                            printer = _norm(val)

                    if not prod and not room and not printer:
                        continue

                    rec: Dict[str, Any] = {
                        "location": current_location,
                        "product": prod,
                        "qty": 1,
                        "room": room,
                        "printer": printer,
                    }

                    # detect 'komplet-XXXX' or 'komplet XXXX'
                    m = re.search(r"komplet[\s\-]*([A-Za-z]{1,3}\d{3,4})", prod, flags=re.IGNORECASE)
                    if m:
                        rec["komplet_family"] = m.group(1).upper()

                    rows.append(rec)

    # keep only rows with something in product (others are noise)
    rows = [r for r in rows if _norm(r.get("product"))]
    return rows
