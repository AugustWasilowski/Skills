"""Post a message as Second Shift Augie to August's private Discord channel.

Usage:
    python post.py "message text"
    echo "message text" | python post.py
    python post.py "caption" --file screenshot.png [--file log.txt]
    python post.py --check          # verify token + channel access, posts nothing

Stdlib only. Reads the bot token from .secret next to this file.
"""
import argparse, json, mimetypes, os, sys, urllib.error, urllib.request, uuid

CHANNEL_ID = "<DISCORD_CHANNEL_ID>"  # <server> / #<channel>
API = "https://discord.com/api/v10"
LIMIT = 2000  # Discord's per-message character cap
HERE = os.path.dirname(os.path.abspath(__file__))


def token():
    path = os.path.join(HERE, ".secret")
    try:
        tok = open(path, encoding="utf-8").read().strip()
    except FileNotFoundError:
        tok = ""
    if not tok:
        sys.exit(f"No bot token in {path}")
    return tok


def call(method, path, body=None, content_type="application/json"):
    req = urllib.request.Request(API + path, data=body, method=method, headers={
        "Authorization": f"Bot {token()}",
        "User-Agent": "DiscordBot (https://claude.com, 1.0)",
        **({"Content-Type": content_type} if body is not None else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        hint = ""
        if e.code == 403:
            hint = ("\nThe bot can't see or post in that channel. In Discord: channel settings > "
                    "Permissions > add Second_Shift_Augie with View Channel, Send Messages, Attach Files.")
        sys.exit(f"Discord API {e.code}: {detail}{hint}")


def chunks(text):
    """Split on line boundaries so each piece fits Discord's 2000-char limit."""
    out, cur = [], ""
    for line in text.splitlines(keepends=True):
        while len(line) > LIMIT:
            if cur:
                out.append(cur); cur = ""
            out.append(line[:LIMIT]); line = line[LIMIT:]
        if len(cur) + len(line) > LIMIT:
            out.append(cur); cur = ""
        cur += line
    if cur.strip():
        out.append(cur)
    return out


def payload(content):
    # Never ping anyone: no @everyone, @here, role or user mentions.
    return {"content": content, "allowed_mentions": {"parse": []}}


def send_text(content):
    return call("POST", f"/channels/{CHANNEL_ID}/messages", json.dumps(payload(content)).encode())


def send_files(content, files):
    boundary = uuid.uuid4().hex
    parts = [(f'--{boundary}\r\nContent-Disposition: form-data; name="payload_json"\r\n'
              f"Content-Type: application/json\r\n\r\n{json.dumps(payload(content))}\r\n").encode()]
    for i, path in enumerate(files):
        name = os.path.basename(path)
        ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="files[{i}]"; '
                      f'filename="{name}"\r\nContent-Type: {ctype}\r\n\r\n').encode())
        parts.append(open(path, "rb").read() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    return call("POST", f"/channels/{CHANNEL_ID}/messages", b"".join(parts),
                f"multipart/form-data; boundary={boundary}")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="message text (otherwise read from stdin)")
    ap.add_argument("--file", action="append", default=[], help="attach a file (repeatable, 10 max)")
    ap.add_argument("--check", action="store_true", help="verify access without posting")
    args = ap.parse_args()

    if args.check:
        me = call("GET", "/users/@me")
        ch = call("GET", f"/channels/{CHANNEL_ID}")
        print(f"OK: {me['username']} can see #{ch['name']} ({CHANNEL_ID})")
        return

    text = args.text if args.text is not None else sys.stdin.read()
    text = text.strip()
    if not text and not args.file:
        sys.exit("Nothing to send.")

    pieces = chunks(text) or [""]
    msgs = [send_text(p) for p in pieces[:-1]]
    msgs.append(send_files(pieces[-1], args.file) if args.file else send_text(pieces[-1]))
    guild = "<DISCORD_GUILD_ID>"
    print(f"Sent {len(msgs)} message(s): https://discord.com/channels/{guild}/{CHANNEL_ID}/{msgs[-1]['id']}")


if __name__ == "__main__":
    main()
