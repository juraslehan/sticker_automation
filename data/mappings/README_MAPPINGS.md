# Mappings Guide (flexible, grow over time)

These CSVs are your “learning layer.” Add rows any time you meet new products or locations.

- **products.csv** — `alias,canonical`
  - Map any real-world product string (alias) to one clean code (canonical), e.g.:
    - `HP CF400A Toner`, `CF400`, `CF400A` → `CF400A`

- **locations.csv** — `raw,short_label`
  - Normalize long or inconsistent site names to short labels for compact stickers.

- **packs.csv** — `family,color,sku`
  - Define CMYK “komplet” packs by printer family (e.g., `CF400` → `CF400A/401A/402A/403A`).

**When a new thing appears:**
- Add aliases to `products.csv`
- Add locations to `locations.csv`
- If it’s a new color pack, add the family to `packs.csv`

All of this works without code changes.
