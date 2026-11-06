---
name: fts-texture-optimizer
description: Run the FTS texture audit (Stage 3) against one or more folders under /Game/Hermes/Art. Use this skill whenever the user mentions a folder under /Game/Hermes/Art/ and wants its textures optimized, capped, recompressed, or processed — or says "run the texture pipeline", "process /Environment/Wasteland", "do textures for /Architecture", "audit Volcanic", "apply Stage 3 on X", "do the rest of /Environment". Also use when the user wants to re-run Stage 2 (the offline classifier) after editing classification logic. Supports a single folder or a list. Two execution modes — Computer Use (Claude drives Unreal) or pair-programmer (Claude edits scripts; user pastes lines into Unreal Editor). Assumes Unreal Editor is already open with the FTS project loaded and View Changes / Output Log / Python console panels visible.
---

# FTS Texture Optimizer

This skill runs Stage 3 of the FTS texture audit pipeline against one or more folders under `/Game/Hermes/Art/`. The pipeline is real, well-tested, and described in detail at `references/pipeline_overview.md`. Read that file before doing anything destructive.

The user is Mayor Awesome (August Wasilowski). He owns the audit. The standing FTS-8915 ticket and Confluence runbook live outside this skill — the skill stays focused on the pipeline mechanics; he handles the comms.

## Hard rules (non-negotiable)

These rules exist because we burned hours diagnosing what they prevent. Don't relax them.

1. **Never modify `ACTION_FILTER` or `CONFIDENCE_FILTER` in `fts_stage3_apply.py` without explicit per-instance user approval.** They're safety gates. Touching them silently is how mass corruption happens.
2. **Never run a folder the user hasn't named.** The script's `FOLDER_FILTER` is one guard; the skill is the second.
3. **Always dry-run before going live.** The dry-run/live-run row count comparison is the single best sanity check. If they don't match, stop.
4. **Stop on hard-block patterns from pre-flight.** They're listed in `references/pre_flight_patterns.md`. Don't proceed past one without the user telling you to.
5. **Don't touch `.uasset` files directly.** Modifications happen through Stage 3 in the Unreal Editor only.

## What the skill does NOT do

The user explicitly does these himself; do not nag or take initiative on them:

- Take memreports
- Update FTS-8915 with progress
- Update the Confluence audit page changelog
- Submit Perforce changelists (creates them only; never submits)
- Launch the Unreal Editor or open a project (assume it's already running)

## Preconditions

The user gets "mise en place" ready before invoking this skill. The skill assumes:

- Unreal Editor is open with the FTS project loaded
- The View Changes (source control) panel is visible
- The Output Log panel is visible and tailing
- The Python console field is accessible at the bottom of the editor
- Source control is connected
- The pipeline files exist at `F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\`

If any of these are missing, ask the user to fix it rather than trying to set it up yourself.

## Step 1 — Gather inputs

Before doing anything, confirm with the user:

1. **Target folder(s)** — one path or a list, exact prefix matching what's in `stage2_proposed_APPROVED.csv` (e.g., `/Game/Hermes/Art/Environment/Wasteland/`). If the user says "Wasteland" without a full path, normalize it but read it back to confirm.
2. **Mode** — Computer Use (Claude drives Unreal) or pair-programmer (user pastes the exec lines and runs them in UE). If unclear, ask. Don't assume.
3. **P4 changesets** — default ON. After each folder's live-run, create a per-folder Perforce changelist named `Texture Optimization - Hermes/Art/<folder>` and move modified assets into it. Only skip if the user explicitly says "don't worry about P4" or "skip changelists".

**Don't proceed until all three are confirmed.** Read inputs back to the user as a one-line plan ("OK — Computer Use mode, P4 changesets ON, processing: /Environment/Volcanic, /Environment/Wasteland, /Environment/Oceanic, in that order. Confirm?") and wait for go-ahead.

## Step 2 — Per-folder loop

For each folder in the target list, run this sequence. Don't parallelize folders — the Unreal Editor's Python console is single-threaded and Stage 3 takes minutes per folder.

### 2a. Pre-flight (offline)

Run the pre-flight analyzer:

```bash
python3 <skill-dir>/scripts/pre_flight.py --folder /Game/Hermes/Art/<...>/ --csv <path-to-stage2_proposed_APPROVED.csv>
```

Or on Windows directly:

```
python <skill-dir>\scripts\pre_flight.py --folder /Game/Hermes/Art/<...>/ --csv F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\stage2_proposed_APPROVED.csv
```

The script:
- Reports row counts by action/confidence/group
- Predicts the Stage 3 touchable count (the live run will report ≤ this number — Stage 3 only counts true field deltas)
- Estimates savings
- Surfaces danger-pattern flags

**If pre-flight exits non-zero (hard-block flag), STOP this folder immediately** and surface the flag(s) to the user. Don't auto-proceed even if "it looks fine to you". Hard-block patterns and their interpretations live in `references/pre_flight_patterns.md`.

If only WARN flags surface, log them in the warnings collector (a list you maintain in conversation memory across the batch — surface it at end of run) and continue.

### 2b. Edit `fts_stage3_apply.py`

Open `F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\fts_stage3_apply.py` and change two lines:

```python
DRY_RUN = True
FOLDER_FILTER = "/Game/Hermes/Art/<...>/"
```

Leave `ACTION_FILTER`, `CONFIDENCE_FILTER`, and everything else untouched. Save.

After editing, **always re-Read the file** to confirm the change committed. There's a known race where the edit doesn't propagate to UE before paste, especially if you're chaining edits and pastes quickly.

### 2c. Dry-run

The mode dispatch lives in:

- Computer Use mode: `references/computer_use_runbook.md`
- Pair-programmer mode: `references/pair_programmer_runbook.md`

Both runbooks describe getting the user (or yourself) to paste this exact line into the UE Python console:

```
exec(open(r"F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\fts_stage3_apply.py").read())
```

Capture the final output line. It looks like:

```
LogPython: [FTS] DONE in <Xs>s -- changed <N>, skipped <M>, failed <F>
```

Acceptance criteria for the dry-run:
- `failed` = 0
- `changed` count is plausible: ≤ pre-flight's predicted touchable count, ≥ ~50% of it (large gap means something has shifted; investigate before going live)

If acceptance fails, STOP the folder. Don't paper over it.

### 2d. Live-run

Edit `fts_stage3_apply.py` to set `DRY_RUN = False`. Re-Read to confirm. Then trigger the same exec line via the active mode's runbook.

Live-run takes longer than dry-run (~1.5–2 seconds per saved asset). Folder of 175 → ~5 min. Folder of 663 → ~20 min. Plan the wait accordingly. Watch for the "Checking out packages..." dialog — it's normal and can sit for a while; let it run.

Acceptance criteria for the live-run:
- `failed` = 0
- `changed` count exactly matches the dry-run

Mismatch → STOP. Surface to user.

### 2e. P4 changelist (if enabled)

If the user opted in to P4 changesets, follow the runbook for the active mode to:

1. Create a new changelist with description `Texture Optimization - Hermes/Art/<folder>`
2. Move every modified asset (anything still in `default`) into the new changelist

In pair mode, you describe the steps; the user clicks. In Computer Use mode, you drive.

Never submit. Only stage the changelist for the user.

### 2f. Append to session log

Append a short entry to `F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\session_log.md` capturing:

- Date
- Folder path
- Pre-flight predicted count
- Dry-run / live-run results (changed, skipped, failed, time)
- Any WARN flags
- P4 changelist number (if created)

Keep it terse — one short section per folder. The session log is the cross-session memory.

## Step 3 — Wrap-up after the batch

When all target folders are done:

1. **Surface the warnings collector.** If any folder produced WARN flags, list them all together at the end with one paragraph each. The user wants a "compile report at the end of anything weird".
2. **Tally the totals.** Total textures changed, total estimated savings, list of P4 changelists created.
3. **Stop.** Don't push to FTS-8915 or Confluence — the user does that himself.

## Re-running Stage 2 (the classifier)

The user may want to re-run Stage 2 mid-session if they've changed classification logic. This is a separate workflow — see `references/pipeline_overview.md` ("When and how to re-run Stage 2") for the cookbook. The short version:

1. Back up the current `stage2_proposed_APPROVED.csv` and `stage2_full_review.csv` (e.g., `.pre-<change>.bak`).
2. Run: `python fts_stage2_classify.py --in stage1_inventory.csv --out stage2_proposed_APPROVED.csv --review-out stage2_full_review.csv`
3. Diff the new CSV against the backup for the user's target folder(s) — show them what proposals changed before they re-run Stage 3.
4. Continue with the per-folder loop.

Never re-run Stage 2 silently as part of a per-folder run. It's a deliberate action that needs the user's awareness.

## Reference files

Read these on demand based on what you're doing:

- `references/pipeline_overview.md` — Stage 1/2/3 mechanics, knobs, Stage 2 re-run cookbook, expected file locations
- `references/pre_flight_patterns.md` — danger patterns with severity, detection criteria, and interpretation
- `references/computer_use_runbook.md` — strategy for driving the Unreal Editor via Computer Use (no memorized coordinates)
- `references/pair_programmer_runbook.md` — strategy for the paste-and-report workflow
