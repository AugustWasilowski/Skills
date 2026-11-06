# UE Texture Compression Reference

## Identifying Texture Type by Filename Suffix

| Suffix / Pattern               | Type                        |
|--------------------------------|-----------------------------|
| `_H`, `_Height`, `_Disp`       | Height / Displacement       |
| `_N`, `_Normal`, `_NM`         | Normal Map                  |
| `_D`, `_Diffuse`, `_Albedo`, `_C`, `_Color`, `_BaseColor` | Albedo / Base Color |
| `_ORM`, `_ARM`, `_MRAO`, `_MRA`| Packed ORM (Occ/Rough/Metal)|
| `_R`, `_Roughness`             | Roughness (standalone)      |
| `_M`, `_Metallic`, `_Metal`    | Metallic (standalone)       |
| `_AO`, `_Occlusion`            | Ambient Occlusion           |
| `_E`, `_Emissive`, `_EM`       | Emissive                    |
| `_Mask`, `_Alpha`              | Mask / Utility              |
| `_Flow`, `_FlowMap`            | Flow Map                    |
| `_Noise`                       | Noise                       |
| `_SubUV`, `_Atlas`             | SubUV Flipbook              |
| Path contains `/UI/` or `/HUD/`| UI Texture                  |
| Prefix `RT_` or `RenderTarget` | Render Target               |

When the suffix is ambiguous or absent, look at the channel data:
- Grayscale (R=G=B) + LDR → likely a mask, AO, roughness, or height blend
- 2-channel meaningful data → likely a normal map (packed XY) or flow
- 3-channel color with sRGB values → likely albedo
- Flat alpha everywhere → no transparency needed

---

## Compression Settings by Texture Type

### Height / Displacement (`_H`)
- **UE Compression Setting:** `Grayscale (BC4)`
- **sRGB:** Off
- **Texture Group:** World or TerrainHeightmap
- **Source format:** 8-bit grayscale PNG (if values are 0–1 LDR)
- **Notes:** BC4 is single-channel — most efficient format for any grayscale data. If values
  exceed 1.0 and the texture drives actual mesh displacement, keep as R16F or export as
  16-bit PNG and set compression to `HDR (RGBA16F)`.

### Normal Map (`_N`)
- **UE Compression Setting:** `Normalmap (BC5)` (set via TC_NormalMap in Texture Editor)
- **sRGB:** Off
- **Texture Group:** WorldNormalMap
- **Source format:** 8-bit or 16-bit PNG (RGB or RG only — UE only reads RG)
- **Notes:** UE's TC_NormalMap setting stores only RG channels internally (BC5), reconstructing
  Z at runtime. Do NOT set sRGB on normal maps. If the source has a Z channel, it's wasted
  but harmless.

### Albedo / Base Color (`_D`, `_C`, `_Albedo`)
- **UE Compression Setting:** `Default (BC7 / DXT5)` or `BC7 (RGBA)` if alpha present
- **sRGB:** On (this is colour data perceived by the eye)
- **Texture Group:** World
- **Source format:** 8-bit PNG (RGB or RGBA)
- **Notes:** Use `DXT1 / BC1` if there is no alpha and memory is critical (2x smaller than
  BC7 but lower quality). BC7 is strongly preferred for quality. If the texture has a
  meaningful alpha mask, set `TC_BC7` to preserve it.

### Packed ORM (`_ORM`, `_ARM`, `_MRAO`)
- **UE Compression Setting:** `Masks (BC7)` — also called `TC_Masks`
- **sRGB:** Off (each channel is data, not colour)
- **Texture Group:** World
- **Source format:** 8-bit PNG (RGB or RGBA)
- **Notes:** UE's `TC_Masks` uses BC7 without sRGB conversion. Confirm channel packing order
  with the artist — common conventions: R=AO, G=Roughness, B=Metallic (ORM) or
  R=Metallic, G=Roughness, B=AO (MRA). Wrong channel order is a silent bug.

### Roughness Standalone (`_R`)
- **UE Compression Setting:** `Grayscale (BC4)`
- **sRGB:** Off
- **Source format:** 8-bit grayscale PNG

### Metallic Standalone (`_M`)
- **UE Compression Setting:** `Grayscale (BC4)`
- **sRGB:** Off
- **Source format:** 8-bit grayscale PNG

### Ambient Occlusion (`_AO`)
- **UE Compression Setting:** `Grayscale (BC4)`
- **sRGB:** Off
- **Source format:** 8-bit grayscale PNG

### Emissive (`_E`, `_EM`)
- **UE Compression Setting (LDR values 0–1):** `Default (BC7)`, sRGB Off
- **UE Compression Setting (HDR values > 1):** `HDR (BC6H)`, sRGB Off
- **Source format (LDR):** 8-bit PNG; **Source format (HDR):** EXR or 16-bit PNG
- **Notes:** Whether to use BC6H depends entirely on whether the emissive values exceed 1.0.
  Always check with analyze_texture.py first.

### Mask / Utility (`_Mask`, `_Alpha`)
- **UE Compression Setting:** `Grayscale (BC4)` for single-channel; `Masks (BC7)` for packed
- **sRGB:** Off
- **Source format:** 8-bit grayscale PNG

### Flow Map (`_Flow`)
- **UE Compression Setting:** `Masks (BC7)` or `Normalmap (BC5)` (BC5 is more precise for RG)
- **sRGB:** Off
- **Source format:** 8-bit or 16-bit PNG (RG channels)
- **Notes:** Flow maps store directional vectors in RG. BC5 treats them like a 2-channel
  normal map, which is efficient and accurate. BC7 is also acceptable.

### Noise (`_Noise`)
- **UE Compression Setting:** `Grayscale (BC4)` if single-channel; `Default (BC7)` if RGB
- **sRGB:** Off
- **Notes:** Noise textures are often used as masks or tileable data. BC4 is ideal if
  grayscale. Avoid sRGB — noise values are used mathematically, not displayed as colour.

### SubUV Flipbook (`_SubUV`, `_Atlas`)
- **UE Compression Setting:** `Default (BC7)` for colour; `Grayscale (BC4)` if greyscale
- **sRGB:** On if colour, Off if data/mask
- **Notes:** Flipbooks typically have many small frames packed into a grid. Ensure dimensions
  are power-of-two. Large SubUV textures (2048+) can be significant memory consumers.

### UI Texture (path contains `/UI/` or `/HUD/`)
- **UE Compression Setting:** `UserInterface2D (BC7)` — set via Texture Group UI
- **sRGB:** On
- **Texture Group:** UI
- **Notes:** UI textures should NOT stream (set `Never Stream`). They should be power-of-two
  or close to it. Very large UI textures (>1024) are a common memory waste — most UI
  elements can be 512 or smaller.

### Render Target (prefix `RT_`)
- **UE Compression Setting:** Leave as-is (FloatRGBA, BGRA8, etc.)
- **sRGB:** Depends on use
- **Notes:** Render targets are generated at runtime and managed by UE. You generally do not
  process or re-import them. If one appears in a memory audit as a large resident, the fix
  is to reduce its resolution or release it when not in use — not to recompress the asset.

---

## sRGB Decision Quick-Reference

| Turn sRGB **On** if...                  | Turn sRGB **Off** if...                    |
|-----------------------------------------|--------------------------------------------|
| Texture is viewed as colour by the eye  | Texture channels are data / math values    |
| Albedo, base colour, UI graphics        | Normal maps, ORM, masks, height, roughness |
| Colour emissive overlays                | Noise, flow, AO, metallic, displacement    |

When in doubt: if a value of 0.5 in the texture should mean "half" (not "gamma-corrected half"), turn sRGB off.

---

## Memory Footprint Reference (per pixel, GPU-side)

| Format   | Bits/pixel | Notes                                 |
|----------|-----------|---------------------------------------|
| BC1/DXT1 | 4         | RGB only, low quality                 |
| BC4      | 4         | Single channel, excellent for grey    |
| BC5      | 8         | Two channels (RG), ideal for normals  |
| BC6H     | 8         | HDR RGB, float precision              |
| BC7      | 8         | High quality RGBA (or RGB), LDR only  |
| DXT5     | 8         | Older RGBA, superseded by BC7         |
| BGRA8    | 32        | Uncompressed, 4 channels              |
| FloatRGBA| 64        | Uncompressed, full float — very large |

At 2048×2048: BC4 = ~512 KB, BC7 = ~1 MB, FloatRGBA = ~32 MB.

---

## Power-of-Two Requirement

UE requires power-of-two dimensions for:
- Textures with mipmaps (most world textures)
- Streaming textures
- Compressed textures (BC formats)

NPOT textures will not mip correctly and may cause streaming issues. When a texture is
NPOT, recommend the nearest POT that fits the content (usually rounding up to the next
power-of-two is safer than rounding down, unless the content is close to the lower value).

---

## Quick Wins Checklist

When reviewing a texture, check for these common issues in order:

1. **Uncompressed format (FloatRGBA, BGRA8)** on a texture that doesn't need it → biggest wins
2. **HDR format on LDR data** → switch to BC7 or BC4
3. **RGBA on grayscale data** (R=G=B) → switch to single-channel BC4
4. **4096+ source when in-game max is 2048** → resize the source file
5. **Non-power-of-two dimensions** → resize to nearest POT
6. **NeverStream off on large textures** → consider enabling streaming
7. **UI textures larger than 512** → scale down if visually acceptable
