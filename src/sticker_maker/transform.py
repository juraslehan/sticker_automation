from __future__ import annotations
from typing import Dict, List, Any, Optional
from datetime import datetime
from .mappings import Normalizer

def today_hr() -> str:
    # Example: "22.10.2025."
    return datetime.now().strftime("%d.%m.%Y.")

def make_line3(room: Optional[str]) -> str:
    room = (room or "").strip()
    return f"SOBA {room}" if room else "SOBA"

def rows_to_labels(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """
    Convert parsed order rows into 4-line label dicts for the renderers.
    Input row schema (flexible, typical fields):
      {
        "location": "Avenija Dubrovnik 10",
        "product": "CF400A" or "komplet CF400" or "crna-CF226A",
        "qty": 2,
        "room": "341"        # optional
        "komplet_family": "CF400"  # optional explicit pack family
      }

    Output: list of dicts with keys: line1..line4 (each element = one sticker)
    Quantity duplicates are expanded (i.e., N pages for qty=N).
    """
    n = Normalizer()
    out: List[Dict[str, str]] = []
    date_str = today_hr()

    for row in rows:
        loc_raw = (row.get("location") or "").strip()
        prod_raw = (row.get("product") or "").strip()
        qty = int(row.get("qty") or 1)
        room = row.get("room")

        # 1) normalize location to short label
        loc_short = n.normalize_location(loc_raw) or loc_raw.upper()

        # 2) decide SKUs
        skus: List[str] = []

        # (a) explicit komplet family provided
        family = (row.get("komplet_family") or "").strip().upper()
        if family:
            expanded = n.expand_pack(family)
            if expanded:
                skus.extend(expanded)

        # (b) infer komplet from product text (e.g., "komplet CF400")
        if not skus and "KOMPLET" in prod_raw.upper():
            # try to find a family token right after "komplet"
            import re
            m = re.search(r"KOMPLET\s*([A-Z]{1,3}\d{3,4})", prod_raw.upper())
            fam = m.group(1) if m else ""
            if fam:
                expanded = n.expand_pack(fam)
                if expanded:
                    skus.extend(expanded)

        # (c) if still empty, treat as single-product and normalize to a canonical SKU
        if not skus:
            canon = n.normalize_product(prod_raw)
            if canon:
                skus.append(canon)

        # 3) build labels (duplicate by qty)
        for sku in skus or [""]:
            for _ in range(max(1, qty)):
                out.append({
                    "line1": loc_short,
                    "line2": date_str,
                    "line3": make_line3(room),
                    "line4": sku,
                })

    return out
