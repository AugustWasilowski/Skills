---
name: tasks-summarizer
description: Fetch August's weekly Tech Art work summary from the n8n MCP server (which assembles the summary from Memos using Claude Haiku) and print it back. Use this skill whenever August asks for a weekly summary, a status update, a recap, a "what did I do this week" rollup, a Thursday or Friday summary, a manager update from his log, or anything that implies condensing his recent Tech Art work. Trigger even when he doesn't name Memos or the webhook explicitly — phrases like "summarize my week", "give me a recap", "do my weekly summary", "what have I been working on", "wrap up the week", or "what did I do over the last N days" all count. The skill itself is a thin MCP client; the real work happens server-side.
---

# Tasks Summarizer (v3 — MCP client)

August's daily Tech Art log lives in Memos on his Plex Ubuntu server at `<HOME_SERVER_IP>`. Memos is also reachable from the public n8n instance at `https://<your-n8n-host>` (same Docker network). Two workflows exist there:

- **`Tech Art Weekly Summary`** (id `Qq3XO9KOGyrgbTAy`) — runs on a Friday cron, posts the summary back to Memos as a `#weekly-summary` memo, and announces it in-house via the office HAL display. Also has a webhook trigger at `/webhook/log-summary`, but that workflow has side effects you don't want on every on-demand call. **Don't execute this one via MCP.** The MCP `execute_workflow` call fires the first trigger it finds, which is the cron, which fires the side effects.
- **`Tech Art Summary On-Demand`** (id `<N8N_WORKFLOW_ID>`) — webhook-only, no cron, no Memos-post, no in-house announce. This is the one to call.

**This skill does not parse files.** It calls the on-demand workflow via MCP and prints the response.

## Workflow

### 1. Pick the day count

Default is 7 days. If August specifies a different range, translate it:
- "last 3 days", "past 3 days" → `days: 3`
- "since Monday" → count calendar days back to that Monday inclusive
- "this week" (no other qualifier) → 7
- "last week", "the previous week" → 7 (the server uses rolling-N-days; precision past that is for him to refine)

### 2. Execute via MCP (primary)

```
mcp__n8n-mcp__execute_workflow
  workflowId: <N8N_WORKFLOW_ID>
  executionMode: production
  inputs:
    type: webhook
    webhookData:
      method: POST
      body:
        days: 7
```

The call returns an `executionId` immediately. Then poll:

```
mcp__n8n-mcp__get_execution
  workflowId: <N8N_WORKFLOW_ID>
  executionId: <id>
  includeData: true
  nodeNames: ["Respond to Webhook", "Format Memo Entries"]
```

The summary string is at:

```
data.resultData.runData["Respond to Webhook"][0].data.main[0][0].json.content[0].text
```

`covers` and `memo_count` come from the `Format Memo Entries` node output:

```
data.resultData.runData["Format Memo Entries"][0].data.main[0][0].json.{covers, memo_count}
```

Total round trip is ~3-4 seconds. If `status` is still `running` on first poll, sleep a couple seconds and re-poll.

### 3. Fallback: direct HTTP

If MCP is unavailable, the workflow also responds to direct POST:

```bash
# Windows cmd (escape inner quotes, no single quotes for the body):
curl -sS -X POST https://<your-n8n-host>/webhook/log-summary-ondemand ^
  -H "Content-Type: application/json" -d "{\"days\": 7}"

# bash:
curl -sS -X POST https://<your-n8n-host>/webhook/log-summary-ondemand \
  -H 'Content-Type: application/json' -d '{"days": 7}'
```

Response shape:

```json
{
  "summary": "This week I drove a materials consolidation effort …",
  "covers": "2026-05-09 to 2026-05-16",
  "memo_count": 5
}
```

### 4. Print it back

Format in chat:

```
Week of {{covers}} ({{memo_count}} entries):

{{summary}}
```

That's the whole job. Don't write any files. Don't try to verify against Memos directly — the server-side workflow is the source of truth.

## Error handling

- **MCP returns an auth/credential error from a node.** The workflow's credentials may have been rotated. Open the workflow at `https://<your-n8n-host>/workflow/<N8N_WORKFLOW_ID>` and re-attach the HTTP Header Auth creds on `Fetch Memos` (Memos bearer token) and `Anthropic Summarize` (Anthropic `x-api-key`).
- **Execution status `error` or `crashed`.** Pull `includeData: true` with no `nodeNames` filter and find the failed node. Most likely culprits: the Memos container being down (Fetch Memos errors), or the Anthropic API returning non-200 (rate limit, key expired).
- **`memo_count: 0` in a successful response.** No entries matched in the window. Most likely cause: nothing got tagged `#tech-art` in that range. New manual entries through the Memos UI need `#tech-art` somewhere in the body or the workflow's filter will skip them. Tell August: "Got 0 entries back for the last N days. Check that recent memos in http://<HOME_SERVER_IP>:5230 actually have a `#tech-art` tag in the body."
- **MCP call fails entirely with no executionId.** The n8n MCP server may be down. Fall back to the direct HTTP path in step 3. If that also fails, the n8n instance itself is down.

## Optional: posting a new entry

If August asks to *log* something new (not summarize), the Memos API takes a direct POST. From the LAN:

```bash
curl -sS -X POST http://<HOME_SERVER_IP>:5230/api/v1/memos \
  -H "Authorization: Bearer $MEMOS_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"content": "Some bullet content\n\n#log #tech-art", "visibility": "PRIVATE"}'
```

The token lives on the Plex server at `/opt/memos/.token`. **Don't ask August to paste it into the skill** — that's not what he wants. For now, posting is best done via the Memos web UI.

## Why this design

The skill used to parse `F:\Snail\TechArt\Tasks.txt` directly. Then it called a private LAN webhook at `http://<HOME_SERVER_IP>:4000/webhook/log-summary` — which only worked when August was on his home network, because Cowork's sandbox runs out on the public internet and can't route to RFC1918 addresses.

Final landing: call the workflow directly via the n8n MCP, which is already authenticated and bound to the public n8n at `<your-n8n-host>`. No new HTTP endpoints, no token plumbing, works from anywhere the MCP works. The on-demand workflow is split off from the cron workflow specifically so MCP execution doesn't trigger Friday's side effects (Memos post, HAL announcement).

If something feels wrong about the summary (tone drift, missing themes, links stripped), the fix is in the on-demand workflow's `Anthropic Summarize` system prompt, not here. The cron workflow has its own copy of the prompt — keep them in sync if you change one.
