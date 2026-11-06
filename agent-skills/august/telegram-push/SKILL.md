---
name: telegram-push
description: Send a Telegram message to August (chat ID <TELEGRAM_CHAT_ID>) by POSTing to the n8n webhook at <your-n8n-host>. Use when the user asks Claude to "ping me", "text me", "send to telegram", "notify me on my phone", or wants any kind of push notification delivered out-of-band. Also use proactively when a long-running task finishes and the user is likely AFK, or when a critical error/decision needs August's attention right now.
---

# Telegram push to August

Sends a message to August's Telegram chat (`<TELEGRAM_CHAT_ID>`) via an n8n webhook. Single user, single chat — no parameterization.

## How to send a message

1. **Read the secret** from `%USERPROFILE%\.claude\skills\telegram-push\.secret` (single line, no whitespace). If the file is missing or empty, stop and tell August to populate it — don't guess.
2. **POST** to `https://<your-n8n-host>/webhook/claude-telegram` with:
   - Header `X-Webhook-Secret: <the secret>`
   - Header `Content-Type: application/json`
   - Body: `{"text": "<your message>"}`
3. **Expect** HTTP 200 with body `{"ok":true}`. Anything else means it failed — surface the error to August.

## Message formatting

The Telegram node uses `parse_mode: Markdown` (legacy Telegram Markdown, not MarkdownV2):

- `*bold*`, `_italic_`, `` `code` ``, ```` ```block``` ```` work.
- `[label](url)` works.
- `~strikethrough~` and `||spoiler||` do **not** work in this mode.
- Bare `_`, `*`, `` ` `` characters in plain text need to be escaped with `\` or removed, or the message will fail to send.

Keep messages short and useful. Lead with the headline. If you're notifying about a task completing, include the result in one or two lines, not the full output.

## Reference example (bash via curl)

```bash
SECRET="$(cat ~/.claude/skills/telegram-push/.secret)"
curl -sS -X POST https://<your-n8n-host>/webhook/claude-telegram \
  -H "X-Webhook-Secret: $SECRET" \
  -H "Content-Type: application/json" \
  -d '{"text":"*Build done* — green across the board."}'
```

PowerShell equivalent:

```powershell
$secret = Get-Content "$env:USERPROFILE\.claude\skills\telegram-push\.secret" -Raw
$secret = $secret.Trim()
Invoke-RestMethod -Method POST `
  -Uri "https://<your-n8n-host>/webhook/claude-telegram" `
  -Headers @{ "X-Webhook-Secret" = $secret } `
  -ContentType "application/json" `
  -Body '{"text":"*Build done* — green across the board."}'
```

## When NOT to use

- Don't use this for chat replies inside the current Claude conversation — only for genuine push notifications to August's phone.
- Don't fire it on every successful tool call. Reserve it for things August would want to see while away from the computer: long task completions, blocking errors, decisions that need his input.
- Don't send the entire transcript or large blobs. One paragraph max.
