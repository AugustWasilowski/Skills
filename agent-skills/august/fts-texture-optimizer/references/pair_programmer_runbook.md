# Pair-Programmer Mode Runbook

In pair-programmer mode, you (Claude) edit scripts and analyze results. The user pastes the exec lines into the Unreal Editor and operates the source-control panel.

This is the more common mode and the easier one — UE actions stay with the human, who's faster and more reliable in the GUI than any computer-use sequence.

## The handoff cadence

The flow alternates between Claude and the user. After every action that produces information you need to interpret, you wait for the user's response before continuing.

Per folder, the loop is:

1. Claude pre-flights → reports counts, savings, flags.
2. Claude edits `apply.py` for dry-run.
3. Claude tells user the paste line. **Claude waits.**
4. User pastes in UE, sends back the DONE log line.
5. Claude verifies dry-run is acceptable.
6. Claude edits `apply.py` for live-run.
7. Claude tells user to paste again. **Claude waits.**
8. User pastes, sends back live DONE log line.
9. Claude verifies live matches dry-run.
10. If P4 enabled: Claude tells user how to create the changelist + move files. **Claude waits for confirmation.**
11. Claude appends to session log.
12. Repeat for next folder.

## Telling the user what to paste

Use a fenced code block so the user can copy-paste cleanly. The exec line is identical every time:

````
Paste in Unreal:

```
exec(open(r"F:\Snail\fts-dev\hermes\Content\Python\AssetAudit\fts_stage3_apply.py").read())
```
````

Tell the user explicitly what state to expect:

- For dry-run: "Expecting `[FTS] DONE in ~1s -- changed N, skipped M, failed 0`. Send back the tail of the log."
- For live-run: "Expecting `[FTS] DONE in <several minutes>s -- changed <same N as dry-run>, skipped M, failed 0`. Send back the tail when it's done."

## Verifying the user's response

When the user sends back a log snippet, parse the final line. The format is:

```
LogPython: [FTS] DONE in <X>s -- changed <N>, skipped <M>, failed <F>
```

- `X` — elapsed time in seconds
- `N` — count of rows where at least one field was changed (or would have been, in dry-run)
- `M` — count of rows skipped (filter mismatch, no field deltas, etc.)
- `F` — failures (Python exceptions)

Acceptance checks:

- `F` must be 0. Anything else → stop, ask user.
- For dry-run: `N` should be ≤ pre-flight predicted touchable count, and roughly within 50% of it. Big gap → investigate before going live.
- For live-run: `N` must exactly match the dry-run's `N`. Mismatch → stop.

## Telling the user how to create the P4 changelist

After a successful live-run with P4 changesets enabled:

> Live-run looks good. To create the changelist:
>
> 1. In the View Changes panel, click the **+** icon at the top of the Changelists section.
> 2. In the dialog, type the description: `Texture Optimization - Hermes/Art/<folder>`
> 3. Click **Ok**.
> 4. Click on the **default** changelist row to see its files.
> 5. Click into the file list, press **Ctrl+A** to select all.
> 6. Right-click → **Move Files To...**
> 7. In the dropdown, pick the new changelist (matches by description).
> 8. Click **Ok**.
>
> Confirm when files are in the new changelist.

Wait for the user to confirm. Don't proceed to the next folder until they say so.

## Edit-Read-Edit pattern for `apply.py`

You'll edit `apply.py` repeatedly during a session — toggling `DRY_RUN` and switching `FOLDER_FILTER`. After every Edit, **re-Read the file** to confirm the change committed. There's a known race where the OS hasn't flushed the change before the next operation reads it.

Example:

```
Edit apply.py: set DRY_RUN = True
Read apply.py (lines 48-60) — confirm both DRY_RUN and FOLDER_FILTER are correct
[Tell user to paste]
```

If the Read shows stale content, Edit again and Read again before telling the user to paste.

## Surfacing pre-flight results

Pair mode is great because the user can read pre-flight results inline. Format them as a compact table:

```
**Pre-flight: /Game/Hermes/Art/Environment/<folder>/**

| Metric | Value |
|---|---|
| Total rows in folder | <N> |
| Stage 3 touchable | <N> (<action breakdown>) |
| Estimated savings | <X> GB |
| Mix-map mislabels | 0 |
| Normal-flips on real normals | 0 |
| /Demos contamination | 0 |
| Foliage proposals | <N> (will route through Project09) |
| Subfolders | <list> |

[clean / WARN flags / BLOCK flags]
```

If hard-block flags appear, surface them prominently and ask the user how to proceed. Don't proceed without their go-ahead.

## When the user's UE setup is different

If the user reports an error pasting (e.g., "the Python field isn't visible" or "the View Changes panel is missing"), stop the workflow and help them get the editor set up. Don't try to work around a broken UI.

The skill's preconditions assume the user has set up "mise en place" — but if reality differs, fix reality, then resume.

## When the user goes silent

If the user has stepped away mid-session, don't proceed past the next handoff point on assumption. Wait. Pair mode requires the human; without them, you can't run live in UE.

If a long live-run is in progress (>5 minutes since you last heard from them), it's fine to stay quiet — they're probably letting it cook. But don't push to the next folder without an explicit signal.
