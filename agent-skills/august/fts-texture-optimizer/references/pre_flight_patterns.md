# Pre-Flight Pattern Detection

The pre-flight script (`scripts/pre_flight.py`) checks for known danger patterns before allowing a folder to proceed. Patterns come in two severities:

- **HARD-BLOCK** — script exits non-zero. Skill must stop the folder and surface to the user. Don't proceed without explicit user direction.
- **WARN** — script exits zero. Skill continues but logs the warning to the batch's warnings collector for end-of-run summary.

## Hard-block patterns

### Normal-map compression flip on real normals

**Detection:** rows where `compression_settings == "TC_Normalmap"` AND `proposed_compression` is set AND `proposed_compression != "TC_Normalmap"` AND (`suffix == "_N"` OR `role` contains "normal").

**Why it's dangerous:** these are textures with `_N` suffix or normal-map role that are CURRENTLY in `TC_Normalmap` (the correct format) but Stage 2 is proposing a switch. Almost always wrong — switching a normal map's compression away from `TC_Normalmap` corrupts the normal data and the affected materials look broken. We have not yet seen a legitimate case of this; if Stage 2 produces this, it's a classifier bug.

**What to do:** Stop. Show the user the affected paths and ask whether to fix the classifier or override per-row. Don't proceed until they explicitly say so.

### Significant /Demos contamination

**Detection:** more than 10 rows in the touchable cohort have `/Game/Demos/` in their package path.

**Why it's dangerous:** /Demos is excluded from the audit by policy. Stage 2 routes /Demos rows to `review` action with `low` confidence; they should never be touchable. If they ARE touchable, Stage 2's routing is broken.

**What to do:** Stop. Investigate whether the classifier's `in_demos` check is firing correctly. Also: reconfirm the user's target path doesn't accidentally include Demos rows.

## Warn patterns

These don't block the run, but should be surfaced in the batch's end-of-run warnings report.

### Mix-map mislabel

**Detection:** rows where `current_group == "TEXTUREGROUP_WorldNormalMap"` AND `proposed_group == "TEXTUREGROUP_World"` AND `suffix == "_M"` AND `compression_settings == "TC_Normalmap"`.

**Interpretation:** these are `_M` (mix map / packed mask) textures that were authored into the WorldNormalMap group with TC_Normalmap compression — almost certainly a packing mistake. Stage 2 will move them to World. The user should also update the materials referencing them so the mask channel is read correctly.

**What to do:** continue, but log the count and sample paths in the warnings report. The user investigates the materials separately.

### Light /Demos contamination

**Detection:** ≤10 rows with `/Game/Demos/` in path that are still touchable.

**Interpretation:** likely a Stage 2 routing edge case. Not catastrophic but worth fixing in the classifier eventually.

**What to do:** continue, log in warnings report.

### HDR-uncompressed in non-Pivot Painter context

**Detection:** rows where `compression_class == "hdr_uncompressed"` AND the texture name doesn't match Pivot Painter / data-texture patterns (`PivotPoint`, `_PP\d`, `_PI`, `_XVE`, `_HDR$` end-of-name, etc.).

**Interpretation:** could be intentional (cinematic HDR, lookup tables, vector flow maps) or could be a memory leak (a 4K texture stored as `TC_Default` at 12 bpp). Stage 2 is conservative and routes most of these to review, but the warn is here in case some slip through.

**The Pivot Painter false-positive** is real: foliage Pivot Painter index textures (`*_PivotPoint_Index_HDR`, `*_PI`, `*_PP2_PI`) are intentionally HDR-uncompressed because they encode high-precision per-vertex pivot data. They typically live in `/Trees/`, `/Plants/`, `/SmallPlant/`, `/MediumPlant/`, `/LargePlant/` paths. Stage 2 catches these via `DATA_TEXTURE_NAME_PATTERNS` and routes them to review. If pre-flight surfaces an HDR-uncompressed warning that's actually one of these, it's a Stage 2 miss — the classifier's name pattern probably needs to be tightened, but it's not blocking.

**What to do:** continue, log in warnings report. The user can decide whether to investigate.

### Foliage proposals (informational, not strictly a warning)

**Detection:** rows where `proposed_group == "TEXTUREGROUP_Foliage"`.

**Interpretation:** not a danger — these are foliage rows that Stage 2 correctly identified. After the Project09 fix, they resolve through the ledger and apply cleanly. Just count and report — they're a useful prediction signal because pre-Project09 they all silent-skipped, so a high Foliage count tells you this folder benefits a lot from the catch-up.

**What to do:** include in pre-flight summary, not in warnings report.

## When pre-flight comes back clean

Zero hard-blocks, zero warns. Proceed with confidence. This is the most common case once the pipeline is stable.

## When you suspect pre-flight is missing something

The user has the standing rule "warn or compile a report at the end of anything weird or warnings." If you notice something the script didn't catch (e.g., proposed compression of `TC_BC7` for a row whose `compression_settings` is already `TC_Masks`, or any cross-field inconsistency that the patterns above don't cover), call it a custom WARN, log it in the warnings collector, and surface it at the end. Better to over-report and let the user wave it off than miss a real problem.
