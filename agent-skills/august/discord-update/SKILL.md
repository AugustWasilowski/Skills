---
name: discord-update
description: Post an update as Second Shift Augie (August's Discord bot / alter ego) to his private project channel. Use ONLY when August asks for it - "post an update to Discord", "tell Discord", "update voltron", "have Second Shift Augie post this", "drop this in the Discord channel", "send a progress update to Discord". Do not post unprompted.
---

# Discord update via Second Shift Augie

Posts to one fixed channel: **<server> › #<channel>** (`<DISCORD_CHANNEL_ID>`), as the bot **Second_Shift_Augie** (app ID `<DISCORD_APP_ID>`). Single channel, no parameterization.

## How to post

Run the bundled script (Python stdlib only, token is read from `.secret` beside it):

```bash
python ~/.claude/skills/discord-update/post.py "**Build fixed** - the shader cache crash was a stale PSO file. Cleared it, 3 clean runs."
```

Multi-line or long messages: pipe via stdin. The script splits anything over Discord's 2000-char limit on line boundaries.

```bash
python ~/.claude/skills/discord-update/post.py <<'EOF'
**EoA nightly: done**
- 412 textures re-compressed, -1.8 GB
- 3 left flagged NeverStream (list in texture_todo.csv)
EOF
```

Attach screenshots, logs or reports with `--file` (repeatable, max 10, 25 MB each on a non-boosted server):

```bash
python ~/.claude/skills/discord-update/post.py "Before/after on the hero mesh" --file before.png --file after.png
```

Check access without posting anything: `python ~/.claude/skills/discord-update/post.py --check`

On success it prints `Sent N message(s): <jump link>`. Give August that link. On failure it exits non-zero with Discord's error. A 403 means the bot lost access to the channel, so tell August instead of retrying.

## Writing the message

- Lead with a bold one-line headline (`**...**`), then a few bullets at most. It's a status ping, not a transcript.
- Say what project it's about if that isn't obvious from the headline.
- Discord markdown: `**bold**`, `*italic*`, `` `code` ``, ```` ```lang ``` ```` blocks, `> quote`, `- list`, `# heading`, `[label](url)`, `||spoiler||`.
- The script turns off all mentions (`@everyone`, `@here`, roles, users), so nobody gets pinged even if the text contains one.
- Never put secrets, tokens, or `.env` contents in a message. The channel is private, but Discord isn't a vault.
