# report_data.json Schema

This file defines the JSON structure that `generate_report.js` expects as input.
All fields are optional — the script handles missing sections gracefully by omitting them.

```json
{
  "meta": {
    "project":   "SolarScene",
    "build":     "WindowsClient",
    "date":      "April 21, 2026",
    "source":    "SolarScene-WindowsClient-21-09.28.44 MemReport"
  },

  "summary_stats": [
    { "label": "Total NeverStream Budget", "value": "567 MB",  "sub": "Non-streaming resident textures", "fill": "CC0000", "bg": "FFF0F0" },
    { "label": "UI Texture Group",         "value": "273 MB",  "sub": "Entirely non-streaming",          "fill": "CC5500", "bg": "FFF8F0" },
    { "label": "Uncompressed Textures",    "value": "741 MB",  "sub": "PF_B8G8R8A8 + FloatRGBA total",  "fill": "886600", "bg": "FFFBF0" },
    { "label": "Total Unstreamable",       "value": "949 MB",  "sub": "All non-streaming render assets", "fill": "555555", "bg": "F5F5F5" }
  ],

  "summary_body": "The single biggest opportunity is the UI texture group (273 MB), which is entirely resident and almost entirely uncompressed PF_B8G8R8A8.",

  "critical_textures": [
    {
      "name":   "T_Caustics",
      "mb":     "64.00",
      "dim":    "4096×4096",
      "fmt":    "PF_B8G8R8A8",
      "stream": "NO",
      "path":   "/Game/OceanWater/Design/Ocean/Textures/"
    }
  ],
  "critical_summary": "Combined resident memory for the top uncompressed + NeverStream offenders: ~327 MB.",

  "neverstream_textures": [
    {
      "name":  "T_head_wm_msk_Array",
      "mb":    "40.00",
      "dim":   "2048×2048",
      "fmt":   "PF_DXT5",
      "group": "Character",
      "note":  "MetaHuman anim mask array — 0 usage count"
    }
  ],
  "neverstream_bullets": [
    "T_head_wm_msk_Array (40 MB) — 0 usage count. If not actively used this session, this is dead weight resident memory.",
    "Real_Stars_Dimmed — 8192×8192 star texture. Even though DXT1-compressed, an 8K sky texture is oversized."
  ],

  "ui_textures": [
    {
      "name":   "T_GenesisPodRadial",
      "mb":     "31.88",
      "dim":    "3839×2160",
      "action": "Scale to 1024×1024; use BC7 compression"
    }
  ],
  "ui_note": "T_Icon_Clock and T_Icon_PowerPole are marked as 'Temp' assets — verify against current UI specs.",

  "recommendations": [
    {
      "title":   "Priority 1 — Immediate Wins (Uncompressed World/VFX Textures)",
      "bullets": [
        "T_Caustics (64 MB, IESLightProfile group): Re-export as BC7. TEXTUREGROUP_IESLightProfile is wrong for a caustic texture.",
        "T_SuffocateTex_3840x2160 & T_01_02 (31.88 MB each): Re-export at 1024×1024 with DXT5. Enable streaming."
      ]
    },
    {
      "title":   "Priority 2 — UI Audit and Compression Pass",
      "bullets": [
        "Run a batch compression pass on all TEXTUREGROUP_UI assets. BC7 is visually lossless at 4:1 savings."
      ]
    }
  ],

  "geometry_stats": [
    { "label": "Process Physical Memory", "value": "11.3 GB",  "sub": "Peak: 11.5 GB",           "fill": "CC0000", "bg": "FFF0F0" },
    { "label": "Total RHI Resources",     "value": "18.97 GB", "sub": "8.1 GB non-transient",    "fill": "CC5500", "bg": "FFF8F0" },
    { "label": "Static Mesh Memory",      "value": "1,714 MB", "sub": "Vertex + Index + Nanite", "fill": "886600", "bg": "FFFBF0" },
    { "label": "Ray Tracing RTAS",        "value": "563 MB",   "sub": "Static BLAS: 448 MB",     "fill": "1F3864", "bg": "F5F5F5" }
  ],

  "hair_rt_intro": "Hair_S_UpdoBuns has a StrandsRaytracing_PositionBuffer consuming 182 MB — the single largest non-engine buffer in the entire report.",
  "hair_rt": [
    {
      "name":           "Hair_S_UpdoBuns\n(StrandsRaytracing_PositionBuffer)",
      "size":           "182 MB",
      "recommendation": "Disable ray tracing on this groom asset. Open Groom asset → Details → uncheck 'Use Hair Strands Raytracing'. Alternatively use r.HairStrands.Raytracing 0 as a scalability setting."
    }
  ],

  "rtas_intro": "Total RTAS budget is 563 MB (Static BLAS: 448 MB, Dynamic BLAS: 51 MB). The primary driver is high-density static meshes at LOD0 without Nanite.",
  "rtas_offenders": [
    { "name": "SM_HS_TopStructure_01",           "mesh_mb": "–",    "rtas_mb": "41.6", "note": "Hermes Station outer ring — enable Nanite to eliminate RTAS cost." },
    { "name": "SM_LB_RockStone_01",              "mesh_mb": "66.8", "rtas_mb": "26.2", "note": "3 instances = 200 MB mesh + 78 MB RTAS. Enable Nanite or add LODs." }
  ],
  "rtas_note": "Enabling Nanite on a static mesh removes it from the per-mesh RTAS system. This is the most effective single action for reducing both mesh memory and RTAS overhead.",

  "additional_sections": [
    {
      "title": "Voxel Plugin — ~237 MB Total",
      "intro": "The FTS Voxel plugin allocates significant memory. If voxel volumes are only active in specific level contexts, runtime deallocation when not in use would recover this budget.",
      "table": [
        { "name": "AttributeIndices Texture (Transient)", "size": "64 MB",   "note": "4096×4096 PF_R32_SINT transient texture. Expected for voxel index storage." },
        { "name": "Voxel Mesh Memory",                   "size": "73.4 MB", "note": "Runtime mesh data for visible voxel surfaces." }
      ]
    },
    {
      "title": "Shader Preload — 359 MB",
      "body":  "The shader preload budget is 359 MB. Run a PSO cache warm-up pass before shipping and audit material complexity for unused feature flags."
    },
    {
      "title": "DLSS Internal GPU Memory — 89.7 MB",
      "body":  "DLSS is allocating 89.7 MB of internal GPU memory. Expected behaviour — not directly actionable, but ensure DLSS is gated behind appropriate hardware detection."
    }
  ],

  "priority_table": [
    { "issue": "Hair ray tracing (UpdoBuns)",    "savings": "182 MB",  "effort": "Low",    "priority": "P0", "action": "Uncheck ray tracing on groom asset" },
    { "issue": "T_Caustics — uncompressed 4K",   "savings": "~56 MB",  "effort": "Low",    "priority": "P0", "action": "Re-export as BC7, fix texture group" },
    { "issue": "Lobby Rocks × 3 (mesh + RTAS)",  "savings": "~278 MB", "effort": "Medium", "priority": "P1", "action": "Enable Nanite or add LODs" }
  ],

  "vt_pools": [
    { "pool": "VirtualTexture_Physical (BC7)",      "size": "64.00 MB", "format": "BC7 — OK" },
    { "pool": "VirtualTexture_Physical (B8G8R8A8)", "size": "60.06 MB", "format": "⚠ Uncompressed — investigate source textures" }
  ],
  "vt_note": "The presence of a B8G8R8A8 VT physical pool (60 MB) is worth noting — uncompressed VT content has the same density cost inside the VT system as outside."
}
```

## Notes

- `summary_stats` and `geometry_stats`: each entry is a "stat box". Use `fill` for the accent 
  colour (top border + value text) and `bg` for the box background.
- `critical_textures[].stream`: use `"NO"` or `"YES"` — controls red/green cell colouring.
- `additional_sections[].table`: optional. If present, renders a 3-column table (Name, Size, Notes). 
  If absent, renders only `body` as a paragraph.
- `priority_table[].priority`: must be one of `"P0"`, `"P1"`, `"P2"`, `"P3"` — controls row colour.
- All fields are optional. Sections with no data are simply omitted from the document.
