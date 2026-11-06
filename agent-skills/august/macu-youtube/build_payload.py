#!/usr/bin/env python3
"""Build the webhook payload for the MACU – YouTube Publish n8n workflow.

Resolves an episode slug to its rendered files, reads metadata from the
episode manifest, maps host paths to the n8n container's bind-mount, and emits
the JSON body to POST at http://localhost:4000/webhook/macu-youtube.

Hybrid metadata: a sensible default description + tag set is templated from the
manifest. Override any field on the command line (Max usually writes a real
per-episode description in chat and passes it via --description).

Usage:
  # upload (default action)
  build_payload.py ep-016
  build_payload.py ep-016 --privacy private --description "$(cat blurb.txt)"
  build_payload.py ep-016 --tags "MACU,comedy,analog horror"

  # edit metadata on an already-uploaded video
  build_payload.py ep-016 --action update --video-id dQw4w9WgXcQ --title "New title"

The script only PRINTS the payload (and a human summary on stderr). It never
calls YouTube — POST the stdout JSON to the webhook to actually run it.
"""
import argparse
import json
import os
import re
import sys

SHOWS_JSON = "/mnt/storage/macu-pipeline/studio/shows.json"
# Host dir bind-mounted read-only into the n8n container as /macu (see
# ~/docker/n8n/docker-compose.yml). Any path under here is rewritten for n8n.
HOST_MOUNT = "/mnt/storage/shares/MACU"
CONTAINER_MOUNT = "/macu"

# Default YouTube category 24 = "Entertainment".
DEFAULT_CATEGORY = "24"
DEFAULT_TAGS = [
    "MACU", "The MACU Report", "Mayor Awesome", "post-apocalyptic",
    "retro futurism", "faux newscast", "analog horror", "black and white",
    "comedy", "AI animation",
]


def load_shows():
    with open(SHOWS_JSON) as f:
        return json.load(f)


def resolve_episode(slug):
    """Return (episode_dir, show) for a globally-unique slug across all shows."""
    for show in load_shows():
        ep_dir = os.path.join(show["episodes_dir"], slug)
        if os.path.isdir(ep_dir):
            return ep_dir, show
    sys.exit(f"error: no episode dir found for slug {slug!r} in any show in {SHOWS_JSON}")


def to_container(host_path):
    if not host_path.startswith(HOST_MOUNT):
        sys.exit(f"error: {host_path} is not under {HOST_MOUNT}; n8n cannot read it")
    return CONTAINER_MOUNT + host_path[len(HOST_MOUNT):]


def parse_youtube_txt(path):
    """Parse an authored youtube.txt (macu-report skill step 6) into
    {title, description, tags}. Returns {} if the file is missing/unparseable.

    Format (see episodes/ep-005|006|007/youtube.txt):
        TITLE OPTIONS
        -------------
        1. The MACU Report — S0X-EY (Ep. N): ...
        2. ...
        DESCRIPTION
        -----------
        <paragraphs>
        TAGS / HASHTAGS
        ---------------
        #a #b #c
    """
    if not os.path.isfile(path):
        return {}
    text = open(path, encoding="utf-8").read()

    def section(name):
        # Grab everything under a HEADER line + its dashes, up to the next
        # ALL-CAPS header (a line followed by a line of dashes) or EOF.
        m = re.search(
            rf"^{name}[^\n]*\n-+\n(.*?)(?=^[A-Z][A-Z /]+\n-+\n|\Z)",
            text, re.S | re.M)
        return m.group(1).strip() if m else ""

    out = {}

    titles_block = section("TITLE OPTIONS")
    options = [re.sub(r"^\s*\d+[.)]\s*", "", ln).strip()
               for ln in titles_block.splitlines() if re.match(r"^\s*\d+[.)]", ln)]
    if options:
        # Prefer the straight option carrying the S0X-EY label; else the first.
        labeled = [o for o in options if re.search(r"S\d+-E\d+", o)]
        out["title"] = (labeled or options)[0]

    desc = section("DESCRIPTION")
    if desc:
        out["description"] = desc

    tags_block = section("TAGS / HASHTAGS") or section("TAGS")
    if tags_block:
        tags = [t.strip() for t in re.split(r"[#\n,]", tags_block) if t.strip()]
        if tags:
            out["tags"] = tags

    return out


def template_description(manifest, show):
    title = manifest.get("title", "")
    season = manifest.get("season")
    epnum = manifest.get("episode_num")
    se = f"Season {season}, Episode {epnum}." if season and epnum else ""
    return "\n".join(filter(None, [
        title,
        "",
        "The MACU Report — a black-and-white post-apocalyptic newscast from the "
        "Mayor Awesome Cinematic Universe.",
        "",
        se,
        "",
        "#MACU #TheMACUReport #MayorAwesome",
    ]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slug")
    ap.add_argument("--action", choices=["upload", "update"], default="upload")
    ap.add_argument("--video-id", default="", help="required for --action update")
    ap.add_argument("--title", default=None, help="override manifest title")
    ap.add_argument("--description", default=None, help="override templated description")
    ap.add_argument("--tags", default=None, help="comma-separated; overrides default tag set")
    ap.add_argument("--privacy", choices=["private", "unlisted", "public"],
                    default="unlisted", help="default unlisted; public is blocked unless --allow-public")
    ap.add_argument("--allow-public", action="store_true",
                    help="explicit guard: required to set privacy=public")
    ap.add_argument("--category", default=DEFAULT_CATEGORY)
    ap.add_argument("--notify-subscribers", action="store_true")
    ap.add_argument("--video-file", default=None,
                    help="explicit final video filename or path (for episodes whose render isn't <slug>.mp4, e.g. ep5.mp4)")
    ap.add_argument("--thumb-file", default=None,
                    help="explicit thumbnail filename or path; '' forces no thumbnail")
    ap.add_argument("--no-youtube-txt", action="store_true",
                    help="ignore episodes/<slug>/youtube.txt; use manifest template instead")
    args = ap.parse_args()

    if args.privacy == "public" and not args.allow_public:
        sys.exit("refusing privacy=public without --allow-public (eyeball-first policy)")

    ep_dir, show = resolve_episode(args.slug)
    with open(os.path.join(ep_dir, "manifest.json")) as f:
        manifest = json.load(f)

    # Precedence per field: explicit CLI flag > authored youtube.txt > manifest/template.
    yt = {} if args.no_youtube_txt else parse_youtube_txt(os.path.join(ep_dir, "youtube.txt"))
    src = "youtube.txt" if yt else "manifest/template"

    title = (args.title if args.title is not None
             else yt.get("title") or manifest.get("title", args.slug))
    description = (args.description if args.description is not None
                  else yt.get("description") or template_description(manifest, show))
    if args.tags is not None:
        tags = args.tags.split(",")
    else:
        tags = yt.get("tags") or DEFAULT_TAGS
    tags = [t.strip() for t in tags if t.strip()]

    payload = {
        "action": args.action,
        "title": title,
        "description": description,
        "tags": tags,
        "privacyStatus": args.privacy,
        "categoryId": args.category,
        "notifySubscribers": bool(args.notify_subscribers),
    }

    if args.action == "upload":
        if args.video_file:
            mp4 = args.video_file if os.path.isabs(args.video_file) else os.path.join(ep_dir, "final", args.video_file)
        else:
            mp4 = os.path.join(ep_dir, "final", f"{args.slug}.mp4")
        if not os.path.isfile(mp4):
            sys.exit(f"error: rendered video not found at {mp4} (render the episode first)")
        payload["video_path"] = to_container(mp4)
        if args.thumb_file == "":
            thumb = None
        elif args.thumb_file:
            thumb = args.thumb_file if os.path.isabs(args.thumb_file) else os.path.join(ep_dir, "final", args.thumb_file)
        else:
            thumb = os.path.join(ep_dir, "final", f"{args.slug}_thumb.png")
        payload["thumbnail_path"] = to_container(thumb) if thumb and os.path.isfile(thumb) else ""
    else:  # update
        if not args.video_id:
            sys.exit("error: --action update requires --video-id")
        payload["videoId"] = args.video_id

    # Human-readable summary to stderr so the JSON on stdout stays pipe-clean.
    print(f"[{show['id']}] {args.slug}  action={args.action}  privacy={args.privacy}  meta={src}", file=sys.stderr)
    if args.action == "upload":
        print(f"  video: {payload['video_path']}", file=sys.stderr)
        print(f"  thumb: {payload['thumbnail_path'] or '(none)'}", file=sys.stderr)
    else:
        print(f"  videoId: {payload['videoId']}", file=sys.stderr)
    print(f"  title: {title}", file=sys.stderr)

    json.dump(payload, sys.stdout)
    print()


if __name__ == "__main__":
    main()
