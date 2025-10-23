from __future__ import annotations
import re
from typing import List, Dict, Any, Optional
import pdfplumber

# =========================
# helpers
# =========================
def _norm(x: Any) -> str:
    return (str(x or "")).strip()

def _lower_no_accents(s: str) -> str:
    repl = (("š","s"),("Š","S"),("ć","c"),("Ć","C"),
            ("č","c"),("Č","C"),("ž","z"),("Ž","Z"),
            ("đ","d"),("Đ","D"))
    t = s or ""
    for a,b in repl: t = t.replace(a,b)
    return t.lower()

def _contains(cell: Any, *needles: str) -> bool:
    name = _lower_no_accents(_norm(cell))
    for n in needles:
        n2 = _lower_no_accents(n)
        if n2 in name or name in n2:
            return True
    return False

def _find_locations_in_text(txt: str) -> List[str]:
    """
    Collect all 'Lokacija: ...' on a page (order preserved).
    Handles case where value spills onto next line.
    """
    out: List[str] = []
    if not txt:
        return out
    lines = [ln.rstrip() for ln in txt.splitlines()]
    for i, ln in enumerate(lines):
        if re.search(r"\blokacija\s*:", ln, flags=re.IGNORECASE):
            m = re.search(r"lokacija\s*:\s*(.+)", ln, flags=re.IGNORECASE)
            if m and m.group(1).strip():
                out.append(m.group(1).strip())
            else:
                nxt = lines[i+1].strip() if i+1 < len(lines) else ""
                if nxt:
                    out.append(nxt)
    return out

def _find_date_in_text(txt: str) -> Optional[str]:
    """
    Extract 'Datum: dd.mm.yyyy.' -> 'dd.mm.yyyy.' (ensure trailing dot).
    """
    if not txt:
        return None
    m = re.search(r"Datum:\s*(\d{2}\.\d{2}\.\d{4}\.?)", txt, flags=re.IGNORECASE)
    if m:
        d = m.group(1)
        return d if d.endswith(".") else (d + ".")
    return None

def _detect_header_map(header_cells: List[str]) -> Dict[int, str]:
    """
    Column index -> key using 'contains' logic.
    Keys we care about: product, room, printer.
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

# ---- row-level heuristics ----
_SKU_TOKEN = re.compile(r"[A-Z]{1,3}\d{3,4}[A-Z]{0,3}")  # CF226A, W1490A, A415AVAL, etc.
_COLOR_WORDS = ("BLACK", "CYAN", "MAGENTA", "YELLOW", "CRNA", "PLAVA", "ŽUTA", "ZUTA", "MAGENTA")

def _is_skuish(text: str) -> bool:
    s = (text or "").upper()
    if not s:
        return False
    if "KOMPLET" in s:
        return True
    if _SKU_TOKEN.search(s):
        return True
    for w in _COLOR_WORDS:
        if w in s:
            return True
    return False

def _is_printerish(text: str) -> bool:
    s = (text or "")
    if not s:
        return False
    # printer hints; allow multi-line models
    if re.search(r"\b(HP|LaserJet|Color|Enterprise|Pro|MFP|M\d{3,4})\b", s, flags=re.IGNORECASE):
        # but reject if it also looks skuish/komplet
        return not _is_skuish(s)
    return False

_ALLOWED_ROOM_WORDS = {"Porta", "Središnja pisarnica", "Sredisnja pisarnica"}

def _is_roomish(text: str) -> bool:
    s = (text or "").strip()
    if not s:
        return False
    if re.fullmatch(r"\d{1,4}", s):   # pure numbers 1–4 digits
        return True
    if s in _ALLOWED_ROOM_WORDS:
        return True
    # avoid alphanumeric like '4002dn' (printer model)
    if re.search(r"[A-Za-z]", s):
        return False
    # short numeric fragments
    if len(s) <= 6 and re.search(r"\d", s):
        return True
    return False

def _is_headerish_row(values: List[str]) -> bool:
    joined = " ".join(_lower_no_accents(v) for v in values if v).strip()
    if not joined:
        return False
    header_tokens = ["pisač", "pisac", "printer", "model", "boja", "šifra", "sifra", "soba", "prostorija", "ured"]
    if joined in header_tokens:
        return True
    if "boja" in joined and ("sifra" in joined or "šifra" in joined) and len(joined) < 30:
        return True
    return False

def _detect_komplet_family(product_text: str) -> Optional[str]:
    m = re.search(r"komplet[\s\-]*([A-Za-z]{1,3}\d{3,4})", product_text or "", flags=re.IGNORECASE)
    return m.group(1).upper() if m else None

# =========================
# main
# =========================
def parse_orders(pdf_path: str) -> List[Dict[str, Any]]:
    """
    Parse orders into rows:
      {date, location, product, qty=1, room, printer, komplet_family?}

    Behavior:
      - multiple 'Lokacija:' per page (assign tables in order; sticky last location)
      - state machine across rows: printer → product → room
      - never accept printer text as product
      - room must be numeric or allowed words
      - date read from 'Datum: dd.mm.yyyy.'
    """
    rows: List[Dict[str, Any]] = []

    with pdfplumber.open(pdf_path) as pdf:
        last_location = ""  # sticky location across tables on a page
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            locations = _find_locations_in_text(page_text)
            page_date = _find_date_in_text(page_text)  # may be None
            loc_idx = 0
            if locations:
                last_location = locations[0]

            # two extraction passes (lines & text)
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
                if not any(v in ("product", "room", "printer") for v in colmap.values()):
                    continue

                # choose/sticky location for this table
                current_location = ""
                if loc_idx < len(locations):
                    current_location = locations[loc_idx]
                    last_location = current_location
                else:
                    current_location = last_location

                # --- state machine over table body ---
                cur: Optional[Dict[str, Any]] = None
                produced = 0

                for r in tbl[1:]:
                    cells = [ _norm(x) for x in r ]
                    if _is_headerish_row(cells):
                        continue

                    # mapped values
                    prod_m = room_m = printer_m = ""
                    for i, val in enumerate(cells):
                        key = colmap.get(i)
                        if key == "product":
                            prod_m = _norm(val)
                        elif key == "room":
                            room_m = _norm(val)
                        elif key == "printer":
                            printer_m = _norm(val)

                    # fallbacks scanning all cells
                    printer_f = ""
                    for c in cells:
                        if _is_printerish(c):
                            printer_f = c
                            break

                    # candidates
                    prod_cand = prod_m if _is_skuish(prod_m) else ""
                    room_cand = room_m if _is_roomish(room_m) else ""
                    printer_cand = printer_m or printer_f

                    # guard: never accept printer-looking text as product
                    if prod_m and _is_printerish(prod_m):
                        prod_cand = ""

                    # if product missing, try to find a SKU-ish cell in row
                    if not prod_cand:
                        for c in cells:
                            if _is_skuish(c) and not _is_printerish(c):
                                prod_cand = c
                                break

                    # if room missing, try to find a room-ish cell in row
                    if not room_cand:
                        for c in cells:
                            if _is_roomish(c):
                                room_cand = c
                                break

                    # 1) start a new block when we see a printer-only row
                    if printer_cand and not prod_cand and not room_cand:
                        # flush previous if it has product
                        if cur and cur.get("product"):
                            rows.append(cur)
                            produced += 1
                        cur = {
                            "date": page_date or "",
                            "location": current_location,
                            "product": "",
                            "qty": 1,
                            "room": "",
                            "printer": printer_cand,
                        }
                        continue

                    # ensure cur exists
                    if cur is None:
                        cur = {
                            "date": page_date or "",
                            "location": current_location,
                            "product": "",
                            "qty": 1,
                            "room": "",
                            "printer": "",
                        }

                    # 2) fill product
                    if prod_cand and not cur.get("product"):
                        cur["product"] = prod_cand
                        fam = _detect_komplet_family(prod_cand)
                        if fam:
                            cur["komplet_family"] = fam

                    # 3) fill room
                    if room_cand and not cur.get("room"):
                        cur["room"] = room_cand

                    # 4) fill printer
                    if printer_cand and not cur.get("printer"):
                        cur["printer"] = printer_cand

                    # 5) finalize when we have product + room
                    if cur.get("product") and cur.get("room"):
                        rows.append(cur)
                        produced += 1
                        cur = None

                # flush pending
                if cur and cur.get("product"):
                    rows.append(cur)
                    produced += 1
                    cur = None

                if produced and loc_idx < len(locations):
                    loc_idx += 1

    # final clean: must have product; ignore literal 'Soba'
    clean: List[Dict[str, Any]] = []
    for r in rows:
        prod = _norm(r.get("product"))
        if not prod:
            continue
        if _lower_no_accents(prod) == "soba":
            continue
        clean.append(r)

    return clean
