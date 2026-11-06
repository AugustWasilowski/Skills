# FTS Texture Audit Pipeline — Overview

The pipeline lives at `F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\` and is three stages.

## File locations

```
F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\
├── fts_stage1_inventory.py        # UE Python; read-only inventory
├── fts_stage2_classify.py         # plain Python; offline classifier
├── fts_stage3_apply.py            # UE Python; applies changes per CSV
├── probe_project_groups.py        # diagnostic; rarely needed
├── stage1_inventory.csv           # Stage 1 output, full Hermes
├── stage2_proposed_APPROVED.csv   # the work list — Stage 3 reads this
├── stage2_full_review.csv         # rows the classifier wouldn't auto-touch
└── session_log.md                 # cross-session log; append per folder
```

When the workspace is mounted in bash, the path becomes `/sessions/<id>/mnt/AssetAudit/`. File tools (Read/Write/Edit) use the Windows path; bash uses the mount path.

## Stage 1 — Inventory (read-only, UE Python)

`fts_stage1_inventory.py` runs in the Unreal Editor's Python console. It walks every Texture2D under the configured root (`/Game/Hermes`), pulls per-texture metadata (group, compression, sRGB, virtual_texture, dimensions, source disk size, runtime memory footprint, `bytes_per_pixel`, derived `compression_class`), and writes `stage1_inventory.csv`.

It's read-only and re-runnable at any time. **Re-run when significant new content has been added to the project** — otherwise the existing inventory is fine.

## Stage 2 — Classify (offline, plain Python)

`fts_stage2_classify.py` is the offline classifier. It reads `stage1_inventory.csv` and writes two CSVs:

- `stage2_proposed_APPROVED.csv` — every row, with proposed action + confidence + rationale
- `stage2_full_review.csv` — subset routed to manual review (low confidence, sensitive data textures, /Demos rows, etc.)

The classifier uses path heuristics, suffix detection, role inference, and a project-specific group ledger to decide what each texture should look like.

### Key Stage 2 logic the user should understand

- **`MASK_LIKE_ROLES`** = `{mask, metallic, orm, rma, specular, roughness, ao}` — these all map to `TC_Masks`, not `TC_BC7`. Stage 1's `_M`-as-`metallic` labeling falls into this bucket.
- **`_M` suffix override** — explicit override at the top of `classify()` that sets `role=mask` for any `_M` texture, regardless of what Stage 1 said. Per project convention, `_M` is always a packed mask (MM_DefaultPlant_Subsurface, MM_ComplexFabric_Subsurface, etc.).
- **`KNOWN_GOOD_COMPRESSION` guard** — if `compression_settings` is already in `{TC_Masks, TC_Normalmap, TC_Grayscale, TC_BC7, TC_HdrCompressed, TC_HalfFloat, TC_DistanceFieldFont}`, Stage 2 won't propose recompressing — even if `compression_class == "uncompressed"` (which fires falsely for Virtual Textures and atlases due to bpp anomalies).
- **Pivot Painter / data-texture guard** — names matching `PivotPoint`, `_PP\d`, `_PI$`, `_XVE`, `_HDR$`, `_SSS$`, `_RVT_` are routed to review and never auto-modified.
- **Foliage proposals route to `TEXTUREGROUP_Foliage`**, which Stage 3's ledger maps to `TEXTUREGROUP_Project09`. `TEXTUREGROUP_Foliage` doesn't exist as a stock UE 5.6 group — the project allocates Project09 for it in DefaultEngine.ini.

### When and how to re-run Stage 2

Re-run Stage 2 if the user has edited classification logic — added a path hint, fixed a role mapping, tightened a compression rule, etc. Re-running regenerates `stage2_proposed_APPROVED.csv` from the (unchanged) inventory, and the new CSV reflects the new logic.

Cookbook:

1. **Back up the current CSVs** so the user can diff and roll back if needed:
   ```bash
   cd /sessions/<id>/mnt/AssetAudit
   cp stage2_proposed_APPROVED.csv stage2_proposed_APPROVED.csv.pre-<short-tag>.bak
   cp stage2_full_review.csv stage2_full_review.csv.pre-<short-tag>.bak
   ```

2. **Re-run the classifier**:
   ```bash
   python3 fts_stage2_classify.py \
     --in stage1_inventory.csv \
     --out stage2_proposed_APPROVED.csv \
     --review-out stage2_full_review.csv
   ```

3. **Diff for the target folder(s)**. Show the user what proposals changed before re-running Stage 3. A useful Python pattern:

   ```python
   # For each folder of interest, compare OLD vs NEW for fields that matter:
   #   proposed_action, proposed_group, proposed_compression, proposed_srgb,
   #   proposed_max_size, confidence
   # Group changes by transition pattern (e.g., 100 rows: TC_BC7 -> TC_Masks)
   ```

   Surface the top transition patterns and their counts. The user wants to see "X rows now propose TC_Masks instead of TC_BC7" before they re-run Stage 3 against already-touched folders.

4. **Flag impact on already-submitted folders.** If the user has previously processed Drones / Fungus / Desert (etc.), the new CSV will propose changes to rows in those folders. Tell the user which folders have new proposals and how many — they can decide whether to re-run those folders as catch-up.

5. **Continue with the per-folder loop** using the new CSV.

### What NOT to do for Stage 2

- Don't re-run Stage 2 silently — always inform the user.
- Don't run Stage 1 first unless content has changed — Stage 2 against the existing inventory is what produces a comparable diff.
- Don't modify the classifier output CSV by hand. If a row is wrong, fix the classifier and re-run.

## Stage 3 — Apply (mutating, UE Python, human-gated)

`fts_stage3_apply.py` runs in the Unreal Editor's Python console. It reads `stage2_proposed_APPROVED.csv` and applies changes to the per-texture properties: `lod_group`, `compression_settings`, `srgb`, `never_stream`, `lod_bias`, `max_texture_size`. Saves modified assets. Does NOT submit to Perforce.

### The knobs at the top of `fts_stage3_apply.py`

```python
INPUT_CSV = r"F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\stage2_proposed_APPROVED.csv"

DRY_RUN = True              # flip to False to apply
FOLDER_FILTER = "/Game/Hermes/Art/.../"  # one folder at a time

ACTION_FILTER = {
    "reassign_group", "recompress", "cap_max_size", "flag_only",
    # NOT "reimport_source" — that's Pass-2 work
}

CONFIDENCE_FILTER = {"high"}
OVERRIDE_OUT_OF_HERMES = False
SAVE_ASSETS = True
```

The skill freely edits `DRY_RUN` and `FOLDER_FILTER`. **Never** edits `ACTION_FILTER`, `CONFIDENCE_FILTER`, or `OVERRIDE_OUT_OF_HERMES` without explicit per-instance user approval.

### How Stage 3 counts

Stage 3 reports a row as `changed` if **at least one field differs** from the texture's current state. It reports `skipped` for rows that:

- Don't pass the in-Hermes / in-Demos guard
- Don't match `FOLDER_FILTER`
- Don't have an action in `ACTION_FILTER`
- Don't have confidence in `CONFIDENCE_FILTER`
- Have proposals that all match current state (no field deltas)
- Failed to load (rare; rolls into skipped, not failed)

`failed` only ticks on Python exceptions caught during `apply_one()`. We expect this to always be 0.

This means **the predicted touchable count from pre-flight is an upper bound on `changed`**. Real `changed` will often be lower (a fraction of touchable rows are already at proposed values, especially after re-runs).

### Stage 3's `FRIENDLY_TO_PROJECT_SLOT` ledger

Project-group friendly names map to project slots that exist as real Unreal `TextureGroup` enum values. The current ledger:

```python
FRIENDLY_TO_PROJECT_SLOT = {
    "TEXTUREGROUP_HUDUI":                    "TEXTUREGROUP_Project01",
    "TEXTUREGROUP_IconUI":                   "TEXTUREGROUP_Project02",
    "TEXTUREGROUP_CharacterOutfit":          "TEXTUREGROUP_Project03",
    "TEXTUREGROUP_CharacterOutfitNormalMap": "TEXTUREGROUP_Project04",
    "TEXTUREGROUP_CharacterOutfitSpecular":  "TEXTUREGROUP_Project05",
    "TEXTUREGROUP_Grass":                    "TEXTUREGROUP_Project06",
    "TEXTUREGROUP_HeightMap":                "TEXTUREGROUP_Project07",
    "TEXTUREGROUP_Mask":                     "TEXTUREGROUP_Project08",
    "TEXTUREGROUP_Foliage":                  "TEXTUREGROUP_Project09",
}
```

If the user adds new project groups (Project10+), update this dict and the corresponding `TextureLODGroups` line in `DefaultEngine.ini`. Run `probe_project_groups.py` in UE to verify the slot resolves before relying on it.

### Two-pass strategy

The pipeline runs in two passes:

- **Pass-1** (current): in-engine `max_texture_size` cap. Recovers cooked memory; the source `.uasset` on disk stays the same size. Fast and reversible. Action label `cap_max_size`.
- **Pass-2** (deferred to shipping prep): export-resize-reimport via the `ue-texture-processor` skill. Actually shrinks source data on disk. Action label `reimport_source` — explicitly NOT in `ACTION_FILTER`, so Stage 3 ignores those rows. They wait for Pass-2.

The `rationale` field on a row mentioning "ceiling" usually means the row is a Pass-1 ceiling cap; that's fine to apply now.

## Per-folder workflow at a glance

This is what the SKILL.md orchestrates per folder. Quick reference:

1. Pre-flight (offline): `pre_flight.py` reports counts + danger flags.
2. Edit `apply.py`: `DRY_RUN = True`, `FOLDER_FILTER = "<folder>"`.
3. Dry-run in UE: paste exec line, capture `[FTS] DONE in Xs -- changed N, skipped M, failed F`. Verify F=0.
4. Edit `apply.py`: `DRY_RUN = False`. Re-Read.
5. Live-run in UE: paste exec line again, wait for new DONE line. Verify changed matches dry-run, F=0.
6. P4 changelist (if enabled): create with description `Texture Optimization - Hermes/Art/<folder>`, move modified files in.
7. Append to session log.

That's it. The runbook for each mode (Computer Use vs pair-programmer) describes how steps 3, 5, and 6 actually happen.
