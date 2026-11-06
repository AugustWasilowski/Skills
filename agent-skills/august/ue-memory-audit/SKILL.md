---
name: ue-memory-audit
description: >
  Generates a comprehensive Unreal Engine memory audit by querying a NotebookLM 
  notebook that contains a UE MemReport. Covers texture offenders (uncompressed, NeverStream, 
  oversized), ray tracing memory, geometry/RTAS, virtual texture pools, plugin memory, and 
  shaders. Produces two outputs: (1) a colour-coded PDF with executive summary, prioritised 
  findings tables, and a P0–P3 action plan; (2) a texture_todo CSV listing every problematic 
  texture parsed directly from the raw .memreport files, deduplicated across maps, ready to 
  open in a spreadsheet as a tech art to-do list. Saves both locally and optionally to Google Drive.

  Use this skill whenever the user mentions: "memreport", "memory audit", "texture audit", 
  "NeverStream", "memory report", "UE memory", "analyse our build memory", "generate an audit", 
  "run the audit", or any request to produce a report from a NotebookLM notebook containing 
  Unreal Engine memory data. Also trigger when comparing memory across builds or following up 
  on a previous audit.
---

# UE Memory Audit Skill

This skill automates the end-to-end workflow of turning a raw UE MemReport (uploaded to 
NotebookLM) into a polished, actionable Word document audit report.

## Prerequisites

- A NotebookLM notebook with a UE `.memreport` or `listtextures` dump already uploaded as a source
- Python 3 with `reportlab` installed:
  - Windows / macOS: `pip install reportlab`
  - Linux (Ubuntu 22+ / Debian): `pip install reportlab --break-system-packages`
- Optionally: Google Drive MCP for saving to Drive

## Step 1 — Identify Notebook and Project

Check memory for a saved NotebookLM notebook ID for UE memory audits. If none is found, ask:
> "Which NotebookLM notebook contains the MemReport? Give me the notebook ID or title."

Also confirm:
- **Project name** (e.g. "SolarScene")  
- **Build type** (e.g. "WindowsClient", "WindowsServer")
- **Report date** (default: today)

Save the notebook ID to memory for future sessions.

## Step 2 — Run Parallel NotebookLM Queries

NotebookLM queries are **async**. Use the pattern:  
`notebook_query_start` → poll `notebook_query_status` (every ~5s) until `status == "complete"` → read `result.answer`.

**Start all 6 queries before polling any.** This keeps total wall-clock time near one round-trip.

If a query result is very large (>5000 chars), parse only the first 5000 characters using:
```bash
echo '<json>' | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result']['answer'][:5000])"
```

### Query 1 — Critical Textures (Uncompressed)
> "List the top 20 textures by memory size that are uncompressed — meaning their pixel format is 
> PF_B8G8R8A8 or PF_FloatRGBA. For each texture include: name, size in MB, pixel format, texture 
> group (LODGroup), dimensions (width×height), NeverStream/Streaming status, asset path. Sort by 
> size descending."

### Query 2 — NeverStream Compressed Textures
> "List the top 20 textures where NeverStream is true (or Streaming: NO) AND the format is a 
> block-compressed format (DXT1, DXT5, BC5, BC7, PF_DXT1, PF_DXT5, etc. — not PF_B8G8R8A8). 
> Sort by size descending. For each: name, size MB, format, texture group, dimensions, usage count."

### Query 3 — UI Textures
> "List all textures that are in TEXTUREGROUP_UI, or have 'UI', 'Icon', 'HUD', or 'Interface' 
> in their name or asset path. For each: name, size MB, pixel format, NeverStream/Streaming status, 
> dimensions, asset path."

### Query 4 — Memory Totals
> "What are the top-level memory totals in this report? Give exact values for: process physical 
> memory (peak and current), total RHI resource memory, texture streaming pool, static mesh 
> total memory, skeletal mesh total memory, ray tracing BLAS/RTAS total. List them all."

### Query 5 — Ray Tracing Acceleration Structures
> "List the top 15 ray tracing acceleration structure entries (BLAS or RTAS) sorted by size in MB. 
> Also list any hair strand ray tracing buffers (StrandsRaytracing, HairStrands, or similar). 
> For each entry include: asset/buffer name, size in MB."

### Query 6 — Additional Memory Consumers
> "Summarise all significant non-texture memory consumers above ~20 MB. Include: each virtual 
> texture physical pool with its format and size, plugin memory subsystems (FTS Voxel, etc.), 
> shader preload size, DLSS or other upscaling buffers, skeletal mesh counts or sizes, render 
> target pools, and anything else notable. Report sizes in MB."

## Step 3 — Parse Results into report_data.json

After all queries complete, extract the information from the natural language answers and write 
a structured `report_data.json` file. See `references/report_schema.md` for the full schema.

**Key UE interpretation rules** (also detailed in `references/ue_knowledge.md`):

| Situation | What it means |
|---|---|
| PF_B8G8R8A8 + NeverStream | Worst case — 4–8× larger than it needs to be AND always resident |
| PF_FloatRGBA + NeverStream | Also critical — 16-bit float has no business being on most colour textures |
| TEXTUREGROUP_UI | Always resident by design; only fixes are compression + resolution |
| TEXTUREGROUP_IESLightProfile | For IES light profiles only — anything else here is likely miscategorised |
| UsageCount: 0 + NeverStream | Resident but unused this session — candidate for removal |
| BC-compressed + NeverStream | Still wasteful if streaming is possible; check if streaming is intentionally disabled |

**Priority assignment:**
- **P0** — Uncompressed + NeverStream, or any single buffer >100 MB (hair RT, etc.)
- **P1** — NeverStream compressed >20 MB, or uncompressed textures that *do* stream, or RTAS without Nanite
- **P2** — NeverStream audit candidates, bone influence reduction, plugin deallocation opportunities
- **P3** — Cosmetic improvements (downsample sky textures, PSO cache, shader pruning)

## Step 4 — Install Dependencies and Generate Report

```bash
pip install reportlab   # only needed first run (Linux: add --break-system-packages)
python3 /path/to/ue-memory-audit/scripts/generate_report.py \
  /path/to/report_data.json \
  /path/to/output/ProjectName_Memory_Audit_YYYY-MM-DD.pdf
```

The script reads `report_data.json` and produces a fully formatted PDF. It handles missing/empty 
sections gracefully — just omit fields you have no data for.

## Step 5 — Generate Texture To-Do CSV

After the PDF is produced, run `texture_todo.py` directly against the raw `.memreport` files.
This script requires **no tokens** — it parses the files locally and deterministically.

```bash
python "~/.claude/skills/ue-memory-audit/scripts/texture_todo.py" "<memreport_dir>" -o "<output_dir>/texture_todo_YYYY-MM-DD.csv"
```

- `<memreport_dir>` — the folder containing the `.memreport` files (e.g. `G:/My Drive/FTS`)
- `<output_dir>` — same folder as the PDF output
- Replace `YYYY-MM-DD` with today's date

**What it produces:** One row per unique problematic texture, deduplicated across maps, with columns:
`priority`, `map_count`, `appears_in`, `asset_name`, `ue_path`, `size_mb`, `cooked_dim`,
`format`, `texture_group`, `streaming`, `vt`, `num_mips`, `is_uncompressed`, `issues`, `suggested_action`

**Default threshold:** textures >= 1 MB. Pass `--min-mb 4` to reduce noise if needed.

## Step 6 — Save the Outputs

`G:\My Drive` is a locally mounted, actively synced Google Drive folder on this machine.
**Do not use the Google Drive MCP to upload files.** Instead, write directly to the local path — the sync client handles the rest automatically.

Save both outputs to `G:\My Drive\FTS\`:

```bash
copy "<output_dir>\{Project}_Memory_Audit_YYYY-MM-DD.pdf" "G:\My Drive\FTS\"
copy "<output_dir>\texture_todo_YYYY-MM-DD.csv" "G:\My Drive\FTS\"
```

Or target `G:\My Drive\FTS\` as the output directory from the start so no copy is needed:

```bash
# PDF (Step 4)
python "...scripts/generate_report.py" report_data.json "G:\My Drive\FTS\{Project}_Memory_Audit_YYYY-MM-DD.pdf"

# CSV (Step 5)
python "...scripts/texture_todo.py" "G:\My Drive\FTS" -o "G:\My Drive\FTS\texture_todo_YYYY-MM-DD.csv"
```

Both files will appear in Google Drive automatically once the sync client picks them up.

## Handling Follow-up Audits

When the user uploads a new MemReport to the same NotebookLM notebook, re-run all 6 queries 
fresh (NotebookLM sees all sources). The new report will reflect the latest build. Name both 
output files with the current date so old reports are preserved for comparison.

The texture_todo CSV (Step 5) always re-parses the raw `.memreport` files from scratch — no 
NotebookLM queries needed for that step. Run it independently anytime with:
```bash
python "~/.claude/skills/ue-memory-audit/scripts/texture_todo.py" "<memreport_dir>" -o "<output>.csv"
```

If the user wants a diff/comparison between builds, query NotebookLM with:
> "Compare the texture memory usage across the different MemRepor