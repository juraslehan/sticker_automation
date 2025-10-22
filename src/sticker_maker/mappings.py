from __future__ import annotations
import csv
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rapidfuzz import process, fuzz
import re

ROOT = Path(__file__).resolve().parents[2]  # project root (.../sticker_automation)
DATA = ROOT / "data" / "mappings"

# ---------- csv loaders ----------
def _load_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        r = csv.DictReader((line for line in f if not line.strip().startswith("#")))
        for row in r:
            if not any(row.values()):
                continue
            rows.append({k.strip(): (v or "").strip() for k, v in row.items()})
    return rows

def load_products_map() -> Dict[str, str]:
    # alias -> canonical (both uppercased)
    out: Dict[str, str] = {}
    for row in _load_csv(DATA / "products.csv"):
        a = row.get("alias", "").strip().upper()
        c = row.get("canonical", "").strip().upper()
        if a and c:
            out[a] = c
    return out

def load_locations_map() -> Dict[str, str]:
    # raw (uppercased) -> short_label (as-is)
    out: Dict[str, str] = {}
    for row in _load_csv(DATA / "locations.csv"):
        raw = row.get("raw", "").strip().upper()
        short = row.get("short_label", "").strip()
        if raw and short:
            out[raw] = short
    return out

def load_packs() -> Dict[Tuple[str, str], str]:
    # (family,color) -> sku (all uppercased)
    out: Dict[Tuple[str, str], str] = {}
    for row in _load_csv(DATA / "packs.csv"):
        fam = row.get("family", "").strip().upper()
        col = row.get("color", "").strip().upper()
        sku = row.get("sku", "").strip().upper()
        if fam and col and sku:
            out[(fam, col)] = sku
    return out

# ---------- normalizer ----------
class Normalizer:
    """
    - normalize_product(text) -> canonical SKU (CF226A, CF259A, W1490A, ...)
    - normalize_location(text) -> short label (TSR, AVDUB 10, ...)
    - expand_pack(family) -> list of SKUs for CMYK (e.g., CF400 -> CF400A..CF403A)
    """

    def __init__(self):
        self.products = load_products_map()
        self.locations = load_locations_map()
        self.packs = load_packs()
        self._product_aliases = list(self.products.keys())
        self._location_raws = list(self.locations.keys())
        self._canonicals = set(self.products.values())  

    # products
    def normalize_product(self, text: str, min_score: int = 90) -> Optional[str]:
        """
        Try exact -> cleaned exact -> SKU extraction (hyphen-safe) -> fuzzy.
        Returns CANONICAL (e.g., CF226A) or None.
        """
        if not text:
            return None
        s = text.strip().upper()

        # 1) exact alias
        if s in self.products:
            return self.products[s]

        # 2) cleaned exact (remove spaces/dashes)
        cleaned = s.replace(" ", "").replace("-", "")
        for alias, canon in self.products.items():
            if alias.replace(" ", "").replace("-", "") == cleaned:
                return canon

        # 3) SKU extraction (handle hyphens: "CRNA-CF226A" -> find CF226A)
        #    Search on a hyphen-to-space version so tokens are separable
        scan = s.replace("-", " ")
        # Tokens like CF226A, CF400A, W1490A, CN053AE, etc.
        import re
        tokens = re.findall(r"[A-Z]{1,3}\d{3,4}[A-Z]{0,2}", scan)
        for tok in tokens:
            # if token is a known alias, map it
            if tok in self.products:
                return self.products[tok]
            # if token already equals a canonical in our map, accept it
            if tok in self._canonicals:
                return tok

        # 4) fuzzy alias matching
        from rapidfuzz import process, fuzz
        match = process.extractOne(s, self._product_aliases, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= min_score:
            return self.products[match[0]]

        return None


    # locations
    def normalize_location(self, text: str, min_score: int = 88) -> Optional[str]:
        if not text:
            return None
        s = text.strip().upper()
        if s in self.locations:
            return self.locations[s]
        for raw, short in self.locations.items():
            if s.startswith(raw):
                return short
        match = process.extractOne(s, self._location_raws, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= min_score:
            return self.locations[match[0]]
        return s  # fallback: keep uppercase

    # packs (komplet)
    def expand_pack(self, family: str) -> List[str]:
        fam = (family or "").strip().upper()
        if not fam:
            return []
        order = ["BLACK", "CYAN", "MAGENTA", "YELLOW"]
        out: List[str] = []
        for col in order:
            sku = self.packs.get((fam, col))
            if sku:
                out.append(sku)
        return out
