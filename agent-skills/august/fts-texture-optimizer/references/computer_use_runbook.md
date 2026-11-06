# Computer Use Mode Runbook

In Computer Use mode, you (Claude) drive the Unreal Editor directly. The user is hands-off and may have stepped away.

## Strategy, not coordinates

The Unreal Editor's panel layout depends on the user's resolution, monitor setup, and how they've arranged their workspace. **Click coordinates that worked last session probably won't work this session.** Don't memorize them. Always start with a fresh screenshot and locate UI elements visually.

The rest of this file describes the *strategy* for finding each element and the *sequence* of actions for each operation — not the pixel positions.

## Setup: gain access

Before any computer-use tool call, request access:

```
request_access(
    apps=["unrealeditor.exe"],
    reason="Drive Unreal Editor's Python console to run Stage 3 of the texture audit",
    clipboardWrite=true
)
```

Important: the Steam-launched app (e.g., "For The Stars") is the launcher; the actual editor process is `unrealeditor.exe`. Request that one. `clipboardWrite=true` enables the fast-paste path for the long exec line.

After the grant, take a screenshot. If the editor isn't focused, call `open_application("Unrealeditor")` and re-screenshot. If a startup modal is up (we've seen "Plugin Media2DFramework failed to load..." before), dismiss it before proceeding.

## Finding the Python console

The Python console field lives at the bottom of the editor. Look for:

- A row of tab labels: `Content Drawer`, `Voxel Stamps`, `Output Log`, `Python ▼`, then a text input field
- The text input has placeholder text like "Enter Python script or a filename"
- The `Python ▼` dropdown is the language picker

Take a screenshot and use `zoom` on the bottom strip to confirm. Once you see the placeholder text, click in the input area to focus it.

## Pasting and running the exec line

Always paste via clipboard rather than `type`. The exec line has special characters (`\`, `"`, `(`, `)`) that are slow and unreliable to type, plus clipboard paste is more deterministic.

Sequence:

1. `write_clipboard("exec(open(r\"F:\\Snail\\fts-dev\\hermes\\Content\\Python\\AssetAudit\\fts_stage3_apply.py\").read())")`
2. `left_click` the Python input field (focus it)
3. `key("ctrl+a")` — select any leftover text
4. `key("delete")` — clear it
5. `key("ctrl+v")` — paste
6. `key("Return")` — execute

You can batch all six actions in a single `computer_batch` call to save round-trips.

## Waiting for the run to finish

Don't poll constantly — the live-run takes 1.5–2 seconds per saved asset. For a 175-row folder, expect ~5 minutes; for 663 rows, ~20 minutes. Wait in 50-second chunks (the `wait` tool times out around 60s). Periodically take a screenshot to check progress.

What you'll see during a live run:

- A "Checking out packages..." modal — Unreal asking Perforce to check out files for editing. Can sit at 0% for a while; just wait through it.
- The Output Log scrolling with `[FTS] N/26745 (changed X, skipped Y, failed 0)` progress lines.
- Eventually a `[FTS] DONE in <time>s -- changed N, skipped M, failed F` line.

The dry-run finishes fast (a second or two — just iterating CSV rows without saves). The live-run is slow because each asset needs to be loaded, modified, and saved.

## Capturing the DONE line

After the run completes, the bottom of the Output Log contains the final line. Take a screenshot, then `zoom` on the lower portion of the Output Log panel to read the line clearly.

If you can't find a DONE line in the visible log, the run may not have finished yet — wait more. Or it may have scrolled off — interact with the panel briefly (e.g., click in the log) and re-zoom.

**Known refresh quirk:** the View Changes panel's `default (N)` count doesn't always update visually until you interact with the editor. If you see `default (0)` after a live-run that should have changed N files, click somewhere in the View Changes pane to force a refresh, then re-screenshot.

**Known race:** if you `Edit` `apply.py` and immediately paste in UE, sometimes UE reads the old file content. After every Edit, re-Read the file to confirm the change committed. If a paste seems to run with stale content, do the Edit again, wait a couple seconds, and re-paste.

## Creating a new Perforce changelist

In the View Changes panel:

1. Look at the top of the Changelists section. There's a header row "Changelists (N)" and to the right, two small icons. The leftmost icon (looks like a circle with a + in it, sometimes faint) is "New Changelist". Click it.
2. A "New Changelist..." dialog opens with a description text field pre-selected with placeholder "enter description here".
3. Click the field, `ctrl+a` to select the placeholder, type the description: `Texture Optimization - Hermes/Art/<folder>` (e.g., `Texture Optimization - Hermes/Art/Environment/Wasteland`).
4. Click `Ok`.
5. A toast appears bottom-right: "Changelist successfully created". The new changelist appears at the bottom of the Changelists list with `(0)` files.

If you can't find the `+` icon, you can also right-click on the Changelists header — the context menu may have a "New Changelist" option.

## Moving files to the new changelist

After creating the changelist, the `default` changelist still holds all the modified files. Move them in:

1. Click the `default` changelist row to select it.
2. The right-side asset list now shows all the files in `default`. Click into the asset list area.
3. `ctrl+a` to select all files. They highlight blue.
4. Right-click on the selection. Context menu opens.
5. Click "Move Files To...".
6. A "Move Files To..." dialog opens with a "Target Changelist" dropdown.
7. Click the dropdown. A long list of changelists appears.
8. Find your newly-created changelist (matches by description). Click it.
9. Click `Ok`.
10. Files move. The View Changes panel updates: `default (0)`, your new changelist `(N)`.

## When something looks wrong

- Click coordinates wrong → re-screenshot, re-locate by visual cues
- Modal appeared unexpectedly → screenshot, identify, dismiss appropriately
- UE seems to hang → wait more (Stage 3 saves are slow); only escalate after >2x predicted time
- Output Log doesn't show new content → click in the log area, re-screenshot
- Multiple monitors → call `switch_display(...)` if the editor isn't on the captured monitor

## When to stop and escalate

If anything goes off-script and you can't figure it out from screenshots within a reasonable few attempts, **stop and message the user**. Don't try to brute-force unfamiliar UI states. The pipeline is set up so the user can always recover by reverting the P4 changelist — but only if you don't keep digging.

The escalation channel: a short summary of what you tried and what's on screen, plus a screenshot the user can react to. If the user provided a Telegram notify channel earlier in the session, you can ping there too — but only if Mayor is currently away from the keyboard.
