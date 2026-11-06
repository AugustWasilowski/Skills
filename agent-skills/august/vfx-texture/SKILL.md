---
name: vfx-texture
description: "Generate VFX textures (EXR, PNG, etc.) from a prompt or recipe. Handles color LUTs, gradient ramps, HDR element palettes, noise, solid fills, and arbitrary numpy-built images. Outputs linear half-float EXR by default. Use when August or Leo asks for a texture file for Unreal, Houdini, or any VFX pipeline."
trigger: /vfx-texture
---

# /vfx-texture

Generate VFX-ready texture files from a natural-language prompt or a structured recipe. Claude interprets the spec, writes and runs a Python script using the permanent tooling on Max, verifies the output, and drops the file to the inbox.

## Trigger

- **Slash command:** `/vfx-texture <description or recipe>`
- **Phrase:** "generate a texture for...", "bake a LUT...", "make an EXR of...", "create a VFX texture..."
- **Vikunja task:** `[VFX]` in title assigned to Max — read the description as the recipe

## Permanent tooling (already installed on Max)

- **Writer:** `python3` (system) + `OpenImageIO` (system `python3-openimageio`, v2.5.19.1)
- **Math:** `numpy` (in venv at `~/tools/aether-exr/venv`, or system numpy)
- **Verify:** `oiiotool` (`/usr/bin/oiiotool`, installed via `openimageio-tools`)
- **Reference script:** `~/tools/aether-exr/gen_palette.py` — the working T_AetherPalette pattern

**IMPORTANT:** The PyPI `OpenEXR` package requires CMake/C++ and fails to build on this box. Always use **system `python3` + `import OpenImageIO as oiio`** as the write backend, not PyPI OpenEXR.

## Default output location

`/mnt/storage/shares/_claude_inbox/vfx/<filename>` (Windows: `S:\_claude_inbox\vfx\`)

Unless the recipe or user specifies otherwise.

## How to execute

### Step 1 — Parse the recipe

Extract from the prompt or task description:
- **Dimensions** (W × H). Default: 256×256. For LUTs: 256×N where N = number of rows.
- **Channels** and **format**: EXR half-float linear (default), EXR float, PNG 8-bit, etc.
- **Pixel content type**: choose the right generator (see below).
- **Output filename** and path.
- **HDR tips needed?** (values > 1.0 — requires EXR, not PNG)

### Step 2 — Write a self-contained Python script

Use this template skeleton:

```python
import numpy as np
import OpenImageIO as oiio

OUTPUT = "/mnt/storage/shares/_claude_inbox/vfx/FILENAME.exr"
W, H = 256, 256

img = np.zeros((H, W, 3), dtype=np.float32)

# --- fill img here ---

# Write EXR (half-float, linear)
spec = oiio.ImageSpec(W, H, 3, oiio.HALF)
spec.channelnames = ["R", "G", "B"]
spec.attribute("compression", "none")
out = oiio.ImageOutput.create(OUTPUT)
out.open(OUTPUT, spec)
out.write_image(img)
out.close()

# Verify
inp = oiio.ImageInput.open(OUTPUT)
rspec = inp.spec()
data = inp.read_image(oiio.FLOAT)
inp.close()
print(f"wrote {OUTPUT}")
print(f"verify: {rspec.width}x{rspec.height} ch={rspec.nchannels} fmt={rspec.format} min={data.min():.4f} max={data.max():.4f}")
```

For **PNG output** (8-bit sRGB), swap the spec:
```python
spec = oiio.ImageSpec(W, H, 3, oiio.UINT8)
spec.attribute("oiio:ColorSpace", "sRGB")
```

For **RGBA** (4 channels), use `oiio.HALF` and `channelnames = ["R","G","B","A"]`.

### Step 3 — Pixel content generators

#### Color ramp LUT (N rows, horizontal gradient)
```python
def s2l(h):  # sRGB hex -> linear float [r,g,b]
    r,g,b = [int(h[i:i+2],16)/255 for i in (1,3,5)]
    f = lambda c: c/12.92 if c<=0.04045 else ((c+0.055)/1.055)**2.4
    return np.array([f(r),f(g),f(b)])

# ramps: list of lists of (t, "#rrggbb") stop pairs, one per row
T = (np.arange(W)+0.5)/W  # texel-center positions
for row, stops in enumerate(ramps):
    pos = [s[0] for s in stops]
    for ch in range(3):
        img[row,:,ch] = np.interp(T, pos, [s2l(s[1])[ch] for s in stops])
    # Optional HDR bloom boost at bright tip:
    # boost = 1.0 + 0.6*np.clip((T-0.80)/0.20,0,1)**1.5
    # img[row] *= boost[:,None]
```

#### Solid color fill
```python
img[:] = s2l("#rrggbb")  # or just [r, g, b] in linear
```

#### UV gradient (U=red, V=green — useful for debugging)
```python
u = (np.arange(W)+0.5)/W
v = (np.arange(H)+0.5)/H
img[:,:,0] = u[np.newaxis,:]
img[:,:,1] = v[:,np.newaxis]
img[:,:,2] = 0.0
```

#### Radial gradient (center=bright, edge=dark)
```python
u = (np.arange(W)+0.5)/W - 0.5
v = (np.arange(H)+0.5)/H - 0.5
r = np.sqrt(u[np.newaxis,:]**2 + v[:,np.newaxis]**2) * 2.0
img[:,:,0] = img[:,:,1] = img[:,:,2] = np.clip(1.0-r, 0, 1)
```

#### Tileable noise (value noise, seeded)
```python
rng = np.random.default_rng(seed=42)
from scipy.ndimage import gaussian_filter  # or roll your own
noise = rng.random((H, W)).astype(np.float32)
noise = gaussian_filter(noise, sigma=4)
noise = (noise - noise.min()) / (noise.ptp() + 1e-8)
img[:,:,0] = img[:,:,1] = img[:,:,2] = noise
```

#### Alpha mask (single-channel, write as RGBA or L)
```python
spec = oiio.ImageSpec(W, H, 1, oiio.HALF)
spec.channelnames = ["A"]
# img shape (H,W,1)
```

### Step 4 — Run and verify

1. Write the script to `~/tools/aether-exr/<taskname>.py`
2. Run with `python3 ~/tools/aether-exr/<taskname>.py`
3. Confirm oiiotool output: `oiiotool --info -v <output>`
4. Assert: correct dimensions, correct channel count, correct format, and `max > 1.0` if HDR was requested

### Step 5 — Report back

For a slash command: state the output path, oiiotool one-liner, and min/max.

For a Vikunja task: post a comment with path, min/max, oiiotool verify line, and note the venv/tooling used. Mark task done.

## Common mistakes to avoid

- **Do NOT use PyPI `OpenEXR`** — it needs CMake and fails to build on this box.
- **Do NOT write HDR content to PNG** — PNG clamps to [0,1]. Always use EXR for HDR.
- **Do NOT apply sRGB gamma** to content destined for Unreal's linear pipeline — keep everything linear float.
- **Do NOT convert from an existing PNG** for HDR ramps — the PNG is already clamped. Regenerate from the source math.
- **Texel-center sampling**: use `(np.arange(W)+0.5)/W` not `np.linspace(0,1,W)` — the latter clips the endpoints and breaks tiling.

## Extending for other formats

- **`.hdr` (Radiance RGBE):** same OIIO writer, just change the output filename extension. OIIO auto-selects the format.
- **`.tiff` (32-bit float):** `spec = oiio.ImageSpec(W, H, C, oiio.FLOAT)` — useful for displacement or data maps.
- **`.png` (8-bit):** apply an sRGB transfer if the content is linear before quantizing, or let OIIO do it via `colorconvert`.

## Reference files

- `~/tools/aether-exr/gen_palette.py` — working T_AetherPalette example (color LUT, HDR ramps, HALF EXR via OIIO)
- `/mnt/storage/shares/_claude_inbox/vfx/` — default drop location
