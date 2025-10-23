from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from .mappings import Normalizer
import re

def today_hr() -> str:
    return datetime.now().strftime("%d.%m.%Y.")

def make_line3(room: Optional[str]) -> str:
    room = (room or "").strip()
    if not room:
        return "SOBA"
    low = room.lower()
    # Središnja pisarnica → središnja pis.
    if low.startswith("sredi"):
        return "SOBA središnja pis."
    # Porta → porta
    if low == "porta":
        return "SOBA porta"
    # 23A → 23a  (digits + single letter)
    m = re.match(r"^(\d+)([A-Za-z])$", room)
    if m:
        return f"SOBA {m.group(1)}{m.group(2).lower()}"
    return f"SOBA {room}"



def rows_to_labels(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Convert parsed rows into 4-line label dicts.
    Uses row['date'] from the PDF when available; falls back to today.
    """
    n = Normalizer()
    out: List[Dict[str, str]] = []

    for row in rows:
        loc_raw = (row.get("location") or "").strip()
        prod_raw = (row.get("product") or "").strip()
        qty = int(row.get("qty") or 1)
        room = row.get("room")
        printer = (row.get("printer") or "").strip()
        date_str = (row.get("date") or "").strip() or today_hr()

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
