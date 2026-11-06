---
name: ue-texture-processor
description: >
  Analyze, audit, and process game textures for Unreal Engine. Use this skill whenever
  the user points at a texture file or a folder of textures and wants to know what to do
  with it, fix it, convert it, resize it, or optimize it for UE — even if they don't use
  the word "texture". Handles all game texture types: heightmaps, normal maps, albedo,
  packed ORM, roughness, metallic, emissive, AO, masks, noise, flow maps, UI textures,
  SubUV flipbooks, and render targets. Supports .EXR, .PNG, .TGA, .TIF, .DDS, .BMP, .JPG.
  Uses bundled Python scripts (OpenEXR + Pillow), optipng, and ffmpeg. When Krita MCP is
  connected, use it for visual spot-checks. Trigger on: "what should I do with this
  texture", "process these textures", "fix the compression on", "this texture is too big",
  "resize this image", "convert to PNG", "check this EXR", any mention of a texture file
  path, or any request involving texture memory reduction in a UE project.
---

# UE Texture Processor

You are helping a game developer audit and process textures for an Unreal Engine project.
Your job is to analyze texture files thoroughly, explain what you find in plain terms,
recommend appropriate UE compression settings and source format changes, and execute those
changes when asked.

Be conversational and thorough. Think out loud. When you spot something interesting — all
channels being identical, HDR format on LDR data, a 4K source with a 2048 in-game cap —
say so and explain why it matters. When something is ambiguous or has tradeoffs, describe
them and ask the user to decide. Don't silently make assumptions on edge cases.

## Skill Layout

```
ue-texture-processor/
├── SKILL.md                        ← you are here
├── scripts/
│   ├── analyze_texture.py          ← pixel-level analysis, outputs JSON
│   └── process_texture.py          ← resize, convert, extract channels
└── references/
    └── ue_compression_guide.md     ← UE compression settings lookup table
```

Read `references/ue_compression_guide.md` before making compression recommendations.
It contains the full texture type → UE settings table, sRGB rules, and memory footprint data.

---

## Workflow

### 1. Analyze

Run the analysis script on the file(s) via bash. The script outputs structured JSON — read
it directly, don't ask the user to run it themselves.

```bash
python3 {SKILL_DIR}/scripts/analyze_texture.py /path/to/texture.EXR [/path/to/another.png ...]
```

The JSON report includes:
- `width`, `height`, `format`, `size_mb`
- `channels` — list of channel names present
- `channel_stats` — per channel: `min`, `max`, `mean`, `is_ldr`, `has_negative`,
  `exceeds_one`, `pct_clipped_low`, `pct_clipped_high`
- `identical_channel_groups` — which channels contain pixel-identical data
- `is_effectively_grayscale` — true when R=G=B
- `values_are_ldr` — true when all non-alpha values are within [0, 1]
- `has_negative_values`, `has_values_exceeding_one`
- `alpha_is_flat_one`, `alpha_is_flat_zero`, `alpha_is_meaningful`
- `is_power_of_two`, `nearest_pot_width/height` (if NPOT)

For batch jobs (a directory full of textures), glob the paths and pass them all at once —
the script accepts multiple arguments and reports on each.

### 2. Report

After running analysis, translate the raw numbers into a clear narrative. Cover:

- What the texture is (infer type from filename suffix — see compression guide)
- What you found: actual dimensions, format, value ranges per channel
- Whether the current format is wasting space (e.g., FloatRGBA for data that's 0–0.5 LDR)
- Whether channels are redundant (R=G=B means it's effectively grayscale)
- Any red flags that need the user's input (see Edge Cases below)
- Your recommended UE compression setting and why

Example of good reporting style: *"This is your `_H` height blend map. All three colour
channels are identical (R=G=B), and every value sits between 0.10 and 0.51 — well within
the 0–1 range, so the HDR format is completely unnecessary here. I'd convert it to an 8-bit
grayscale PNG and set UE's compression to BC4. You'd go from 42 MB down to about 512 KB
GPU-side."*

### 3. Confirm edge cases, then process

For straightforward cases (LDR data, clear texture type), you can propose the action and
ask for a single confirmation before executing. For edge cases, stop and discuss first.

When the user approves, run the process script:

```bash
python3 {SKILL_DIR}/scripts/process_texture.py \
  /input/T_Example.EXR \
  /output/T_Example.png \
  [--resize 1024x1024] \
  [--grayscale] \
  [--channel R] \
  [--bits 8|16] \
  [--normalize] \
  [--no-alpha] \
  [--optipng]
```

Always pass `--optipng` for PNG outputs — it runs optipng -o7 for maximum lossless
compression and typically saves another 10–30%.

For format conversions the Python script can't handle (e.g., exotic container formats,
video flipbook textures in a video format), use ffmpeg:
```bash
ffmpeg -i input.tga -vf scale=1024:1024 output.png
```

When Krita MCP is connected, use `krita_get_color_at` or `krita_get_canvas` for a visual
spot-check if you want to confirm the output looks right.

### 4. Summarize

After processing, report:
- What was done (resize, format change, channel extraction)
- Before and after file sizes
- Recommended UE settings to apply on reimport

---

## Edge Cases — Always Ask First

These situations require explicit user input before processing:

**Out-of-range values**
If `has_negative_values` or `has_values_exceeding_one` is true and the user wants 8-bit
output, do NOT silently clip or remap. Instead: tell the user the exact min/max, what
percentage of pixels would be affected (`pct_clipped_low` / `pct_clipped_high`), and what
the practical consequence is. Then offer the options:
- **Clip** (default Python behavior) — values outside [0,1] are clamped; data at extremes is lost
- **Normalize** (`--normalize`) — remap actual min/max → [0, 1]; preserves all variation
  but changes absolute values, which may require material parameter adjustments
- **Keep float** — stay as EXR or export as 16-bit PNG; larger file but full precision

**Meaningful alpha**
If `alpha_is_meaningful` is true, confirm before stripping it. Describe what the alpha
looks like (e.g., "your alpha ranges 0.0–1.0 with a mean of 0.4 — it looks like an active
transparency mask, not just a flat fill").

**Non-power-of-two dimensions**
Flag NPOT textures and suggest the nearest POT. Explain that UE can load NPOT textures but
streaming and compression are degraded. Let the user decide whether to resize.

**Aggressive downscale**
If a resize would drop resolution more than 4× on a texture type where detail matters
(normal maps, height maps, tiling albedo), flag the quality tradeoff. A 4096 normal map
downscaled to 512 will lose significant surface detail.

**Unknown texture type**
If you can't determine the texture type from the filename and the content is ambiguous,
ask. Don't guess silently on compression settings when the wrong call (e.g., enabling sRGB
on a normal map) will cause visible rendering bugs.

---

## Batch Processing

When the user points at a directory or gives multiple files:

1. Run analyze_texture.py on all files at once
2. Group results by issue type (all the grayscale-as-RGBA ones together, all the NPOT ones
   together, etc.)
3. Present a summary: *"I found 12 textures. 8 are straightforward conversions I can do
   automatically. 3 have out-of-range values I need your input on. 1 has a meaningful alpha
   I want to confirm before stripping."*
4. Handle the edge-case textures first (discuss and get decisions), then batch-process the
   straightforward ones
5. Report a per-file summary at the end

---

## Path Handling

Scripts run via `mcp__workspace__bash`. Translate Windows paths to their bash equivalents:
- `F:\Snail\...` → `/sessions/.../mnt/Snail/...`
- `F:\Snail\fts-dev\Unreal Engine\...` → `/sessions/.../mnt/Unreal Engine/...`

The exact session mount prefix is visible in the bash tool description. Use it consistently.
Save processed outputs in-place by default (same directory as the source, new extension if
format changes) unless the user specifies otherwise.
