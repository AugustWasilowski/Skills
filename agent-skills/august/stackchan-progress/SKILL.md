---
name: stackchan-progress
description: "Light up the StackChan 30-LED WS2812 strip as a progress bar during long-running multi-step work. Apply by DEFAULT at the start of any task with 3+ discrete stages that will take more than ~1 minute total (renders, multi-stage migrations, large batch fixes, long deploys, multi-target builds). Computes zone widths from N stages across the strip, picks a distinct color per stage, optionally paints partial-fill within the active stage for intra-stage progress, and signals completion (all-lit then clear) or failure (failing zone solid red, earlier zones stay lit). MCP calls auto-skip if the device is unreachable, so this never blocks work. Triggered automatically — not by `/stackchan-progress`."
metadata:
  type: skill
---

# StackChan progress bar (general-purpose)

A visible indicator on the 30-LED Port C strip mounted to the user's StackChan. They can glance at it from across the desk and know which phase you're in without reading the terminal.

This skill generalizes the per-stage progress bar that the `/macu-render` pipeline uses (`/mnt/storage/shares/MACU/pipeline/stackchan.py`). Apply it to ANY long multi-step task — not just MACU renders.

## When to use (default-on)

USE when **all** of these are true:
- Task has **3 or more** distinct stages you'll execute in sequence
- Total work will take **more than ~1 minute**
- You're working autonomously enough to fire the MCP call between stages

SKIP when:
- Single-step / one-shot tasks
- Total runtime is under ~1 minute
- Pure read / research / exploratory work with no clear stages
- The user has said "no stackchan" / "skip the lights" / "quiet mode"
- The device is already running a `macu-render` (its driver owns the strip)

No need to ask permission — just paint stage 1 at frac=0 when you start and let the lights speak.

## API

Call `mcp__stackchan__set_buffer` with `{ pixels: [[r,g,b], ...], brightness: 32 }`.

- `pixels` is a list of up to 30 `[r, g, b]` triplets, 0-255 each. First N (max 30) LEDs get set; the rest are cleared. Empty `pixels: []` clears the strip.
- `brightness` is firmware-capped to **0..64** because Port C 5V can't deliver more current. Default **32** (calm but visible). Drop to **16** for night, push to **64** for a fully-lit room.
- The MCP swallows timeouts; if the StackChan is unreachable, calls fail silently — they cannot block your work.

## Zone math

Given `N` stages, cumulative end indices across the 30-LED strip:

```
ENDS[i] = round((i + 1) * 30 / N)   for i in 0..N-1
```

Stage `s` (1-indexed) spans `[ENDS[s-2], ENDS[s-1])` — except `s = 1` starts at 0.

For sub-progress fraction `f` (0.0..1.0) within stage `s`, fill `round((end - start) * f)` LEDs of that zone, left-to-right, in the stage's color.

Pre-computed zone widths for common N:

| N  | Zone widths (LEDs per stage)             |
|----|------------------------------------------|
| 2  | 15, 15                                   |
| 3  | 10, 10, 10                               |
| 4  | 8, 7, 8, 7                               |
| 5  | 6, 6, 6, 6, 6                            |
| 6  | 5, 5, 5, 5, 5, 5                         |
| 7  | 4, 4, 5, 4, 4, 5, 4                      |
| 8  | 4, 4, 3, 4, 4, 4, 3, 4                   |
| 10 | 3, 3, 3, 3, 3, 3, 3, 3, 3, 3             |
| 15 | 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2 |

For any other N, just compute on the fly with the formula above.

## Palette

8 high-contrast hues; cycle if `N > 8`.

```python
PALETTE = [
    (40, 80, 255),    # blue
    (255, 20, 200),   # magenta
    (0, 220, 220),    # cyan
    (255, 200, 0),    # yellow
    (0, 220, 60),     # green
    (255, 130, 0),    # orange
    (255, 40, 40),    # red
    (255, 255, 255),  # white
]
ERROR = (255, 0, 0)
```

For small N, pick visually distinct picks from the palette in this order:
- N=2: blue, green
- N=3: blue, yellow, green
- N=4: blue, magenta, yellow, green
- N=5+: take the first N from PALETTE

Adjacent zones must contrast — never two blues touching.

## Lifecycle

1. **Start**: paint with `stage_n=1, frac=0.0`. Whole strip dark, ready to fill.
2. **Each stage start**: paint stages `1..s-1` fully lit + stage `s` at frac=0.
3. **Mid-stage (optional)**: if the stage is long AND you can estimate progress, paint at `frac` in `(0, 1)`. One paint per major sub-milestone is plenty; do NOT paint inside tight inner loops.
4. **Stage complete**: paint that stage at `frac=1.0` before advancing.
5. **All done**: paint every zone at its full color (one final buffer), hold ~3s, then `set_buffer({pixels: []})` to clear.
6. **Failure**: paint the failing stage's zone solid `ERROR` (red), leave earlier zones lit, DO NOT clear. The user can see how far you got.

## Reference buffer builder

```python
def compute_buffer(n_stages, stage_n, frac, palette):
    TOTAL = 30
    ends = [round((i + 1) * TOTAL / n_stages) for i in range(n_stages)]
    buf = [[0, 0, 0] for _ in range(TOTAL)]
    # Fill all completed stages.
    for s in range(1, stage_n):
        start = ends[s - 2] if s > 1 else 0
        color = list(palette[(s - 1) % len(palette)])
        for i in range(start, ends[s - 1]):
            buf[i] = color
    # Partial-fill the current stage.
    if 1 <= stage_n <= n_stages:
        start = ends[stage_n - 2] if stage_n > 1 else 0
        end = ends[stage_n - 1]
        f = max(0.0, min(1.0, frac))
        filled = round((end - start) * f)
        color = list(palette[(stage_n - 1) % len(palette)])
        for i in range(start, start + filled):
            buf[i] = color
    return buf
```

In a session you can either call this via a tiny Python one-liner through Bash, or just compute the buffer by hand for small N (the zone widths are short enough to inline). Then fire `mcp__stackchan__set_buffer` with the result.

## Don't-block rules

- **Never** wait on the MCP response in a way that gates your real work. The tool already times out fast; treat every paint as fire-and-forget.
- **Never** paint inside a tight inner loop (per-file, per-frame). Paint on stage boundaries and at most a few sub-milestones per long stage.
- If a paint fails or errors, ignore and continue. The strip is a nice-to-have, not a load-bearing component.

## Examples

**4-step deploy** (build, test, push, smoke-test):
- Stage 1 (build) starts: `set_buffer(compute_buffer(4, 1, 0.0, palette))`
- Build finishes, test starts: `set_buffer(compute_buffer(4, 2, 0.0, palette))`
- ...
- All done: `set_buffer(compute_buffer(4, 4, 1.0, palette))` → wait 3s → `set_buffer({pixels: []})`

**5-step batch fix across files**, each step a different file:
- Same pattern, N=5, advance the stage after each file is patched + verified.

**Long single-step work that you split into sub-progress** (e.g. one big script with 6 logical phases):
- Treat the phases as N=6 stages.

## Reference

- MACU-specific implementation (8 fixed stages, custom palette, brightness scaler): `/mnt/storage/shares/MACU/pipeline/stackchan.py`
- Firmware endpoint behind the MCP tool: `POST /leds/buffer` on `http://<STACKCHAN_IP>`
- Power / pin map / OTA: see `[[stackchan-firmware-ops]]` memory and `10-Built-Apps/StackChan/` in the server-infra vault
