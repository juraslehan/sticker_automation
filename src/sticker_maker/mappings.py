from __future__ import annotations
import csv
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from rapidfuzz import process, fuzz

# project root → data/mappings
ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data" / "mappings"

# ---------- CSV loaders ----------
def _load_csv(path: Path) -> List[Dict[str, str]]:
    rows: List[Dict[str, str]] = []
    if not path.exists():
        return rows
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
    # raw (uppercased) -> short label (as-is)
    out: Dict[str, str] = {}
    for row in _load_csv(DATA / "locations.csv"):
        raw = row.get("raw", "").strip().upper()
        short = row.get("short_label", "").strip()
        if raw and short:
            out[raw] = short
    return out

def load_packs() -> Dict[Tuple[str, str], str]:
    # (family, color) -> sku (all uppercased)
    out: Dict[Tuple[str, str], str] = {}
    for row in _load_csv(DATA / "packs.csv"):
        fam = row.get("family", "").strip().upper()
        col = row.get("color", "").strip().upper()
        sku = row.get("sku", "").strip().upper()
        if fam and col and sku:
            out[(fam, col)] = sku
    return out

def load_printer_families() -> Dict[str, str]:
    """
    keyword (upper substring) -> family (e.g., 'M404' -> 'CF259')
    """
    out: Dict[str, str] = {}
    for row in _load_csv(DATA / "printer_families.csv"):
        kw = row.get("keyword", "").strip().upper()
        fam = row.get("family", "").strip().upper()
        if kw and fam:
            out[kw] = fam
    return out

# ---------- Normalizer ----------
class Normalizer:
    """
    Provides:
      - normalize_product(text) -> canonical SKU (CF226A, CF259A, W1490A, ...)
      - normalize_location(text) -> short label (TSR, AVDUB 10, ...)
      - expand_pack(family) -> list of SKUs in CMYK/K order
      - family_from_printer(printer_text) -> family (e.g., 'CF400')
    """

    def __init__(self):
        self.products = load_products_map()          # alias -> canonical
        self.locations = load_locations_map()        # raw -> short
        self.packs = load_packs()                    # (family,color) -> sku
        self.printer_families = load_printer_families()  # keyword -> family

        self._product_aliases = list(self.products.keys())
        self._location_raws = list(self.locations.keys())
        self._canonicals = set(self.products.values())

    # ---- products ----
    def normalize_product(self, text: str, min_score: int = 90) -> Optional[str]:
        """
        exact -> cleaned exact -> SKU extraction (hyphen-safe) -> fuzzy.
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

        # 3) SKU extraction: scan on hyphen→space version so tokens split
        scan = s.replace("-", " ")
        tokens = re.findall(r"[A-Z]{1,3}\d{3,4}[A-Z]{0,3}", scan)
        for tok in tokens:
            if tok in self.products:
                return self.products[tok]
            if tok in self._canonicals:
                return tok

        # 4) fuzzy alias matching
        match = process.extractOne(s, self._product_aliases, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= min_score:
            return self.products[match[0]]

        return None

    # ---- locations ----
    def normalize_location(self, text: str, min_score: int = 88) -> Optional[str]:
        """
        exact -> startswith -> fuzzy. Returns short label; fallback to UPPERCASE original.
        """
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

        return s  # fallback: keep uppercase so something prints

    # ---- packs (komplet) ----
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

    # ---- printer → family ----
    def family_from_printer(self, printer_text: str) -> Optional[str]:
        """
        Use substring keywords (or fuzzy partial) to map a printer model to a toner family.
        """
        s = (printer_text or "").upper()
        if not s:
            return None

        for kw, fam in self.printer_families.items():
            if kw and kw in s:
                return fam

        # fuzzy partial match as a fallback
        if self.printer_families:
            match = process.extractOne(s, list(self.printer_families.keys()), scorer=fuzz.partial_ratio)
            if match and match[1] >= 85:
                return self.printer_families[match[0]]

        return None
