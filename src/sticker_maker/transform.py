from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from .mappings import Normalizer

def today_hr() -> str:
    # "22.10.2025."
    return datetime.now().strftime("%d.%m.%Y.")

def make_line3(room: Optional[str]) -> str:
    room = (room or "").strip()
    return f"SOBA {room}" if room else "SOBA"

def rows_to_labels(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Convert parsed rows into 4-line label dicts.
    Input row example:
      {
        "location": "Područni ured Trešnjevka",
        "product": "komplet-CF400" | "black-CF259A" | "CF226A" | ...
        "qty": 1,
        "room": "215",
        "printer": "HP Color LaserJet Pro M479fdn",
        "komplet_family": "CF400"  # optional if product said it explicitly
      }
    Output: list of {"line1","line2","line3","line4"} (duplicated by qty).
    """
    n = Normalizer()
    out: List[Dict[str, str]] = []
    date_str = today_hr()

    for row in rows:
        loc_raw = (row.get("location") or "").strip()
        prod_raw = (row.get("product") or "").strip()
        qty = int(row.get("qty") or 1)
        room = row.get("room")
        printer = (row.get("printer") or "").strip()

        # normalize location to short label (or keep uppercase)
        loc_short = n.normalize_location(loc_raw) or loc_raw.upper()

        # Decide SKUs
        skus: List[str] = []

        # (a) explicit komplet-family provided by parser
        family = (row.get("komplet_family") or "").strip().upper()
        if family:
            skus.extend(n.expand_pack(family))

        # (b) detect 'komplet' in product text; try to read/guess family
        if not skus and "KOMPLET" in prod_raw.upper():
            import re
            m = re.search(r"KOMPLET[\s\-]*([A-Z]{1,3}\d{3,4})", prod_raw.upper())
            fam = m.group(1) if m else ""
            if not fam:
                fam = n.family_from_printer(printer) or ""
            if fam:
                skus.extend(n.expand_pack(fam))

        # (c) otherwise treat as single-product and normalize to a canonical SKU
        if not skus:
            canon = n.normalize_product(prod_raw)
            if canon:
                skus.append(canon)

        # build final labels, duplicate by qty
        for sku in skus or [""]:
            for _ in range(max(1, qty)):
                out.append({
                    "line1": loc_short,
                    "line2": date_str,
                    "line3": make_line3(room),
                    "line4": sku,
                })
    return out
