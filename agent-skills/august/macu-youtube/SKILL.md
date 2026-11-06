---
name: macu-youtube
description: "Publish a rendered MACU episode to the 'The MACU Report' YouTube Brand Account, or edit an already-uploaded video's metadata. Trigger when August says things like 'upload ep-016 to YouTube', 'publish the MACU report to my channel', 'put episode 16 on YouTube (unlisted)', 'edit the title for this video on my channel', 'change the description on the MACU video', or 'schedule Season 3' (treat as a batch of unlisted uploads to queue — never auto-publish). Conversational, Max-driven; NOT wired into MACU Studio."
trigger: /macu-youtube
---

# /macu-youtube

Publish a finished MACU episode to YouTube, or edit a video that's already up. Conversational — August talks to Max, Max builds the payload and POSTs the n8n webhook. **Default privacy is `unlisted`; this skill never makes anything public on its own.**

## What this is

- **n8n workflow:** `MACU – YouTube Publish`, id **`eAlfmwpBKPDvFmXS`**, webhook path **`macu-youtube`**.
- **Production trigger (from Max / the LAN):** `POST http://localhost:4000/webhook/macu-youtube` (use `localhost`, not the host IP — Docker NAT doesn't loop back, and this path skips Cloudflare's 100s edge timeout so long uploads don't get cut off).
- **Credential:** n8n credential `YouTube – MACU Report` (type `youTubeOAuth2Api`), bound to the **Brand Account** channel, not August's personal channel. Shared by the upload, update, and thumbnail nodes.
- **File access:** the render share `/mnt/storage/shares/MACU` is bind-mounted read-only into the n8n container as `/macu`. The workflow reads the MP4/PNG straight off disk — no copy, no upload-to-n8n.

## Where the files are

Renders land at (multi-show aware — slug is globally unique):

```
<episodes_dir>/<slug>/final/
  ├── <slug>.mp4          # the upload
  ├── <slug>_thumb.png    # 1920×1080 YouTube thumbnail (optional — used if present)
  ├── <slug>.srt          # captions (not auto-sideloaded yet — see Future)
  └── <slug>_thumbs.jpg   # contact strip (review only, NOT uploaded)
```

`<episodes_dir>` per show comes from `/mnt/storage/macu-pipeline/studio/shows.json`. The MACU Report default is `/mnt/storage/shares/MACU/shows/the-macu-report/episodes`. Episode metadata (title, season, episode_num) lives in `<slug>/manifest.json`. The helper resolves all of this for you.

## How to run it

### 1. Upload an episode

Build the payload from the manifest, then POST it. `build_payload.py` resolves the slug, maps host→container paths, and templates a default description + tag set.

```bash
cd ~/.claude/skills/macu-youtube
python3 build_payload.py ep-016 > /tmp/yt.json        # action=upload, privacy=unlisted by default
curl -sS --max-time 1800 -X POST http://localhost:4000/webhook/macu-youtube \
  -H 'Content-Type: application/json' --data @/tmp/yt.json
```

The webhook responds synchronously with `{ ok, action, videoId, url, studioUrl, privacyStatus, title }`. Surface `studioUrl` to August so he can review/publish.

**Metadata source of truth — `youtube.txt`.** The `macu-report` skill authors `episodes/<slug>/youtube.txt` (step 6, "Write the YouTube copy") when a script locks — title options (the straight one carries the `S0X-EY` label), an in-universe description, and a hashtag line. `build_payload.py` parses it and uses: the labeled title, the DESCRIPTION block, and the tags (hashtags stripped). The helper logs `meta=youtube.txt` vs `meta=manifest/template` so you know which it used. **Precedence per field: explicit CLI flag > `youtube.txt` > manifest boilerplate.** If an episode has no `youtube.txt`, write one first (it's the `macu-report` deliverable, format-matched to ep-005/006/007) — or pass `--no-youtube-txt` to force the generic template.

**Override in chat.** Even with a `youtube.txt`, Max can override any field:

```bash
python3 build_payload.py ep-016 \
  --description "$(cat /tmp/ep16_blurb.txt)" \
  --tags "MACU,The MACU Report,Mayor Awesome,cannibalism,deadpan,analog horror" \
  > /tmp/yt.json
```

Useful flags: `--title`, `--description`, `--tags "a,b,c"`, `--privacy {private,unlisted,public}` (public also needs `--allow-public`), `--category <id>` (default 24 = Entertainment), `--notify-subscribers`.

### 2. Edit an already-uploaded video

YouTube's update **replaces** the snippet, so always send the full intended state (title + description + tags + privacy), not just the one field you're changing. The helper templates the rest from the manifest; override what should change.

```bash
python3 build_payload.py ep-016 --action update --video-id <VIDEO_ID> \
  --title 'The MACU Report — Episode 16 — "Welcome to the Practice"' \
  > /tmp/yt.json
curl -sS -X POST http://localhost:4000/webhook/macu-youtube \
  -H 'Content-Type: application/json' --data @/tmp/yt.json
```

Get `<VIDEO_ID>` from the `url`/`studioUrl` returned at upload time (the 11-char id), or ask August.

## Webhook body reference

```jsonc
{
  "action": "upload",                 // or "update"
  "video_path": "/macu/shows/the-macu-report/episodes/ep-016/final/ep-016.mp4", // upload only; container path
  "thumbnail_path": "/macu/.../ep-016_thumb.png",  // upload only; "" to skip
  "videoId": "dQw4w9WgXcQ",           // update only
  "title": "…",
  "description": "…",
  "tags": ["MACU", "comedy"],          // array OR comma string; normalized either way
  "privacyStatus": "unlisted",         // private | unlisted | public
  "categoryId": "24",
  "notifySubscribers": false
}
```

Paths are **container paths** (`/macu/...`), which is what `to_container()` in the helper emits. If you ever hand-write a payload, map `/mnt/storage/shares/MACU` → `/macu`.

## Safety rules (do not relax without August saying so)

- **Default `unlisted`.** Never send `privacyStatus: "public"` unless August explicitly asks for this specific video AND you pass `--allow-public`. The point is he eyeballs every upload in YouTube Studio first.
- **No auto-publish / no scheduling.** Don't set `publishAt`. "Schedule Season 3" means queue the episodes as unlisted uploads and report the Studio links — August publishes manually. (Real YouTube scheduled-publish auto-goes-live; that's deliberately not wired.)
- **`notifySubscribers` stays false** for review uploads.
- This is a "publish my own content" action. Confirm the slug + privacy with August before the first POST of a session; after that, batching within the same ask is fine.

## "Schedule Season 3 for next week" pattern

There's no real scheduler here by design. Interpret it as: upload each named episode as **unlisted**, collect the `studioUrl`s, and hand August the list so he can set publish dates himself in Studio. If he ever wants true auto-publish, that's a workflow change (add `publishAt` + privacy=private) — flag it, don't improvise it.

## First-time setup (one-time, needs August)

The workflow exists but is **inactive** and its credential is a placeholder until OAuth is done:

1. August completes the YouTube Data API v3 OAuth in a browser and creates the n8n credential `YouTube – MACU Report`, **choosing the "The MACU Report" Brand channel** at Google's channel-picker step. (Set the OAuth app to "In production" so the refresh token doesn't expire after 7 days.)
2. Attach that credential to the three nodes — `YouTube Upload`, `YouTube Update Metadata`, `Set Thumbnail` — and activate the workflow. Max can do this via the n8n MCP (`update_workflow` → `setNodeCredential`, then activate) once the credential id exists, or August does it in the editor.
3. Test path before going live: POST a payload built with `--privacy private` and confirm the returned `studioUrl` opens the right channel.

## Files

| path | role |
|---|---|
| `~/.claude/skills/macu-youtube/SKILL.md` | this file |
| `~/.claude/skills/macu-youtube/build_payload.py` | slug → manifest → container-path payload builder (templates default metadata) |
| n8n workflow `eAlfmwpBKPDvFmXS` | `MACU – YouTube Publish` (webhook `macu-youtube`) |
| n8n workflow `RqQV2b9NJqefmTSb` | `MACU – YouTube Captions` (webhook `macu-youtube-captions`) |
| `~/docker/n8n/docker-compose.yml` | the `/mnt/storage/shares/MACU:/macu:ro` mount + `N8N_DEFAULT_BINARY_DATA_MODE=filesystem` |

## Sideload an SRT caption track (built 2026-06-11)

Separate workflow: `MACU – YouTube Captions`, id **`RqQV2b9NJqefmTSb`**, webhook path **`macu-youtube-captions`** (active). Two-step YouTube `captions.insert` resumable upload (init → PUT bytes) using the same `YouTube – MACU Report` credential. SRT content goes inline in the JSON body (caption files are small — no `/macu` mount needed):

```bash
python3 - <<'PY'
import json
body = {"videoId": "<VIDEO_ID>", "language": "en", "name": "",
        "srt": open("/path/to/captions.srt").read()}
json.dump(body, open("/tmp/captions.json","w"))
PY
curl -sS -X POST http://localhost:4000/webhook/macu-youtube-captions \
  -H 'Content-Type: application/json' --data @/tmp/captions.json
```

Responds with `{ ok, captionId, videoId, language, status }` — `status: "serving"` means the track is live. `name: ""` makes it the default track; pass a `name` for additional tracks (e.g. localized dubs: `language: "es", name: "Español"`). To replace an existing track, delete the old one in YouTube Studio first (`captions.update` isn't wired).

## Future hooks (not built)

- Playlist add (per-season playlists) — YouTube node `playlistItem:add`.
- True scheduled publish (`publishAt`) — only if August opts out of eyeball-first.
