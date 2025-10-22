from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
import pdfplumber

# -------- helpers --------
def _norm(x: Any) -> str:
    return (str(x or "")).strip()

def _lower_no_accents(s: str) -> str:
    repl = (
        ("š","s"),("Š","S"),("ć","c"),("Ć","C"),
        ("č","c"),("Č","C"),("ž","z"),("Ž","Z"),
        ("đ","d"),("Đ","D")
    )
    t = s or ""
    for a,b in repl: t = t.replace(a,b)
    return t.lower()

def _contains(cell: Any, *needles: str) -> bool:
    name = _lower_no_accents(_norm(cell))
    for n in needles:
        if _lower_no_accents(n) in name or name in _lower_no_accents(n):
            return True
    return False

def _find_locations_in_text(txt: str) -> List[str]:
    """
    Return all 'Lokacija: ...' occurrences on the page, in order.
    """
    out: List[str] = []
    if not txt:
        return out
    # handle wrapped lines (… 'Lokacija:' on one line, value on the next)
    lines = [ln.rstrip() for ln in txt.splitlines()]
    for i, ln in enumerate(lines):
        if re.search(r"\blokacija\s*:", ln, flags=re.IGNORECASE):
            # prefer same-line after colon
            m = re.search(r"lokacija\s*:\s*(.+)", ln, flags=re.IGNORECASE)
            if m and m.group(1).strip():
                out.append(m.group(1).strip())
            else:
                # next line fallback
                nxt = lines[i+1].strip() if i+1 < len(lines) else ""
                if nxt:
                    out.append(nxt)
    return out

def _detect_header_map(header_cells: List[str]) -> Dict[int, str]:
    """
    Map column index -> canonical key using 'contains' logic.
    Keys: product, room, printer
    """
    colmap: Dict[int, str] = {}
    for idx, cell in enumerate(header_cells):
        if _contains(cell, "boja", "šifra", "sifra", "boja -", "boja-"):
            colmap[idx] = "product"
        elif _contains(cell, "soba", "prostorija", "room"):
            colmap[idx] = "room"
        elif _contains(cell, "pisač", "pisac", "printer", "model"):
            colmap[idx] = "printer"
    return colmap

def _detect_komplet_family(product_text: str) -> Optional[str]:
    m = re.search(r"komplet[\s\-]*([A-Za-z]{1,3}\d{3,4})", product_text or "", flags=re.IGNORECASE)
    return m.group(1).upper() if m else None

# -------- main --------
def parse_orders(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse the order PDF into rows:
      {location, product, qty=1, room, printer, komplet_family?}
    Strategy:
      - For each page, find all 'Lokacija: …' headers in text (ordered).
      - Extract tables with two passes (lines → text).
      - For each table that exposes product/room/printer, assign it to the
        next location header on that page (heuristic matches your examples).
    """
    rows: List[Dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            locations = _find_locations_in_text(page_text)
            loc_idx = 0  # which 'Lokacija:' we are consuming on this page

            # two passes: (1) lines (lattice-like), (2) text (stream-like)
            pass_settings = [
                dict(vertical_strategy="lines", horizontal_strategy="lines",
                     intersection_tolerance=5, snap_tolerance=3,
                     edge_min_length=10, join_tolerance=3,
                     text_x_tolerance=2, text_y_tolerance=2),
                dict(vertical_strategy="text", horizontal_strategy="text",
                     text_x_tolerance=2, text_y_tolerance=2),
            ]

            page_tables: List[List[List[str]]] = []
            for ts in pass_settings:
                try:
                    tbls = page.extract_tables(table_settings=ts) or []
                except Exception:
                    tbls = []
                if tbls:
                    page_tables.extend(tbls)

            for tbl in page_tables:
                if not tbl or len(tbl) < 2:
                    continue

                header = [ _norm(c) for c in tbl[0] ]
                colmap = _detect_header_map(header)
                if not any(v in ("product","room","printer") for v in colmap.values()):
                    continue  # not a relevant table

                # choose location for this table (in order)
                current_location = ""
                if loc_idx < len(locations):
                    current_location = locations[loc_idx]
                    # Advance location index only if we actually produce rows
                    will_bump_loc = True
                else:
                    will_bump_loc = False

                produced = 0
                for r in tbl[1:]:
                    if not any(r):  # skip empty lines
                        continue
                    prod = room = printer = ""
                    for i, val in enumerate(r):
                        key = colmap.get(i)
                        if not key: 
                            continue
                        if key == "product":
                            prod = _norm(val)
                        elif key == "room":
                            room = _norm(val)
                        elif key == "printer":
                            printer = _norm(val)
                    if not (prod or room or printer):
                        continue

                    rec: Dict[str, Any] = {
                        "location": current_location,
                        "product": prod,
                        "qty": 1,
                        "room": room,
                        "printer": printer,
                    }
                    fam = _detect_komplet_family(prod)
                    if fam:
                        rec["komplet_family"] = fam

                    rows.append(rec)
                    produced += 1

                if produced and will_bump_loc:
                    loc_idx += 1  # next table belongs to next 'Lokacija: ...'

    # keep only those with some product text
    rows = [r for r in rows if _norm(r.get("product"))]
    return rows
