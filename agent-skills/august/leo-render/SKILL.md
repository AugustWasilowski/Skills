---
name: leo-render
description: >
  Generate MACU anchor stills and lip-synced talking-head videos on Leo's GPU (<WORKSTATION_IP>:8779).
  Three modes: (1) text prompt → 1970s MACU news-anchor still (Z-Image-Turbo fp8, ~14 s warm);
  (2) still + audio → lip-synced talking-head video (Wan 2.1 I2V + InfiniteTalk fp8, ~2–6 min);
  (3) full chain: prompt + audio → anchor → talking head. Trigger when August asks to "make an
  anchor image", "generate an anchor still", "make a talking-head clip", "lip-sync this audio to
  an image/anchor", "render a talking head on Leo", or "/leo-render". NOT the episode pipeline —
  that's `macu-render`. Outputs land on the MACU share where Max reads them directly.
---

# leo-render — anchor stills + talking heads on Leo's GPU

Leo (Windows box, WSL, `<WORKSTATION_IP>`) runs a render service on **:8779** (LAN-direct, Hyper-V
firewall opened). Single GPU — jobs queue and run one at a time. Everything is **async**:
POST returns a `job_id`, you poll status, then read the finished file straight off the share
at `/mnt/storage/shares/MACU/...`.

## Pre-flight (always do this first)

```bash
curl -s -m 5 http://<WORKSTATION_IP>:8779/
```

- **Up** → proceed.
- **Down** → the services are stopped (August parks the GPU for work). Recovery options, in order:
  1. Ask August (voice buddy / StackChan / chat): "hit Start in the MACU tray app on your Windows box"
     (MACU favicon in the tray → Start services).
  2. SSH to Leo-WSL and `sudo systemctl start leo-comfyui leo-lipsync`
     (key `~/.config/n8n-leo-wsl/id_ed25519`, host `<your-tailnet-host>` or `<WORKSTATION_IP>` —
     note SSH is only reachable when the box is awake; if SSH times out, the box is off/asleep
     and only August can help).
- **Cold-start warning**: the FIRST render after a service start is slow — one-time fp8 CUDA
  kernel compile: ~70 s for an image, ~10 min for a video. After that: ~14 s image, ~2 min fast
  video, ~5–6 min quality video. Tell August up front if you know it's a cold start.

## Endpoints

Primary = direct to Leo (Max is on the same LAN). Fallback / remote = the n8n webhooks
(workflow `ilvZYYO93QiccRVT`, "MACU – Render (Leo): image + lip-sync") which just forward.

| Action | Direct (preferred from Max) | n8n webhook (remote/desktop callers) |
|---|---|---|
| Image | `POST http://<WORKSTATION_IP>:8779/render-image` | `POST http://localhost:4000/webhook/macu-image` |
| Lip-sync | `POST http://<WORKSTATION_IP>:8779/render` | `POST http://localhost:4000/webhook/macu-lipsync` |
| Status | `GET http://<WORKSTATION_IP>:8779/status/<job_id>` | `GET http://localhost:4000/webhook/macu-lipsync-status?id=<job_id>` |
| Result bytes (fallback) | `GET http://<WORKSTATION_IP>:8779/result/<job_id>` | `POST http://localhost:4000/webhook/macu-lipsync-fetch {"id":...}` |
| Job list | `GET http://<WORKSTATION_IP>:8779/jobs` | — |

Status response: `{status: queued|running|done|error, output: "/mnt/storage/shares/MACU/...", output_size}`.
The `output` path is already translated to Max's view of the share — read it directly; the
fetch-bytes endpoint is only a fallback if the share is somehow stale.

## Mode 1 — anchor image (prompt → PNG)

```json
POST /render-image
{
  "name": "ron-desk-01",
  "prompt": "<scene description> + STYLE_SUFFIX",
  "out_rel": "shows/the-macu-report/episodes/ep-NN/anchors/ron-desk-01.png",
  "params": {"width": 1024, "height": 1024, "steps": 8, "cfg": 1.0, "shift": 3.0, "seed": 123}
}
```

- Defaults: 1024×1024, 8 steps, cfg 1.0, shift 3.0. Leave them unless August asks.
- `out_rel` is relative to the MACU share root; omit it and the image lands in `…/MACU/_anchors/<name>.png`.
- **House style** — append the canonical MACU suffix to every anchor prompt (same one the episode
  manifests use):
  `, black and white, grainy vintage analog television footage, 1970s broadcast, retro futurism, low resolution, washed out, soft focus`
  Typical base: `a 1970s television news anchor at a broadcast desk, suit and tie, studio
  backdrop, facing camera` + whatever character/scene detail August wants. Vary `seed` for takes.
- Poll every ~5 s; warm renders finish in ~15 s.

## Mode 2 — talking head (image + audio → MP4)

```json
POST /render
{
  "name": "ron-cold-open",
  "image_path": "/mnt/storage/shares/MACU/.../anchors/ron-desk-01.png",
  "audio_path": "/mnt/storage/shares/MACU/.../vo/c01.wav",
  "out_rel": "shows/the-macu-report/episodes/ep-NN/lipsync/ron-cold-open.mp4",
  "params": {"frames": 89, "steps": 10, "audio_cfg_scale": 3.0}
}
```

- Pass Max-side `/mnt/storage/...` paths — Leo auto-translates to its `/mnt/m/...` view.
  `image_b64` / `audio_b64` exist but share paths are simpler.
- **Presets** (offer August the choice):
  - **quality** (default): `{"frames": 89, "steps": 10, "audio_cfg_scale": 3.0}` — ~5–6 min.
  - **fast**: `{"frames": 81, "steps": 6, "audio_cfg_scale": 1.0}` — ~2 min, weaker lip lock.
- `audio_cfg_scale` is the lip-sync strength knob: 1 = fast/weak, 3 = strong but ~2× slower.
- Default output (no `out_rel`): `…/MACU/_lipsync/<name>.mp4`.
- Poll every ~20 s.

## Mode 3 — full chain (prompt + audio → talking head)

1. Mode 1 with the prompt → poll until `done` → take the `output` path.
2. Mode 2 with `image_path` = that output + the audio.
3. Return the final mp4 share path.

For episode assets always set `out_rel` under `shows/<show>/episodes/<slug>/...`; loose
experiments can use the `_anchors`/`_lipsync` defaults.

## Polling pattern

```bash
JOB=$(curl -s -X POST http://<WORKSTATION_IP>:8779/render-image -H 'Content-Type: application/json' -d @req.json | python3 -c 'import sys,json;print(json.load(sys.stdin)["job_id"])')
# then loop:
curl -s http://<WORKSTATION_IP>:8779/status/$JOB
```

Sleep between polls (5 s images / 20 s video); jobs queue FIFO on the single GPU, so a `queued`
status may just mean another job is ahead. `error` status → grab logs:
`ssh leo 'journalctl -u leo-lipsync -n 50'`.

## Gotchas (learned the hard way on Leo — do not relearn)

- **Never switch the Wan models to GGUF** — Q4 outputs noise, Q8 NaNs in this torch/WSL combo.
  The fp8 safetensors already wired are the only working setup.
- Both turbo models are CFG-distilled: **cfg stays 1.0**. Z-Image: 8 steps, sampler
  `res_multistep`, scheduler `simple`, CLIPLoader `lumina2`. Lip-sync: lightx2v distill lora,
  `lcm`, 6–10 steps, `rope_function=default`. Don't "tune" these via params.
- Network is LAN-direct on purpose — Tailscale was too slow for the payloads. ComfyUI itself
  stays localhost-only on Leo; only :8779 is exposed.

## Where it lives on Leo (for fixes — SSH in)

- Service: `/mnt/f/ML/ComfyUI/leo_lipsync_serve.py` (stdlib HTTP :8779); image graph inline
  (`build_image_prompt`), lip-sync graph `lipsync_template.json`.
- systemd: `leo-comfyui` (ComfyUI :8188 localhost) + `leo-lipsync` (:8779); env in the units sets
  `LEO_SHARE_BASE=/mnt/m/shares/MACU`, `MAX_SHARE_BASE=/mnt/storage/shares/MACU`.
- Full API contract + deploy: `/mnt/f/ML/ComfyUI/deploy-lipsync/README.md`, `install.sh`,
  `open-firewall.ps1`, tray app `leo-tray.ps1`/`.vbs`.
- Models: image = `z_image_turbo_fp8.safetensors` + `qwen_3_4b` TE + `ae.safetensors` VAE;
  video = `Wan2_1-I2V-14B-480p_fp8_e4m3fn_scaled_KJ` + `Wan2_1-InfiniteTalk-Single_fp8_…_KJ`
  (on ext4 `~/comfy-models`, symlinked from SwarmUI).

## Reporting back

Give August the share path (`/mnt/storage/shares/MACU/...` = `S:\MACU\...` on Windows) and, for
images, consider sending the file via SendUserFile so he sees it inline. Mention render time and
which preset was used.
