"""
texture_todo.py — Parse Unreal Engine .memreport files and produce a
prioritised texture to-do CSV listing every problematic texture.

Issues flagged:
  P0  Uncompressed format (PF_B8G8R8A8 / PF_FloatRGBA / Uncompressed=YES)
  P1  Non-streaming AND 0 usage count  (dormant resident memory)
  P1  FloatRGBA HDR format (unless already caught by P0)
  P2  Non-power-of-two dimensions

Usage:
    python texture_todo.py                              # scans current dir
    python texture_todo.py "G:/My Drive/FTS"           # scans a directory
    python texture_todo.py a.memreport b.memreport      # explicit files
    python texture_todo.py "G:/My Drive/FTS" -o E:/out/todo.csv
    python texture_todo.py "G:/My Drive/FTS" --min-mb 4  # only >= 4 MB
"""

import argparse
import csv
import math
import os
import re
import sys
from datetime import date
from pathlib import Path


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------

# Header line that marks the start of the texture table
_TEXTURE_SECTION = "Listing all textures."

# Compiled regex for a texture data line.
# Format (comma-separated, but first two fields each contain an inner comma):
#   CoookedWxH (KB, bias), CurrentWxH (KB), Format, LODGroup, Path, Stream, UnkRef, VT, UsageCount, NumMips, Uncompressed
_LINE_RE = re.compile(
    r"^(\d+)x(\d+)\s+\((\d+)\s+KB,[^)]+\),\s*"   # cooked dim + KB
    r"(\d+)x(\d+)\s+\((\d+)\s+KB\),\s*"            # current dim + KB
    r"(\w+),\s*"                                    # format
    r"(\w+),\s*"                                    # LOD group
    r"([^,]+),\s*"                                  # full path
    r"(\w+),\s*"                                    # Streaming
    r"(\w+),\s*"                                    # UnknownRef
    r"(\w+),\s*"                                    # VT
    r"(\d+),\s*"                                    # UsageCount
    r"(\d+),\s*"                                    # NumMips
    r"(\w+)"                                        # Uncompressed
)


def _parse_line(line: str) -> dict | None:
    m = _LINE_RE.match(line.strip())
    if not m:
        return None
    (
        cw, ch, c_kb,
        iw, ih, i_kb,
        fmt, lod_group, full_path,
        streaming, unk_ref, vt,
        usage_count, num_mips, uncompressed,
    ) = m.groups()

    # Extract short asset name from path like /Game/Foo/Bar/T_Asset.T_Asset
    path_clean = full_path.strip()
    asset_name = path_clean.rsplit(".", 1)[-1] if "." in path_clean else path_clean.rsplit("/", 1)[-1]

    return {
        "asset_name": asset_name,
        "ue_path": path_clean,
        "cooked_dim": f"{cw}x{ch}",
        "cooked_w": int(cw),
        "cooked_h": int(ch),
        "current_dim": f"{iw}x{ih}",
        "size_kb": int(i_kb),
        "size_mb": round(int(i_kb) / 1024, 2),
        "format": fmt,
        "texture_group": lod_group.replace("TEXTUREGROUP_", ""),
        "streaming": streaming,
        "vt": vt,
        "usage_count": int(usage_count),
        "num_mips": int(num_mips),
        "uncompressed": uncompressed,
    }


def parse_memreport(path: str) -> list[dict]:
    textures = []
    in_section = False
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            if _TEXTURE_SECTION in line:
                in_section = True
                continue
            if not in_section:
                continue
            tex = _parse_line(line)
            if tex:
                tex["source_file"] = Path(path).name
                textures.append(tex)
    return textures


# ---------------------------------------------------------------------------
# Issue classification
# ---------------------------------------------------------------------------

_UNCOMPRESSED_FORMATS = {"PF_B8G8R8A8", "PF_FloatRGBA", "PF_A32B32G32R32F", "PF_R32G32B32A32_UINT", "PF_R32_SINT"}
_HDR_FORMATS = {"PF_FloatRGBA", "PF_A32B32G32R32F"}


def _is_power_of_two(n: int) -> bool:
    return n > 0 and (n & (n - 1)) == 0


def _next_pow2(n: int) -> int:
    return 1 << math.ceil(math.log2(n)) if n > 1 else 1


def _compression_suggestion(tex: dict) -> str:
    group = tex["texture_group"]
    fmt = tex["format"]
    if fmt in _HDR_FORMATS:
        return "Compress to BC6H (HDR) or BC7 if LDR content"
    if "NormalMap" in group:
        return "Compress to BC5 (normal maps)"
    if group == "UI":
        w, h = tex["cooked_w"], tex["cooked_h"]
        if w > 1024 or h > 1024:
            tw, th = min(w, 1024), min(h, 1024)
            return f"Scale to {tw}x{th}; compress to BC7"
        return "Compress to BC7"
    return "Compress to BC7"


def classify(tex: dict) -> tuple[str, list[str], str]:
    """Return (priority, [issue strings], suggested_action)."""
    issues = []
    priority = None
    suggestions = []

    # P0 — uncompressed format
    is_uncompressed = (
        tex["uncompressed"] == "YES"
        or tex["format"] in _UNCOMPRESSED_FORMATS
    )
    is_transient = tex["ue_path"].startswith("/Engine/Transient")

    if is_uncompressed and not is_transient:
        issues.append(f"Uncompressed format ({tex['format']})")
        priority = "P0"
        suggestions.append(_compression_suggestion(tex))

    # P1 — non-streaming + 0 usage (dormant resident memory)
    if tex["streaming"] == "NO" and tex["usage_count"] == 0 and not is_transient:
        issues.append("Non-streaming / 0 usage (dormant resident)")
        if priority is None:
            priority = "P1"
        suggestions.append("Verify if active in gameplay loop; consider conditional load or removal")

    # P2 — non-power-of-two dimensions
    w, h = tex["cooked_w"], tex["cooked_h"]
    if not (_is_power_of_two(w) and _is_power_of_two(h)):
        pw, ph = _next_pow2(w), _next_pow2(h)
        issues.append(f"Non-power-of-two dims ({w}x{h})")
        if priority is None:
            priority = "P2"
        suggestions.append(f"Resize to {pw}x{ph} for optimal GPU memory alignment")

    return priority, issues, "; ".join(dict.fromkeys(suggestions))


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

COLUMNS = [
    "priority",
    "map_count",
    "appears_in",
    "asset_name",
    "ue_path",
    "size_mb",
    "cooked_dim",
    "format",
    "texture_group",
    "streaming",
    "vt",
    "num_mips",
    "is_uncompressed",
    "issues",
    "suggested_action",
]


def _map_name(source_file: str) -> str:
    """Extract 'Fungal' from 'Fungal-WindowsClient-22-10.08.21.memreport'."""
    return source_file.split("-")[0]


def build_rows(textures: list[dict], min_mb: float) -> list[dict]:
    rows = []
    for tex in textures:
        if tex["size_mb"] < min_mb:
            continue
        priority, issues, suggestion = classify(tex)
        if not issues:
            continue
        rows.append({
            "priority": priority,
            "_source_file": tex["source_file"],
            "asset_name": tex["asset_name"],
            "ue_path": tex["ue_path"],
            "size_mb": tex["size_mb"],
            "cooked_dim": tex["cooked_dim"],
            "format": tex["format"],
            "texture_group": tex["texture_group"],
            "streaming": tex["streaming"],
            "vt": tex["vt"],
            "num_mips": tex["num_mips"],
            "is_uncompressed": tex["uncompressed"],
            "issues": "; ".join(issues),
            "suggested_action": suggestion,
        })
    return rows


def deduplicate(rows: list[dict]) -> list[dict]:
    """One row per unique ue_path. Merge map appearances; keep worst priority."""
    seen: dict[str, dict] = {}
    for row in rows:
        key = row["ue_path"]
        map_name = _map_name(row["_source_file"])
        if key not in seen:
            seen[key] = dict(row)
            seen[key]["_maps"] = [map_name]
        else:
            existing = seen[key]
            if map_name not in existing["_maps"]:
                existing["_maps"].append(map_name)
            # keep highest priority
            if PRIORITY_ORDER.get(row["priority"], 99) < PRIORITY_ORDER.get(existing["priority"], 99):
                existing["priority"] = row["priority"]
            # union issues
            existing_issues = set(existing["issues"].split("; "))
            new_issues = set(row["issues"].split("; "))
            existing["issues"] = "; ".join(sorted(existing_issues | new_issues))

    result = []
    for row in seen.values():
        maps = row.pop("_maps")
        row.pop("_source_file")
        row["appears_in"] = ", ".join(maps)
        row["map_count"] = len(maps)
        result.append(row)
    return result


def sort_rows(rows: list[dict]) -> list[dict]:
    return sorted(
        rows,
        key=lambda r: (
            PRIORITY_ORDER.get(r["priority"], 99),
            -r["size_mb"],
        ),
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def find_memreports(inputs: list[str]) -> list[str]:
    paths = []
    for a in inputs:
        p = Path(a)
        if p.is_dir():
            paths.extend(sorted(p.glob("*.memreport")))
        elif p.suffix == ".memreport" and p.exists():
            paths.append(p)
        else:
            print(f"Warning: skipping '{a}'")
    if not paths:
        paths = sorted(Path(".").glob("*.memreport"))
    return [str(p) for p in paths]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("inputs", nargs="*", help="Directories or .memreport files")
    parser.add_argument("-o", "--output", help="Output CSV path (default: auto-named next to first memreport)")
    parser.add_argument("--min-mb", type=float, default=1.0, help="Minimum texture size in MB to include (default: 1.0)")
    args = parser.parse_args()

    memreports = find_memreports(args.inputs)
    if not memreports:
        print("No .memreport files found.")
        sys.exit(1)

    print(f"Processing {len(memreports)} memreport(s) (min size: {args.min_mb} MB):")
    all_rows = []
    for path in memreports:
        textures = parse_memreport(path)
        rows = build_rows(textures, args.min_mb)
        print(f"  {Path(path).name}: {len(textures)} textures parsed, {len(rows)} flagged")
        all_rows.extend(rows)

    all_rows = deduplicate(all_rows)
    all_rows = sort_rows(all_rows)

    if args.output:
        output_path = args.output
    else:
        output_dir = str(Path(memreports[0]).parent)
        output_path = os.path.join(output_dir, f"texture_todo_{date.today()}.csv")

    os.makedirs(Path(output_path).parent, exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(all_rows)

    p0 = sum(1 for r in all_rows if r["priority"] == "P0")
    p1 = sum(1 for r in all_rows if r["priority"] == "P1")
    p2 = sum(1 for r in all_rows if r["priority"] == "P2")
    print(f"\n{len(all_rows)} total rows (P0: {p0}, P1: {p1}, P2: {p2}) -> {output_path}")


if __name__ == "__main__":
    main()
