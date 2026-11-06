#!/usr/bin/env python3
"""
Texture analysis tool for the UE Texture Processor skill.
Reads one or more texture files and outputs a JSON report with channel stats,
identical-channel detection, value range analysis, and power-of-two checks.

Usage:
    python3 analyze_texture.py <file> [file2 ...]

Output: JSON array, one object per file.
"""

import sys
import os
import json
import array as array_mod
import numpy as np


def _is_power_of_two(n):
    return n > 0 and (n & (n - 1)) == 0


def _nearest_pot(n):
    if _is_power_of_two(n):
        return n
    lower = 1 << (n.bit_length() - 1)
    upper = lower << 1
    return lower if (n - lower) < (upper - n) else upper


def _channel_stats(arr):
    mn = float(arr.min())
    mx = float(arr.max())
    return {
        "min": round(mn, 6),
        "max": round(mx, 6),
        "mean": round(float(arr.mean()), 6),
        "is_ldr": mn >= 0.0 and mx <= 1.0,
        "has_negative": mn < 0.0,
        "exceeds_one": mx > 1.0,
        "pct_clipped_low": round(float((arr < 0.0).mean() * 100), 2) if mn < 0 else 0.0,
        "pct_clipped_high": round(float((arr > 1.0).mean() * 100), 2) if mx > 1 else 0.0,
    }


def _detect_identical_groups(channel_arrays):
    names = list(channel_arrays.keys())
    checked = set()
    groups = []
    for i, c1 in enumerate(names):
        if c1 in checked:
            continue
        group = [c1]
        for c2 in names[i + 1:]:
            if c2 in checked:
                continue
            if np.allclose(channel_arrays[c1], channel_arrays[c2], atol=1e-4, rtol=0):
                group.append(c2)
                checked.add(c2)
        if len(group) > 1:
            groups.append(group)
        checked.add(c1)
    return groups


def _analyze_exr(path):
    import OpenEXR
    import Imath

    exr = OpenEXR.InputFile(path)
    header = exr.header()
    dw = header["dataWindow"]
    w = dw.max.x - dw.min.x + 1
    h = dw.max.y - dw.min.y + 1
    channel_names = sorted(header["channels"].keys())

    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
    channel_arrays = {}
    for ch in channel_names:
        raw = array_mod.array("f", exr.channel(ch, FLOAT))
        channel_arrays[ch] = np.frombuffer(raw, dtype=np.float32).reshape(h, w).copy()

    return w, h, channel_names, channel_arrays, "float32", True


def _analyze_standard(path):
    from PIL import Image

    img = Image.open(path)
    w, h = img.size
    mode = img.mode

    if mode in ("I", "F"):
        arr = np.array(img, dtype=np.float32)
        max_val = float(arr.max()) if mode == "F" and arr.max() > 0 else 65535.0
        arr = arr / max_val
        channel_names = ["L"]
        bit_depth = "32" if mode == "F" else "16"
    elif mode in ("L",):
        arr = np.array(img, dtype=np.float32) / 255.0
        channel_names = ["L"]
        bit_depth = "8"
    elif mode in ("LA",):
        arr = np.array(img, dtype=np.float32) / 255.0
        channel_names = ["L", "A"]
        bit_depth = "8"
    elif mode in ("P",):
        img = img.convert("RGBA")
        arr = np.array(img, dtype=np.float32) / 255.0
        channel_names = ["R", "G", "B", "A"]
        bit_depth = "8"
    elif mode in ("RGB", "RGBA"):
        arr = np.array(img, dtype=np.float32) / 255.0
        channel_names = list(mode)
        bit_depth = "8"
    else:
        img = img.convert("RGBA")
        arr = np.array(img, dtype=np.float32) / 255.0
        channel_names = ["R", "G", "B", "A"]
        bit_depth = "8"

    channel_arrays = {}
    if arr.ndim == 2:
        channel_arrays[channel_names[0]] = arr
    else:
        for i, ch in enumerate(channel_names):
            channel_arrays[ch] = arr[:, :, i]

    return w, h, channel_names, channel_arrays, bit_depth, False


def analyze_file(path):
    ext = os.path.splitext(path)[1].lower()
    size_bytes = os.path.getsize(path)

    try:
        if ext == ".exr":
            w, h, channel_names, channel_arrays, bit_depth, is_hdr_format = _analyze_exr(path)
        else:
            w, h, channel_names, channel_arrays, bit_depth, is_hdr_format = _analyze_standard(path)
    except Exception as e:
        return {"path": path, "filename": os.path.basename(path), "error": str(e)}

    channel_stats = {ch: _channel_stats(channel_arrays[ch]) for ch in channel_names}
    identical_groups = _detect_identical_groups(channel_arrays)

    rgb = {"R", "G", "B"}
    is_effectively_grayscale = any(
        len(set(g) & rgb) >= 2 for g in identical_groups
    )

    non_alpha = {k: v for k, v in channel_stats.items() if k.upper() != "A"}
    values_are_ldr = all(v["is_ldr"] for v in non_alpha.values())
    has_negative_values = any(v["has_negative"] for v in non_alpha.values())
    has_values_exceeding_one = any(v["exceeds_one"] for v in non_alpha.values())

    alpha_stats = channel_stats.get("A") or channel_stats.get("a")
    alpha_is_flat_one  = alpha_stats is not None and abs(alpha_stats["min"] - 1.0) < 1e-4 and abs(alpha_stats["max"] - 1.0) < 1e-4
    alpha_is_flat_zero = alpha_stats is not None and abs(alpha_stats["max"]) < 1e-4
    alpha_is_meaningful = alpha_stats is not None and not alpha_is_flat_one and not alpha_is_flat_zero

    is_pow2 = _is_power_of_two(w) and _is_power_of_two(h)

    return {
        "path": path,
        "filename": os.path.basename(path),
        "format": ext.lstrip(".").upper(),
        "size_mb": round(size_bytes / (1024 * 1024), 2),
        "width": w,
        "height": h,
        "channels": channel_names,
        "bit_depth": bit_depth,
        "is_hdr_format": is_hdr_format,
        "channel_stats": channel_stats,
        "identical_channel_groups": identical_groups,
        "is_effectively_grayscale": is_effectively_grayscale,
        "values_are_ldr": values_are_ldr,
        "has_negative_values": has_negative_values,
        "has_values_exceeding_one": has_values_exceeding_one,
        "alpha_is_flat_one": alpha_is_flat_one,
        "alpha_is_flat_zero": alpha_is_flat_zero,
        "alpha_is_meaningful": alpha_is_meaningful,
        "is_power_of_two": is_pow2,
        "is_square": w == h,
        "nearest_pot_width": _nearest_pot(w) if not is_pow2 else None,
        "nearest_pot_height": _nearest_pot(h) if not is_pow2 else None,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: analyze_texture.py <file> [file2 ...]", file=sys.stderr)
        sys.exit(1)

    results = []
    for path in sys.argv[1:]:
        if not os.path.exists(path):
            results.append({"path": path, "error": "File not found"})
        else:
            results.append(analyze_file(path))

    print(json.dumps(results, indent=2))
