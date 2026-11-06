#!/usr/bin/env python3
"""Pre-flight analyzer for the FTS texture audit pipeline.

Reads stage2_proposed_APPROVED.csv, narrows to a folder prefix, and reports:
  - Counts by action and confidence
  - Stage 3 touchable count (high + in ACTION_FILTER)
  - Estimated savings
  - Subfolder breakdown one level under the target folder
  - Danger pattern detections (HARD-BLOCK or WARN)

Exit codes:
  0 - clean or WARN-only; safe to proceed (skill should still surface warnings)
  1 - at least one HARD-BLOCK pattern detected; do not proceed
  2 - usage error or CSV not found

Usage:
    python pre_flight.py --folder /Game/Hermes/Art/Environment/Wasteland/

By default reads the canonical Windows path. Override with --csv when running
from a Linux mount (e.g. /sessions/<id>/mnt/AssetAudit/stage2_proposed_APPROVED.csv).
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import Counter

DEFAULT_CSV = r"F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\stage2_proposed_APPROVED.csv"

# Must mirror Stage 3's ACTION_FILTER. If the user changes Stage 3, update here.
ACTION_FILTER = {"reassign_group", "recompress", "cap_max_size", "flag_only"}

# Pivot Painter / data-texture name patterns. These textures are intentionally
# HDR-uncompressed and routed to review; don't flag them as anomalies.
PIVOT_PAINTER_PATTERNS = [
    re.compile(r"PivotPoint", re.IGNORECASE),
    re.compile(r"_PP\d", re.IGNORECASE),
    re.compile(r"_PI$", re.IGNORECASE),
    re.compile(r"_XVE", re.IGNORECASE),
    re.compile(r"Xaxis_Xextent", re.IGNORECASE),
    re.compile(r"Yaxis_Yextent", re.IGNORECASE),
    re.compile(r"Zaxis_Zextent", re.IGNORECASE),
    re.compile(r"_HDR$", re.IGNORECASE),
    re.compile(r"_RVT_", re.IGNORECASE),
]


def is_pivot_painter(name):
    return any(p.search(name) for p in PIVOT_PAINTER_PATTERNS)


def load_rows(csv_path, folder):
    rows = []
    with open(csv_path, newline="", encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("package_path", "").startswith(folder):
                rows.append(r)
    return rows


def detect_patterns(touchable):
    """Return a list of detected pattern flags. Each flag has severity, name,
    count, samples, and explanation."""
    flags = []

    # HARD-BLOCK: normal-map compression flip on real normals
    flips = []
    for r in touchable:
        if (
            r.get("compression_settings") == "TC_Normalmap"
            and r.get("proposed_compression")
            and r.get("proposed_compression") != "TC_Normalmap"
            and (r.get("suffix") == "_N" or "normal" in r.get("role", "").lower())
        ):
            flips.append(r["package_path"])
    if flips:
        flags.append({
            "severity": "BLOCK",
            "name": "Normal-map compression flip on real normal",
            "count": len(flips),
            "samples": flips[:5],
            "explanation": (
                "These rows are normal maps (suffix _N or role=normal) currently in "
                "TC_Normalmap, but Stage 2 proposed a different compression. That would "
                "corrupt the normal data. Almost certainly a classifier bug."
            ),
        })

    # HARD-BLOCK / WARN: /Demos contamination in touchable cohort
    demos = [r for r in touchable if "/Game/Demos/" in r.get("package_path", "")]
    if len(demos) > 10:
        flags.append({
            "severity": "BLOCK",
            "name": "/Demos contamination (significant)",
            "count": len(demos),
            "samples": [r["package_path"] for r in demos[:5]],
            "explanation": (
                "/Game/Demos/ is excluded from the audit by policy. Significant "
                "contamination in the touchable cohort means Stage 2's routing is "
                "broken - investigate before applying."
            ),
        })
    elif demos:
        flags.append({
            "severity": "WARN",
            "name": "/Demos contamination (small)",
            "count": len(demos),
            "samples": [r["package_path"] for r in demos[:5]],
            "explanation": (
                "A few /Demos rows in the touchable cohort. Should be 0; may indicate "
                "Stage 2 misrouting on edge cases."
            ),
        })

    # WARN: mix-map mislabel pattern (the Drones pattern from the pilot)
    mix = [
        r for r in touchable
        if r.get("current_group") == "TEXTUREGROUP_WorldNormalMap"
        and r.get("proposed_group") == "TEXTUREGROUP_World"
        and r.get("suffix") == "_M"
        and r.get("compression_settings") == "TC_Normalmap"
    ]
    if mix:
        flags.append({
            "severity": "WARN",
            "name": "Mix-map mislabel pattern",
            "count": len(mix),
            "samples": [r["package_path"] for r in mix[:5]],
            "explanation": (
                "_M textures currently labeled WorldNormalMap with TC_Normalmap "
                "compression. Almost certainly mix maps that were authored into the "
                "wrong group. The audit will move them to World; the user should "
                "also update materials referencing them."
            ),
        })

    # WARN: HDR-uncompressed in non-Pivot-Painter context
    hdr_unc = [
        r for r in touchable
        if r.get("compression_class") == "hdr_uncompressed"
        and not is_pivot_painter(r.get("object_name", ""))
    ]
    if hdr_unc:
        flags.append({
            "severity": "WARN",
            "name": "HDR-uncompressed (non-Pivot Painter)",
            "count": len(hdr_unc),
            "samples": [r["package_path"] for r in hdr_unc[:5]],
            "explanation": (
                "HDR-uncompressed textures that aren't Pivot Painter index data. "
                "Could be intentional (cinematic, HDR effects, lookup tables) or a "
                "memory leak (4K texture stored as TC_Default at 12 bpp). Review the "
                "rationale field on these rows."
            ),
        })

    return flags


def main():
    p = argparse.ArgumentParser(description="Pre-flight analyzer for FTS texture audit Stage 3.")
    p.add_argument("--folder", required=True, help="Folder prefix, e.g. /Game/Hermes/Art/Environment/Wasteland/")
    p.add_argument("--csv", default=DEFAULT_CSV, help="Path to stage2_proposed_APPROVED.csv.")
    args = p.parse_args()

    folder = args.folder if args.folder.endswith("/") else args.folder + "/"

    try:
        rows = load_rows(args.csv, folder)
    except FileNotFoundError:
        print("ERROR: CSV not found at " + args.csv, file=sys.stderr)
        print("If running from a Linux bash mount, pass --csv /sessions/<id>/mnt/AssetAudit/stage2_proposed_APPROVED.csv", file=sys.stderr)
        return 2

    if not rows:
        print("No rows in " + folder + ". Verify the path is correct (must match an exact prefix in stage2_proposed_APPROVED.csv).")
        return 2

    touchable = [r for r in rows if r.get("confidence") == "high" and r.get("proposed_action") in ACTION_FILTER]

    print("=== Pre-flight: " + folder + " ===")
    print("Total rows in folder: " + str(len(rows)))
    print("  By action:    " + str(dict(Counter(r.get("proposed_action") for r in rows))))
    print("  By confidence:" + str(dict(Counter(r.get("confidence") for r in rows))))
    print()
    print("Stage 3 touchable rows (high + in ACTION_FILTER): " + str(len(touchable)))
    print("  By action:        " + str(dict(Counter(r.get("proposed_action") for r in touchable))))
    print("  By proposed_group:" + str(dict(Counter(r.get("proposed_group") for r in touchable))))

    try:
        savings_mb = sum(float(r.get("estimated_savings_mb") or 0) for r in touchable)
        print("  Estimated savings: {:,.1f} MB ({:,.2f} GB)".format(savings_mb, savings_mb / 1024))
    except Exception:
        pass

    # Subfolder breakdown one level deeper than the target folder.
    # /Game/Hermes/Art/Environment/Volcanic/ has 6 slashes; the segment
    # one level deeper sits at split index 6.
    folder_depth = folder.count("/")
    subs = sorted({
        r["package_path"].split("/")[folder_depth]
        for r in rows
        if len(r["package_path"].split("/")) > folder_depth
    })
    if subs:
        print("  Subfolders one level deeper: " + str(subs))

    print()
    flags = detect_patterns(touchable)
    blocks = [f for f in flags if f["severity"] == "BLOCK"]
    warns = [f for f in flags if f["severity"] == "WARN"]

    if blocks:
        print("=== HARD-BLOCK FLAGS (must resolve before applying) ===")
        for f in blocks:
            print("  [BLOCK] " + f["name"] + ": " + str(f["count"]) + " rows")
            print("    " + f["explanation"])
            for s in f["samples"]:
                print("      - " + s)
            print()

    if warns:
        print("=== WARNINGS (review but does not block) ===")
        for f in warns:
            print("  [WARN] " + f["name"] + ": " + str(f["count"]) + " rows")
            print("    " + f["explanation"])
            for s in f["samples"]:
                print("      - " + s)
            print()

    if not flags:
        print("=== Pattern checks: clean ===")

    return 1 if blocks else 0


if __name__ == "__main__":
    sys.exit(main())
