# Unreal Engine Memory Audit — Reference Knowledge

## Pixel Formats and What They Cost

| Format | Bits/pixel | Compression | Use case |
|---|---|---|---|
| PF_B8G8R8A8 | 32 | None (uncompressed) | Should almost never be used at runtime |
| PF_FloatRGBA | 64 | None (uncompressed) | HDR data only — very expensive |
| PF_BC7 / RGBA | 8 | 4:1 over RGBA8 | Best quality for colour+alpha |
| PF_DXT5 / BC3 | 8 | 4:1 | Colour+alpha, weaker than BC7 |
| PF_DXT1 / BC1 | 4 | 8:1 | Opaque colour only |
| PF_BC5 | 8 | 4:1 | Normal maps (RG channels) |
| PF_BC6H | 8 | 4:1 | HDR colour (replaces FloatRGBA) |
| PF_G8 | 8 | N/A | Single-channel greyscale |
| PF_R32_SINT | 32 | N/A | Integer data (voxel indices, etc.) |

**Rule of thumb:** A 2048×2048 PF_B8G8R8A8 texture = 16 MB. The same texture as BC7 = 4 MB.

## Texture Streaming vs NeverStream

- **Streaming**: UE loads/unloads mip levels based on camera distance. GPU only holds the mips 
  it needs. This is the default and preferred behaviour for world textures.
- **NeverStream**: The full texture (all mips) stays resident in GPU memory at all times, 
  regardless of visibility. Correct for: UI, IES profiles, render targets, lookup tables.
  Wrong for: world geometry, VFX, sky textures, characters at a distance.
- **Virtual Textures (VT)**: Tile-based streaming — only the tiles visible on screen are loaded. 
  Best for large world textures. Requires VT physical pool allocation (~60-64 MB per format pool).

## UE Texture Groups (LOD Groups)

| Group | Default streaming | Intended use |
|---|---|---|
| TEXTUREGROUP_World | Streaming | General world geometry |
| TEXTUREGROUP_WorldNormalMap | Streaming | World normal maps |
| TEXTUREGROUP_Character | Streaming | Character albedo/normals |
| TEXTUREGROUP_UI | NeverStream | UI and HUD textures |
| TEXTUREGROUP_IESLightProfile | NeverStream | IES light profile textures ONLY |
| TEXTUREGROUP_Skybox | Streaming (or NeverStream depending on project config) | Sky textures |
| TEXTUREGROUP_Effects | Streaming | VFX particle textures |
| TEXTUREGROUP_RenderTarget | NeverStream | Render targets (expected) |

**Common misassignment:** World/VFX textures accidentally placed in TEXTUREGROUP_IESLightProfile 
inherit its NeverStream behaviour. Always verify any non-IES content in this group.

## Compression Settings in UE5 Texture Editor

The dropdown names in the UE Texture Editor map to formats as follows:

| UE Dropdown Name | Runtime Format | Notes |
|---|---|---|
| Default (DXT1/DXT5) | BC1 or BC3 | Auto-selects based on alpha |
| BC7 (RGBA) | BC7 | Best quality for RGBA; use for UI with alpha |
| DXT5 (RGBA) | BC3 | Older RGBA; fine for VFX masks |
| BC5 (RG) | BC5 | Use for normal maps |
| BC6H (HDR) | BC6H | Use for HDR colour (replaces FloatRGBA) |
| Grayscale (G8/G16) | PF_G8 or PF_G16 | Single channel |
| UserInterface2D (RGBA) | PF_B8G8R8A8 | Uncompressed — avoid for large textures |
| HDR (FloatRGBA) | PF_FloatRGBA | Uncompressed HDR — usually replaceable with BC6H |
| Editor Icon | PF_B8G8R8A8 | Editor-only setting — DO NOT use for game textures |

**Key insight:** "UserInterface2D" sounds like the right setting for UI textures, but it is 
UNCOMPRESSED. Use BC7 (RGBA) instead for UI textures with alpha — it is visually lossless 
at 4:1 compression.

## Ray Tracing Memory

- **BLAS (Bottom-Level Acceleration Structure)**: One per static/skeletal mesh instance. 
  Size is proportional to triangle count. High-polygon meshes without Nanite each carry 
  a separate BLAS.
- **TLAS (Top-Level Acceleration Structure)**: One per scene. Small.
- **Hair Strand BLAS**: Per-strand ray tracing is extremely expensive. Each groom asset with 
  ray tracing enabled gets a StrandsRaytracing_PositionBuffer that can easily be 100–200 MB.
- **Nanite interaction**: Enabling Nanite on a static mesh removes it from the per-mesh RTAS 
  system. Nanite geometry uses a shared, optimised ray tracing path. This is the most effective 
  single action for reducing RTAS overhead.

## Common Issues and Fixes

### Uncompressed textures
- **Cause:** Texture exported with "UserInterface2D", "HDR", or "Editor Icon" compression setting
- **Fix:** Change to BC7 (RGBA) for colour+alpha, BC6H for HDR, BC4 for single-channel
- **Impact:** ~4–8× memory reduction

### Large NeverStream textures
- **Cause:** Texture group defaults to NeverStream, or NeverStream checkbox explicitly set
- **Fix:** Uncheck NeverStream in texture settings, or move to a streaming-enabled group
- **Caveat:** Some textures legitimately need to be NeverStream (UI, LUTs, IES profiles)

### Non-power-of-2 dimensions
- **Impact:** Cannot generate a full mip chain; may not stream correctly; wastes atlas space
- **Fix:** Rescale source art to nearest power of 2 (or use power-of-2 for at least one axis)
- **UE behaviour:** UE will still load non-PoT textures but warns about them

### Hair strand ray tracing
- **Cause:** Groom asset has "Use Hair Strands Raytracing" enabled
- **Fix:** Uncheck it in the Groom asset Details panel, or use `r.HairStrands.Raytracing 0` 
  as a scalability setting for lower quality tiers

### High bone influence count on skeletal meshes
- **UE default:** 8 bone influences per vertex (saves to GPU skinning buffer)
- **Recommended:** 4 bone influences for non-hero characters
- **How to check:** Asset details → LOD Settings → Max Bone Influences
- **Savings:** ~30–50% reduction in skinning buffer size

## Virtual Texture Pools

VT pools are allocated per format. Each pool is typically 60–64 MB. The presence of a 
B8G8R8A8 or FloatRGBA pool means some VT-assigned textures are using uncompressed source 
formats — the same compression recommendations apply inside VT pools as outside.

## Shader Memory

- Shader preload budget: typically 200–400 MB for a complex game
- High shader preload = many material permutations or incomplete PSO cache
- PSO (Pipeline State Object) cache warm-up: running the game through all common scenarios 
  before shipping so shaders are pre-compiled and cached
- Audit material feature flags: materials with Cloth, Eye, or Hair shading models enabled 
  where they aren't needed double the shader permutation count
