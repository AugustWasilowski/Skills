#!/usr/bin/env python3
"""
Texture processing tool for the UE Texture Processor skill.
Handles resizing, bit-depth conversion, channel extraction, format conversion,
and optional optipng post-processing.

Usage:
    python3 process_texture.py <input> <output> [options]

Options:
    --resize WxH        Target dimensions, e.g. 1024x1024
    --grayscale         Convert to single-channel grayscale (uses R channel for EXR)
    --channel R|G|B|A   Extract a specific channel as grayscale
    --bits 8|16         Output bit depth (default: 8)
    --normalize         Remap values to [0, 1] before quantising (use only when asked)
    --optipng           Run optipng -o7 on the output (PNG only)
    --no-alpha          Strip alpha channel from output

Notes:
    - For EXR input, if all RGB channels are identical the R channel is used automatically
      unless --channel is specified.
    - Clipping (not normalizing) is the default for out-of-range values. Pass --normalize
      only when the user explicitly requests value remapping.
    - Output format is inferred from the output file extension.
"""

import sys
import os
import argparse
import array as array_mod
import subprocess
import numpy as np


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_exr(path):
    import OpenEXR
    import Imath

    exr = OpenEXR.InputFile(path)
    header = exr.header()
    dw = header["dataWindow"]
    w = dw.max.x - dw.min.x + 1
    h = dw.max.y - dw.min.y + 1
    channel_names = sorted(header["channels"].keys())

    FLOAT = Imath.PixelType(Imath.PixelType.FLOAT)
    channels = {}
    for ch in channel_names:
        raw = array_mod.array("f", exr.channel(ch, FLOAT))
        channels[ch] = np.frombuffer(raw, dtype=np.float32).reshape(h, w).copy()

    return channels, w, h


def _load_standard(path):
    from PIL import Image

    img = Image.open(path)
    mode = img.mode
    w, h = img.size

    if mode == "P":
        img = img.convert("RGBA")
        mode = "RGBA"

    if mode in ("I", "F"):
        arr = np.array(img, dtype=np.float32)
        max_val = 65535.0 if mode == "I" else (float(arr.max()) or 1.0)
        arr /= max_val
        channels = {"L": arr}
    elif mode == "L":
        arr = np.array(img, dtype=np.float32) / 255.0
        channels = {"L": arr}
    elif mode == "LA":
        arr = np.array(img, dtype=np.float32) / 255.0
        channels = {"L": arr[:, :, 0], "A": arr[:, :, 1]}
    elif mode == "RGB":
        arr = np.array(img, dtype=np.float32) / 255.0
        channels = {"R": arr[:, :, 0], "G": arr[:, :, 1], "B": arr[:, :, 2]}
    elif mode == "RGBA":
        arr = np.array(img, dtype=np.float32) / 255.0
        channels = {"R": arr[:, :, 0], "G": arr[:, :, 1], "B": arr[:, :, 2], "A": arr[:, :, 3]}
    else:
        img = img.convert("RGBA")
        arr = np.array(img, dtype=np.float32) / 255.0
        channels = {"R": arr[:, :, 0], "G": arr[:, :, 1], "B": arr[:, :, 2], "A": arr[:, :, 3]}

    return channels, w, h


# ---------------------------------------------------------------------------
# Processing helpers
# ---------------------------------------------------------------------------

def _are_rgb_identical(channels):
    rgb = [channels.get(c) for c in ("R", "G", "B") if c in channels]
    if len(rgb) < 2:
        return False
    return all(np.allclose(rgb[0], c, atol=1e-4, rtol=0) for c in rgb[1:])


def _resize_array(arr, target_w, target_h):
    from PIL import Image

    # Temporarily wrap as PIL image (float32 → uint16 for quality, then back)
    uint16 = (np.clip(arr, 0, 1) * 65535).astype(np.uint16)
    img = Image.fromarray(uint16.astype(np.int32), mode="I")
    img = img.resize((target_w, target_h), Image.LANCZOS)
    resized = np.array(img, dtype=np.float32) / 65535.0
    return resized


def _to_pil(arr, bits):
    from PIL import Image

    if arr.ndim == 2:
        # Grayscale
        if bits == 16:
            data = (np.clip(arr, 0, 1) * 65535).astype(np.uint16)
            img = Image.fromarray(data.astype(np.int32), mode="I")
        else:
            data = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
            img = Image.fromarray(data, mode="L")
    elif arr.shape[2] == 3:
        if bits == 16:
            # PIL doesn't support 16-bit RGB PNG natively; use 8-bit fallback
            print("Warning: 16-bit RGB PNG not fully supported; saving as 8-bit RGB", file=sys.stderr)
            data = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
            img = Image.fromarray(data, mode="RGB")
        else:
            data = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
            img = Image.fromarray(data, mode="RGB")
    elif arr.shape[2] == 4:
        data = (np.clip(arr, 0, 1) * 255).astype(np.uint8)
        img = Image.fromarray(data, mode="RGBA")
    else:
        raise ValueError(f"Unexpected array shape: {arr.shape}")

    return img


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def process(input_path, output_path, resize=None, grayscale=False, channel=None,
            bits=8, normalize=False, no_alpha=False, use_optipng=False):

    ext_in = os.path.splitext(input_path)[1].lower()

    # Load
    if ext_in == ".exr":
        channels, src_w, src_h = _load_exr(input_path)
    else:
        channels, src_w, src_h = _load_standard(input_path)

    # Channel selection
    if channel:
        ch = channel.upper()
        if ch not in channels:
            raise ValueError(f"Channel '{ch}' not found. Available: {list(channels.keys())}")
        arr = channels[ch]  # 2D
    elif grayscale:
        if "R" in channels:
            arr = channels["R"]
        elif "L" in channels:
            arr = channels["L"]
        else:
            arr = list(channels.values())[0]
    else:
        # Build stacked array
        ch_names = list(channels.keys())
        if no_alpha:
            ch_names = [c for c in ch_names if c.upper() != "A"]
        if len(ch_names) == 1:
            arr = channels[ch_names[0]]
        else:
            arr = np.stack([channels[c] for c in ch_names], axis=2)

    # Optionally normalize
    if normalize:
        mn, mx = arr.min(), arr.max()
        if mx > mn:
            arr = (arr - mn) / (mx - mn)
            print(f"Normalized: [{mn:.4f}, {mx:.4f}] → [0, 1]")
        else:
            print(f"Normalize skipped: flat value {mn:.4f}")

    # Resize
    if resize:
        target_w, target_h = resize
        if arr.ndim == 2:
            arr = _resize_array(arr, target_w, target_h)
        else:
            # Resize each channel
            resized = np.stack([_resize_array(arr[:,:,i], target_w, target_h)
                                for i in range(arr.shape[2])], axis=2)
            arr = resized
        print(f"Resized: {src_w}x{src_h} → {target_w}x{target_h}")

    # Convert to PIL and save
    img = _to_pil(arr, bits)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    ext_out = os.path.splitext(output_path)[1].lower()
    if ext_out == ".png":
        img.save(output_path, format="PNG", compress_level=9, optimize=True)
    elif ext_out in (".tga", ".targa"):
        img.save(output_path, format="TGA")
    elif ext_out in (".tif", ".tiff"):
        img.save(output_path, format="TIFF")
    elif ext_out == ".jpg":
        if img.mode in ("RGBA", "L") and img.mode != "RGB":
            img = img.convert("RGB")
        img.save(output_path, format="JPEG", quality=95)
    else:
        img.save(output_path)

    size_kb = os.path.getsize(output_path) / 1024
    print(f"Saved: {output_path} ({size_kb:.1f} KB)")

    # optipng post-processing
    if use_optipng and ext_out == ".png":
        result = subprocess.run(
            ["optipng", "-o7", "-quiet", output_path],
            capture_output=True, text=True
        )
        if result.returncode == 0:
            new_size_kb = os.path.getsize(output_path) / 1024
            print(f"optipng: {size_kb:.1f} KB → {new_size_kb:.1f} KB")
        else:
            print(f"optipng warning: {result.stderr.strip()}", file=sys.stderr)

    return output_path


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process a texture file for UE import.")
    parser.add_argument("input", help="Input texture file path")
    parser.add_argument("output", help="Output file path")
    parser.add_argument("--resize", help="Target size WxH, e.g. 1024x1024")
    parser.add_argument("--grayscale", action="store_true", help="Output single-channel grayscale")
    parser.add_argument("--channel", help="Extract specific channel (R/G/B/A) as grayscale")
    parser.add_argument("--bits", type=int, choices=[8, 16], default=8, help="Output bit depth")
    parser.add_argument("--normalize", action="store_true",
                        help="Remap value range to [0,1] before quantising")
    parser.add_argument("--no-alpha", action="store_true", help="Strip alpha channel")
    parser.add_argument("--optipng", action="store_true", help="Run optipng -o7 on PNG output")

    args = parser.parse_args()

    resize = None
    if args.resize:
        try:
            w_str, h_str = args.resize.lower().split("x")
            resize = (int(w_str), int(h_str))
        except ValueError:
            print(f"Invalid --resize value: {args.resize}. Expected format: WxH", file=sys.stderr)
            sys.exit(1)

    process(
        input_path=args.input,
        output_path=args.output,
        resize=resize,
        grayscale=args.grayscale,
        channel=args.channel,
        bits=args.bits,
        normalize=args.normalize,
        no_alpha=args.no_alpha,
        use_optipng=args.optipng,
    )
