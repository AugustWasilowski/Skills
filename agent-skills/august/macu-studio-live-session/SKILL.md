---
name: macu-studio-live-session
description: Start a MACU Studio live production session on leo. Use when August says "macu studio live session", "let's do a MACU session", "boot up the studio", "start a studio session", "let's work on an episode", or wants to produce/edit a MACU Report episode in the Studio app. Gets leo on the latest code, launches the Studio app (FastAPI+SPA+MCP on :8774) detached, hands August the UI URL + MCP connect command, and briefs Max (the developer peer) to stand by for incoming issues.
---

# MACU Studio — Live Session Startup

Recurring workflow. Roles for these sessions: **August = client**, **Max = developer** (peer agent on the intercom, host `max`), **you (Leo) = customer-service rep** — you drive Studio via its MCP tools, hand-hold August through the web UI, and bubble any friction/bugs/UX papercuts to Max, who fixes + commits + pushes so you both keep moving.

Studio runs **on leo** (`<WORKSTATION_IP>`). Its MCP server only exists while the uvicorn app is running locally — so booting the app *is* what gives you the tools. Do NOT point at Max's box (`<MEDIA_SERVER_IP>`); that's his separate dev instance.

## Key facts (leo)
- **Repo:** `F:\MACU\macu-pipeline` (Windows path) = `/mnt/f/MACU/macu-pipeline` (WSL). Studio app under `studio/`.
- **Runs in WSL** (`Ubuntu` distro), POSIX venv at `studio/.venv`. Drive WSL through the **PowerShell tool** (`wsl -d Ubuntu -- bash -lc "..."`), never Git Bash (it mangles leading-slash paths).
- **Ports:** Studio `:8774` (UI + `/api` + `/mcp`), render service `:8773` (internal, optional — see below).
- **Reachability gotcha:** from the Windows host, `localhost:8774` may time out (WSL loopback mirroring is flaky). **Use the LAN IP `http://<WORKSTATION_IP>:8774`** for both August's browser and the MCP connection.
- **systemd units are NOT installed on leo** — launch manually + detached so the app survives August restarting his Claude session for the MCP.
- **No auth** (LAN-only trust model).

## Procedure

### 1. Make contact with Max + confirm online
- `intercom_peers` — confirm `max` is online.
- `intercom_send` to `max`: brief him on roles for this session (August=client, Max=dev, Leo=CS), that you're producing an episode in Studio on leo, and that you'll bubble friction to him to fix+commit+push fast. Ask him to run the pre-flight in step 2 on his checkout.

### 2. Get on the latest code
- **Max's side (ask him):** `git status` → confirm working tree clean and **no unpushed local commits**. If he has unpushed dev work, he pushes it first (or tells you why not) before you pull.
- **Leo's side (you run):**
  ```
  git -C F:\MACU\macu-pipeline status -sb
  git -C F:\MACU\macu-pipeline pull --ff-only
  ```
  The tracked tree is normally clean; there will be many untracked `.scratch.py`/`.sh` dotfiles from prior episodes — ignore them.
- **Reinstall only if the pull brought changes** that touch the app. If `git pull` says "Already up to date" → skip reinstall, go straight to launch. If it pulled changes:
  - frontend changes → rebuild: `wsl -d Ubuntu -- bash -lc "cd /mnt/f/MACU/macu-pipeline/studio && ./scripts/install.sh"` (backend venv + frontend build), or just `cd frontend && npm run build` for FE-only.
  - backend-only Python changes → usually just relaunch uvicorn (step 3); only re-run install.sh if deps changed (`pyproject.toml` touched).

### 3. Launch Studio detached + verify
Run the bundled launcher (copy is in this skill dir; canonical copy lives at `studio/.start_studio.sh`). It binds `0.0.0.0:8774` via `nohup setsid` so it survives a session restart:
```
wsl -d Ubuntu -- bash -lc "bash /mnt/f/MACU/macu-pipeline/studio/.start_studio.sh; sleep 4; curl -s http://127.0.0.1:8774/api/health; echo; tail -n 8 /tmp/macu-studio.log"
```
Expect `{"ok":true,"release":"vX.Y.Z",...}` and `Uvicorn running on http://0.0.0.0:8774` + `StreamableHTTP session manager started`.
Then confirm host reachability (use the **LAN IP**, not localhost):
```
(Invoke-WebRequest -UseBasicParsing -Uri http://<WORKSTATION_IP>:8774/api/health -TimeoutSec 5).Content
```
If it's already running (health responds before you launch), don't double-start — just proceed.

### 4. Hand August the connect steps
Give August:
1. **UI:** `http://<WORKSTATION_IP>:8774/`
2. **Register MCP, then restart Claude Code:**
   ```
   claude mcp add --transport http macu-studio http://<WORKSTATION_IP>:8774/mcp
   ```
   Fallback if `--transport http` errors: `claude mcp add macu-studio -- npx -y mcp-remote@latest http://<WORKSTATION_IP>:8774/mcp --allow-http`

### 5. On reconnect — confirm the link
After August restarts, the `macu-studio` MCP server (~27 tools) should be present. First call **`studio_overview`** — it returns the shows, what's connected, and the step-by-step episode workflow (create episode → write script → manifest → shots → render → publish). If tools don't enumerate, ping Max.

### 6. Render service (defer)
Don't start `macu-render` (:8773) up front. Bring it up only when you reach an actual render stage. Studio's health will show the render URL as configured even when render is down — that's fine for script/VO/manifest/shot-prep work. See **Render backends** below before rendering ep-022 specifically.

## Render backends (when you reach the render stage)
Two valid paths, **August's call** (he cares about "local = leo"):
- **A — masters on Max's ComfyUI** (`<MEDIA_SERVER_IP>:8188`, an episode manifest's own endpoint if set to zeroscope). Drive leo pipeline with `MACU_COMFY_URL=http://<MEDIA_SERVER_IP>:8188`; collected over HTTP via `/view` (no shared FS). Zero setup; uses Max's GPU; crosses "local=leo".
- **B — all-WAN i2v fully on leo** (matches how ep-021 was built). MCP: `set_masters_backend wan_i2v` → `generate_stills` → mark character cues `kind=lipsync` (must LEAD a mixed cue) → `run_pipeline`. As of 2026-06-15 leo's ComfyUI has all required bare-named fp8 safetensors indexed (I2V, InfiniteTalk, lightx2v lora, clip_vision_h, Wan2_1_VAE_bf16, umt5_xxl) → **no symlinks/setup needed**. Verify before relying on it with `studio/.comfy_objinfo.sh` (queries ComfyUI `/object_info`).
- ep-022 specific brief: `F:\MACU\macu-pipeline\EP22_RENDER_BLOCKER.md`.

## Higgsfield lipsync gotchas (hard-won on ep-022)
Lipsync = `kind: lipsync`, model **`wan2_7`** (audio-driven talking head), `source_still=<char key>`. The model WORKS — if a head renders static, it's the INPUTS, not the model. Two distinct failure modes, both seen on ep-022:

1. **Still must be a TIGHT FRONTAL face** (head-and-shoulders, face fills frame, mouth clearly visible). Wide/environmental/small-face stills → wan2_7 animates body/scene but finds no mouth → no lip motion. Fix: generate a tight portrait take (`generate_character_takes` with a portrait prompt — strip the scene so nano_banana doesn't render wide), `set_default_take`, `use_character_in_episode`, regen.
2. **The lipsync VIDEO PROMPT is the character's manifest `core`.** If the core describes a SCENE/ACTION ("at a tasting bench, packet before him, candlelight"; "theatrical wrestling poses"; "podium in a hearing room"), wan2_7 dramatizes it — subject looks away/down — and never lip-syncs. For lipsync characters set the core to a TALKING-HEAD prompt: *"<who> speaking directly to the camera, head and shoulders, facing forward, talking naturally, composed and still with only natural speaking motion, plain dark background, black and white vintage television"*. Identity comes from the STILL, not the prompt. (Ron/Walter/Daryl worked out of the box because their cores were already "news anchor at a desk".)

- **Cache caveat:** `lipsync_hash` = still_sha + vo_sha + model (NOT the prompt). Changing only the core does NOT mark a shot stale → it won't re-render. Force it with `generate_cloud_shot` (drops the clip) or by changing the still (`use_character_in_episode`, which bumps still_sha).
- **mouthless characters** (e.g. a paper-bag head): can't lipsync; static is correct. On fresh builds flag `mouthless: true`/`no_lipsync: true` so it routes to i2v and skips a doomed lipsync gen. Retroactive flagging on already-rendered clips just wastes a re-render — skip it.
- **ALWAYS render with the LATEST selected take.** When the user curates takes in the Studio UI, re-fetch `list_characters` (watch `default_take` + `updated_at`) and `use_character_in_episode` each current default into the episode BEFORE rendering — and re-check if they keep tweaking. A stale still renders the wrong face (and re-breaks lipsync if the old one was wide). On ep-022 the user reselected bureau_chair/roscoe takes mid-flow; pausing to re-sync before the render saved a wrong-face pass.
- **Validate one shot before scaling.** `generate_cloud_shot <shot>` → extract frames (ffmpeg) → confirm frontal + mouth motion BEFORE re-rendering the whole episode. Pull seg results straight from HF with the Higgsfield MCP `job_status` for fast inspection.

## WSL / PowerShell quoting pitfalls (learned the hard way)
- The PowerShell tool evaluates `$(...)` **before** passing the string to `wsl ... bash -lc` → your bash command substitution runs in PowerShell and errors (`wslpath`/`pgrep` "not recognized"). **Avoid `$()` and bash arrays/heredocs in the inline string.** For anything non-trivial, **write a `.sh` file** (e.g. into `studio/` as a `.scratch.sh`) and run `bash /mnt/f/.../script.sh` — this is what the bundled `start_studio.sh` / `comfy_objinfo.sh` do.
- Prefer `/mnt/f/...` paths in WSL commands.
