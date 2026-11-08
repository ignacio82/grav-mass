#!/usr/bin/env python3
"""Validate bom/bom.yaml and generate docs/BOM.md tables and bom/bom.csv."""

from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path

import yaml

ROOT_DIR = Path(__file__).resolve().parent.parent
BOM_YAML_PATH = ROOT_DIR / "bom" / "bom.yaml"
BOM_CSV_PATH = ROOT_DIR / "bom" / "bom.csv"
BOM_MD_PATH = ROOT_DIR / "docs" / "BOM.md"

BEGIN_MARKER = "<!-- BOM:BEGIN -->"
END_MARKER = "<!-- BOM:END -->"

PART_REQUIRED_FIELDS = (
    "id",
    "qty",
    "sku",
    "name",
    "vendor",
    "url",
    "alt_skus",
    "spec",
    "where_used",
    "category",
    "optional",
    "notes",
)

FILAMENT_REQUIRED_FIELDS = (
    "toolhead",
    "color_name",
    "hex",
    "material",
    "est_weight_g",
    "spools",
    "vendor_url",
)

DEFAULT_BOM_MD_TEMPLATE = f"""# 🛒 Complete Shopping List (Bill of Materials & Where to Buy)

Everything required to build, light, and control the tree in **Home Assistant (via ESPHome)** uses off-the-shelf components with **zero soldering** (only screw terminals and plug-in Grove/DuPont connectors). All legacy wired Bambu Lab hubs, switches, COB strips, and lamp pucks have been removed so you only buy what is used in the ESPHome model.

> 📖 **Full Electrical Engineering Reference:** See **[`POWER_ARCHITECTURE.md`](../POWER_ARCHITECTURE.md)** for the complete power budget, 3-branch fused wiring schematic, wire-gauge calculations, and multimeter commissioning checklist.

{BEGIN_MARKER}
{END_MARKER}

---

## 🗺️ Complete Mechanical & Electrical Connection Diagram (One-Cable 12V Solder-Free Edition)

```mermaid
flowchart TB
    subgraph HA["🏠 0. Home Assistant (Wi-Fi / Native ESPHome API)"]
        HA_CTRL["Home Assistant Dashboard & Automations: Auger Speed (0-100%), Track RGBIC Strip, Apple Topper Ring, & 12V Bus Telemetry"]
    end

    subgraph PWR["🔌 1. Single-Cable 12V Fused Distribution Hub (Inside trunk_base #1 Hollow Root Vault)"]
        PSU["BTF-LIGHTING 12V 5A 60W Adapter (B01D8FLSV8)"] ==>|"Single External 5.5x2.1mm Barrel Plug"| JACK["Rear (-X) Panel-Mount 5.5x2.1mm DC Jack (B07C7VSRBG, Ø 11.4mm Port)"]
        JACK -->|"+12V (Fuse F0=5A) & Star GND"| WAGO["WAGO 221-415 Lever-Nut Distribution Bus (B07NKT2P2F)"]
        WAGO -->|"Branch 1 & 3: Fuse F1 (2A) -> VIN & GND"| C008["M5Stack Atomic H-Driver (A092, 9-24V Rated) + ATOM Lite ESP32 (C008)"]
        WAGO -->|"Branch 2: Fuse F2 (3A) -> VIN+ & GND"| BUCK5["UCTRONICS 12V -> 5.0V 5A Screw-Terminal Buck (B07XXWQ49N) + 1000µF Cap (B07WPWFSNQ)"]
        HA_CTRL <-->|"Encrypted ESPHome API"| C008
        BC["Battery_Cover (2x M2.5x6mm Screws B0BYF4X65F)"] -.->|"Ø 5.0mm Port Exposes Atom Button (GPIO39) & RGB LED (GPIO27)"| C008
    end

    subgraph LIFT["🌲 2. Central Trunk Stack, Archimedes Auger & Topper Ring"]
        C008 -->|"Screw Terminals M1 & M2 (12V PWM GPIO19/23 + GPIO22 nFAULT)"| N20["12V 150 RPM N20 Gear Motor (B0BFRPMSW6)"]
        N20 -->|"Ø 3.0mm D-Shaft"| MCD["Motor_Clutch_Driver (Gold Hex Coupler)"]
        MCD -->|"Bottom Female Hex Socket"| AL["auger_lower (#1)"]
        AL -->|"Male/Female Hex Joint (#1 -> #2)"| AU["auger_upper (#2)"]
        TB["trunk_base (#1)"] -->|"Keyed Tenon (#1 -> #2)"| TM["trunk_mid (#2)"]
        TM -->|"Keyed Tenon (#2 -> #3)"| TT["trunk_top (#3)"]
        TT -->|"Top Rim (#3 -> #4)"| TOP["golden_apple_topper (#4)"]
        BUCK5 -->|"+5.0V & GND via WAGO-3/4 + B0CT827QQC Rear -X Conduit"| RING["Sparkleiot 16-Bit WS2812 RGB Ring (B09YTMNGTD, Ø 45mm)"]
        C008 -->|"A096 Grove Yellow (GPIO32 Data Only)"| RING
        RING -.->|"Seated in Ø 46.2mm Rim Recess of trunk_top (Z = 447.5mm)"| TOP
    end

    subgraph TRACK["🎢 3. Cantilever Brackets & 4.5-Turn Helical Track"]
        TB & TM & TT -->|"24x Helical Dovetail Slots (60 deg step)"| BRK["24x Cantilever Brackets (Tiers #4, #3, #2, #1)"]
        BRK -->|"Twin Ø 4.0mm Snap-Lock Pegs (u = ±10.6mm)"| SEG["14x Helical Track Segments (track_seg_01 #1 -> track_seg_14 #14)"]
        BUCK5 -->|"+5.0V & GND via WAGO-3/4 (Start + Top Dual-End Injection)"| COB["BTF-LIGHTING DC5V WS2812B Pebble/Seed Pixel Wire (B0CCS11V7H, 50 LEDs)"]
        C008 -->|"A096 Grove White (GPIO26 Data Only)"| COB
        COB -.->|"8.0 x 3.6mm Snap-In Dovetail Channel (4.6mm Throat)"| SEG
    end

    subgraph WIRELESS["🪄 4. Wireless Magnetic LEDs & Closed-Loop Marble Cascade"]
        AU -->|"Top Discharge Spout (Z = 435.5 -> 431.8mm)"| SEG
        SEG -->|"Bottom Return Chute (-90 deg, Z = 54.5mm)"| AL
        SEG -->|"8x Balcony Pegs (#1..#8, Ø 7.6mm)"| PLN["8x Solar System Planets (#1 Mercury -> #8 Neptune + 8x KA006 Single LEDs)"]
        MRB["6x Quarter-Turn Twist-Lock Apple Marbles (Hemi A + Hemi B + 6x KC013 Y-Shape 3-LEDs)"] -->|"Rolls Down G0 -> G5"| SEG
        WAND["Magic_LED_Wand (Ø 8x2mm Neodymium Magnet in Star Tip)"] -.->|"Tap to Toggle ON / Breathe / Strobe / OFF"| PLN & MRB
    end
```
"""


def _is_positive_int(val: object) -> bool:
    return isinstance(val, int) and not isinstance(val, bool) and val > 0


def parse_notes_kv(notes: str) -> dict[str, str]:
    """Parse 'key: value | key2: value2' metadata from notes string."""
    result: dict[str, str] = {}
    if not notes:
        return result
    for chunk in notes.split("|"):
        chunk = chunk.strip()
        if ":" in chunk:
            k, v = chunk.split(":", 1)
            result[k.strip()] = v.strip()
    return result


def validate_bom(data: object) -> None:
    if not isinstance(data, dict):
        raise ValueError("Top-level BOM YAML must be a mapping.")

    for top_key in ("electronics", "fasteners", "filament"):
        if top_key not in data:
            raise ValueError(f"Missing required top-level key: '{top_key}'")
        if not isinstance(data[top_key], list) or not data[top_key]:
            raise ValueError(f"Top-level key '{top_key}' must be a non-empty list.")

    seen_ids: set[str] = set()

    for section in ("electronics", "fasteners"):
        for idx, item in enumerate(data[section]):
            if not isinstance(item, dict):
                raise ValueError(f"{section}[{idx}] must be a mapping.")
            for req in PART_REQUIRED_FIELDS:
                if req not in item:
                    raise ValueError(f"{section}[{idx}] missing required field '{req}'.")
            part_id = item["id"]
            if not isinstance(part_id, str) or not part_id.strip():
                raise ValueError(f"{section}[{idx}].id must be a non-empty string.")
            if part_id in seen_ids:
                raise ValueError(f"Duplicate BOM id '{part_id}' in {section}[{idx}].")
            seen_ids.add(part_id)

            if not _is_positive_int(item["qty"]):
                raise ValueError(f"{section}[{idx}] ({part_id}): 'qty' must be a positive int, got {item['qty']!r}.")

            url = item["url"]
            if not isinstance(url, str) or not url.startswith("http"):
                raise ValueError(f"{section}[{idx}] ({part_id}): 'url' must start with 'http', got {url!r}.")

            if not isinstance(item["alt_skus"], list):
                raise ValueError(f"{section}[{idx}] ({part_id}): 'alt_skus' must be a list.")

            if not isinstance(item["optional"], bool):
                raise ValueError(f"{section}[{idx}] ({part_id}): 'optional' must be a boolean.")

            for str_field in ("sku", "name", "vendor", "spec", "where_used", "category", "notes"):
                if not isinstance(item[str_field], str):
                    raise ValueError(f"{section}[{idx}] ({part_id}): '{str_field}' must be a string.")

    for idx, item in enumerate(data["filament"]):
        if not isinstance(item, dict):
            raise ValueError(f"filament[{idx}] must be a mapping.")
        for req in FILAMENT_REQUIRED_FIELDS:
            if req not in item:
                raise ValueError(f"filament[{idx}] missing required field '{req}'.")
        if not _is_positive_int(item["est_weight_g"]):
            raise ValueError(f"filament[{idx}]: 'est_weight_g' must be a positive int.")
        if not _is_positive_int(item["spools"]):
            raise ValueError(f"filament[{idx}]: 'spools' must be a positive int.")
        v_url = item["vendor_url"]
        if not isinstance(v_url, str) or not v_url.startswith("http"):
            raise ValueError(f"filament[{idx}]: 'vendor_url' must start with 'http', got {v_url!r}.")
        for str_field in ("toolhead", "color_name", "hex", "material"):
            if not isinstance(item[str_field], str) or not item[str_field].strip():
                raise ValueError(f"filament[{idx}]: '{str_field}' must be a non-empty string.")


def _format_filament_link(item: dict) -> str:
    color_name = item["color_name"]
    material = item["material"]
    url = item["vendor_url"]
    m = re.match(r"^(\S+)\s+(.+?)\s+\(`([^`]+)`\)$", color_name)
    if m:
        finish, shade, sku = m.group(1), m.group(2), m.group(3)
        if material == "PETG":
            label = f"Bambu Lab Store — {material} {finish} (`{finish} {shade} {sku}`)"
        else:
            label = f"Bambu Lab Store — {material} {finish} (`{shade} {sku}`)"
    else:
        label = f"Bambu Lab Store — {material} ({color_name})"
    return f"[{label}]({url})"


def render_markdown_tables(data: dict) -> str:
    lines: list[str] = []

    # Section 1: Electronics
    lines.append("### 1. Electronics, Single-Cable 12V Power Distribution & Wireless Magnetic LEDs (100% Solder-Free)")
    lines.append("")
    lines.append("| Qty | Status / Role | Part Number / ASIN | Component | Spec / Dimensions | Direct Product Link | Where It Goes in the Tree |")
    lines.append("| :---: | :---: | :---: | :--- | :--- | :--- | :--- |")
    for item in data["electronics"]:
        meta = parse_notes_kv(item["notes"])
        qty_str = meta.get("qty_display", "*Optional*" if item["optional"] else f"**{item['qty']}×**")
        status_str = meta.get("status", "*Optional*" if item["optional"] else "**Required**")
        link_text = meta.get("link_text", f"{item['vendor']} — {item['name']} (`{item['sku']}`)")
        sku_str = f"**`{item['sku']}`**"
        name_str = f"**{item['name']}**"
        link_md = f"[{link_text}]({item['url']})"
        lines.append(
            f"| {qty_str} | {status_str} | {sku_str} | {name_str} | {item['spec']} | {link_md} | {item['where_used']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 2: Fasteners
    lines.append("### 2. Fasteners (Only 2 Screws Needed!)")
    lines.append("")
    lines.append("| Qty | Part Number / ASIN | Component | Spec / Dimensions | Direct Product Link | Purpose |")
    lines.append("| :---: | :---: | :--- | :--- | :--- | :--- |")
    for item in data["fasteners"]:
        meta = parse_notes_kv(item["notes"])
        qty_str = meta.get("qty_display", f"**{item['qty']}×**")
        link_text = meta.get("link_text", f"{item['vendor']} — {item['name']} (`{item['sku']}`)")
        sku_str = f"**`{item['sku']}`**"
        name_str = f"**{item['name']}**"
        link_md = f"[{link_text}]({item['url']})"
        lines.append(
            f"| {qty_str} | {sku_str} | {name_str} | {item['spec']} | {link_md} | {item['where_used']} |"
        )

    lines.append("")
    lines.append("---")
    lines.append("")

    # Section 3: Filament
    lines.append("### 3. 3D Printing Filament (Snapmaker U1 4-Toolhead Palettes — Max 4 Colors Per Plate)")
    lines.append("")
    lines.append("| Toolhead / Role | Color & Finish | Material | Est. Weight | Spools Needed | Direct Product Link |")
    lines.append("| :---: | :--- | :---: | :---: | :---: | :--- |")
    for item in data["filament"]:
        color_finish = f"**{item['color_name']}** (`{item['hex']}`)"
        weight_str = f"~{item['est_weight_g']:,} g"
        spools_n = item["spools"]
        spools_str = f"**{spools_n}× 1 kg {'spools' if spools_n != 1 else 'spool'}**"
        link_md = _format_filament_link(item)
        lines.append(
            f"| {item['toolhead']} | {color_finish} | {item['material']} | {weight_str} | {spools_str} | {link_md} |"
        )

    return "\n".join(lines)


def build_bom_markdown(data: dict, existing_md: str | None) -> str:
    base_md = existing_md if existing_md is not None else DEFAULT_BOM_MD_TEMPLATE
    if BEGIN_MARKER not in base_md or END_MARKER not in base_md:
        raise ValueError(f"{BOM_MD_PATH} must contain both '{BEGIN_MARKER}' and '{END_MARKER}' markers.")

    before, rest = base_md.split(BEGIN_MARKER, 1)
    _, after = rest.split(END_MARKER, 1)
    tables_block = render_markdown_tables(data)
    return f"{before}{BEGIN_MARKER}\n\n{tables_block}\n\n{END_MARKER}{after}"


def build_bom_csv(data: dict) -> str:
    buf = io.StringIO(newline="")
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(
        [
            "section",
            "id",
            "qty",
            "sku",
            "name",
            "vendor",
            "url",
            "alt_skus",
            "spec",
            "where_used",
            "category",
            "optional",
            "notes",
        ]
    )

    for section in ("electronics", "fasteners"):
        for item in data[section]:
            writer.writerow(
                [
                    section,
                    item["id"],
                    item["qty"],
                    item["sku"],
                    item["name"],
                    item["vendor"],
                    item["url"],
                    ";".join(str(s) for s in item["alt_skus"]),
                    item["spec"],
                    item["where_used"],
                    item["category"],
                    str(item["optional"]).lower(),
                    item["notes"],
                ]
            )

    for idx, item in enumerate(data["filament"], start=1):
        sku_match = re.search(r"`(\d+)`", item["color_name"])
        sku = sku_match.group(1) if sku_match else f"FIL-{idx:02d}"
        fil_id = f"filament-{sku}"
        spools_n = item["spools"]
        spec_str = f"~{item['est_weight_g']} g ({spools_n}x 1 kg {'spools' if spools_n != 1 else 'spool'})"
        writer.writerow(
            [
                "filament",
                fil_id,
                spools_n,
                sku,
                f"{item['material']} {item['color_name']} ({item['hex']})",
                "Bambu Lab Store",
                item["vendor_url"],
                "",
                spec_str,
                item["toolhead"],
                "filament",
                "false",
                "",
            ]
        )

    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate bom/bom.yaml and generate docs/BOM.md and bom/bom.csv.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if docs/BOM.md and bom/bom.csv are up to date without writing files.",
    )
    args = parser.parse_args()

    if not BOM_YAML_PATH.exists():
        print(f"ERROR: {BOM_YAML_PATH} does not exist.", file=sys.stderr)
        return 1

    raw = yaml.safe_load(BOM_YAML_PATH.read_text(encoding="utf-8"))
    validate_bom(raw)

    existing_md = BOM_MD_PATH.read_text(encoding="utf-8") if BOM_MD_PATH.exists() else None
    expected_md = build_bom_markdown(raw, existing_md)
    expected_csv = build_bom_csv(raw)

    if args.check:
        out_of_date: list[str] = []
        if existing_md != expected_md:
            out_of_date.append(str(BOM_MD_PATH.relative_to(ROOT_DIR)))
        existing_csv = BOM_CSV_PATH.read_text(encoding="utf-8") if BOM_CSV_PATH.exists() else None
        if existing_csv != expected_csv:
            out_of_date.append(str(BOM_CSV_PATH.relative_to(ROOT_DIR)))
        if out_of_date:
            print(
                f"ERROR: Out-of-date generated BOM files: {', '.join(out_of_date)}. "
                "Run 'uv run --with pyyaml python3 scripts/gen_bom.py' to update.",
                file=sys.stderr,
            )
            return 1
        print("OK: bom/bom.yaml is valid and docs/BOM.md + bom/bom.csv are up to date.")
        return 0

    BOM_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOM_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOM_MD_PATH.write_text(expected_md, encoding="utf-8")
    BOM_CSV_PATH.write_text(expected_csv, encoding="utf-8")
    print(f"Generated {BOM_MD_PATH.relative_to(ROOT_DIR)} and {BOM_CSV_PATH.relative_to(ROOT_DIR)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
