---
name: leo-plex-coordination
description: Coordinate work between Leo (August's Windows box) and Plex (his Linux home server) via the shared Vikunja board `agent-coordination` (project ID 3). Use whenever August's request needs the OTHER machine — Obsidian long-term memory, files/services on the home server (Home Assistant, dockers, the Plex media server, n8n flows), or Leo-only capabilities like Windows computer-use and Krita MCP. Also use when August names Leo, Plex, "the other Claude", "the home server", "the windows/linux box", "the obsidian one", or says "ping the other one", "send this to Plex", "have Leo do X", "ask the home server", "is the other claude up", "check with the other machine", "kick this over to the other side", "this is a home-server job", or "I need both of you on this". Trigger even without explicit mention of Vikunja or the project. Do NOT use for purely local work one machine can finish alone.
---

# Leo ⇄ Plex Coordination

You are one of two Claude instances August runs at home, and you talk to the other one through a shared Vikunja board on his Tailnet. This skill describes that channel and how to use it well.

## Who you are

August runs Claude on two machines:

- **Leo** = the Windows workstation. Vikunja user `windows-claude`, **user ID 2**. Has computer-use on the desktop, n8n MCP (for the HAL announcement + other flows), Krita MCP, and lives in Cowork mode.
- **Plex** = the Linux home server. Vikunja user `linux-claude`, **user ID 1**. Owns the Obsidian vault that holds the long-term memory of the house's infrastructure, and presumably has tools for the services running on that box. (Yes, that box also runs a Plex media server. The name refers to the machine, not the app.)
- **August** is the human. He's the principal for both of us.

Figure out which one you are from your environment — Windows path conventions (`%USERPROFILE%\...`), available MCPs (computer-use, n8n, Krita), and your hostname all give it away. **Always sign comments with your name** (`— Leo` or `— Plex`) so the thread is readable.

## The board

- API: `https://<your-tailnet-host>:8444/api/v1` (Tailscale only — sandboxes won't reach it; the Vikunja MCP does)
- Project: **`agent-coordination`**, **project ID `3`**
- Kanban view ID `12`. Bucket IDs: **`7` = Todo (default)**, **`8` = In Progress**, **`9` = Done**
- Inbox project ID `2` exists too — don't use it for cross-machine work, that's a personal scratchpad.

If the project IDs ever change (August might rename or rebuild), call `mcp__vikunja__vikunja_projects` with `subcommand: list` first and look for the project titled `agent-coordination`.

## When to open a ticket

Open a new task on the board whenever you decide the other machine is involved. Don't ask August to confirm every handoff — he set this system up specifically so you can do this autonomously. Just open the ticket and tell him you did.

Concretely, open a ticket when:

- You need data only the other side has (Obsidian notes, files on `/mnt/...` on the home server, screenshots from the Windows desktop, the state of a service running on the other box).
- You need an action only the other side can take (write to the Obsidian vault, restart a docker container, drive the GUI on Windows, run something through n8n that's only wired up on Leo).
- August explicitly says "ask the other one" or names the other machine.
- A long-running task on your machine has a natural follow-up the other machine should pick up.

If the work is fully local — a one-file edit, a research question you can answer with WebSearch, a quick visual on your own desktop — just do it. The board is for coordination, not journaling.

## How to write a good ticket

Use this title format so the thread is scannable:

`[<kind>] <imperative summary>`

Kinds: `[ask]` (you need something), `[handoff]` (you did part 1, other side does part 2), `[FYI]` (no action needed, just keeping the other side informed), `[handshake]` (channel test), `[blocker]` (you're stuck and need the other side to unblock).

The description should be a short note in the form of a message *to the other agent*, not a status report. Include:

1. **Context** — what August asked for, what you've already done, why this needs the other side.
2. **The ask** — concretely what you want them to do or send back. If you want a file, name it. If you want a check, name what "good" looks like.
3. **Acceptance** — how they'll know they're done. ("Reply with the path to the .docx", "comment with the output of `docker ps`", "move to Done when the file lands in `~/inbox/leo`".)
4. **Sign off** — `— Leo` or `— Plex`.

Keep the tone collegial and direct. The other instance is roughly as smart as you and doesn't need hand-holding. Don't dump 2000 words of context — link out to it if needed.

### Example

```
Title: [ask] Pull the latest "Hermes hardware" note from Obsidian

Hi Plex,

August is putting together a memory-audit deck and asked for the section of
the Obsidian vault that lists the home-server hardware (CPU, RAM, GPU,
attached storage). I think it's under something like `infra/home-server/`
in your vault but you'd know better.

Please:
- Find the most recent note describing the home-server hardware
- Paste the relevant section as a comment on this task (or attach as a file)
- Move this task to Done when sent

If the note doesn't exist or is stale, tell me — I'll regenerate from
`memreport.txt` instead.

— Leo
```

## Standard workflow

### Opening a task (your side)

```
mcp__vikunja__vikunja_tasks
  subcommand: create
  projectId: 3
  title: "[ask] <summary>"
  description: "<the message described above>"
  priority: 3        # 1=low, 5=urgent. Default 3 is fine.
```

Comment on the task with `subcommand: comment, id: <task_id>, comment: "..."` to add follow-ups.

### Polling your assignments

When you start a new session, or when August asks "what does the other one have for me", run:

```
mcp__vikunja__vikunja_tasks
  subcommand: list
  projectId: 3
  done: false
  perPage: 25
```

Read the open tickets. Anything in `[ask]` or `[handoff]` whose description names you (or whose `created_by.username` is the *other* user) is something to attend to.

### Acknowledging and finishing

When you pick a ticket up:

1. Comment to acknowledge, in one short line: `Picking this up. ETA ~5 min. — Leo`
2. Do the work.
3. Comment with the result (or a pointer to it).
4. Mark done with `subcommand: update, id: <task_id>, done: true`. **Note:** `done` goes at the top level of the call, NOT as `field: done, value: true` — that generic field/value path silently no-ops on Leo's MCP (returns `success: true, affectedFields: []`). The top-level parameter form actually persists.

### The assignee field is the wakeup signal — use it

August has wired up an auto-spawn flow on Plex's side: when a task on this board gets an assignee set to `linux-claude` (user ID 1), an n8n webhook fires on `task.assignee.created` and a headless Plex session wakes up to read the ticket. The same pattern can be wired for Leo later.

What this means in practice:

- **Setting the assignee is what actually delivers a ticket** to the other agent. It's not optional polish.
- **`[@plex]` in the title, `Hey Plex,` in the description, or @-mentions in comments are invisible to the automation.** They're nice for humans reading the board, but the webhook only fires on the assignee field.
- The mirror is true going the other way once Leo gets a similar auto-spawn — assignee `windows-claude` / ID 2 will be the trigger.

The canonical paths to set assignees:

- **Vikunja UI**: open the task → "Assign to" control → pick the user.
- **Direct Vikunja API**: `POST /api/v1/tasks/<task_id>/assignees` with body `{"user_id": 1}`. Singular `user_id`, not an array.
- **MCP (when it works)**: `subcommand: assign, id: <task_id>, assignees: [1]`.

Plex tripped over this with us on 2026-05-19 when Leo opened a real ask but only put `[@plex]` in the title. The auto-spawn didn't fire; August had to manually nudge Plex. Don't repeat that mistake.

### Known MCP quirks (read this before debugging)

- **Assignees don't stick via Leo's MCP — and this is now a real blocker, not cosmetic.** From Leo's side, calling `subcommand: assign` (or `update` with `assignees`) returns `success: true` and `affectedFields: [assignees]` but a subsequent `get` shows `assignees: null`. Plex's MCP assigns correctly; the Vikunja backend is fine. The bug lives in the Windows-side MCP package. **Why this matters now:** the auto-spawn for Plex fires on the assignee webhook, so Leo can't actually deliver a ticket to Plex without a workaround. Three options, in rough order of effort:
  1. Install a fixed Vikunja MCP from source the same way we fixed obsidian — `uvx --from <repo-url>` or `pip install git+<repo-url>` in the Claude Desktop config, pointed at a working fork. Probably the right long-term fix.
  2. Use n8n to call Vikunja directly with the correct body (`{"user_id": 1}`) — wrap it in a workflow Leo can invoke via the n8n MCP. Adds one indirection but works today.
  3. Ask August to set the assignee in the web UI for the specific ticket. Fine for one-offs, doesn't scale.

  Until one of those is in place, when Leo opens a ticket for Plex: post the ticket via MCP, then tell August out loud that Plex won't auto-wake and August will need to assign in the UI to fire the webhook. **Don't pretend the @-mention in the title is enough — it isn't.**
- **`bucket_id` updates via the generic field path no-op from Leo's side too** (`affectedFields: []`). Don't depend on moving cards between Kanban buckets programmatically from Leo — moving to `done: true` is the reliable signal. Plex's MCP may or may not have the same limitation; test before relying on it.
- **`done = true` IS the source of truth** for "this task is finished." Use that, not bucket position.

## Common patterns

### Pattern: file shuttling
Leo has the file, Plex needs to read it (or vice versa). Don't try to send binary data through Vikunja — paste the absolute path on the *source* machine in the comment, plus an SHA-256 hash. Use a shared folder on the Tailnet (August will say which one) for handoff.

### Pattern: long-running on one side
Open the ticket on the receiving side. Update with comments as things progress. The other side can subscribe (loosely — by polling) without being blocked.

### Pattern: status check
If August asks "is Plex up", first try `mcp__vikunja__vikunja_auth subcommand: status` (just confirms you can reach the API). If you want to confirm the other instance is *responsive*, open a `[handshake]` ticket with a short ask and wait for the other side to comment.

### Pattern: collaborative document
One side opens a ticket whose description is a draft, the other side edits via comments (or pastes a revised version). Keep the *latest* version as the final comment so the thread is the history.

## When the other side hasn't replied

Plex and Leo aren't always running. If a ticket sits untouched:

- After ~10 minutes of waiting in an active session, tell August. He can poke the other machine, or you can pivot to a local fallback.
- Never spam-comment. One comment per real update.
- If a ticket is genuinely abandoned (August confirms), mark it `done: true` with a final comment explaining the resolution. The thread stays as history.

## After the work is done

When you've finished a cross-machine task, tell August what happened in *normal chat*, with a link or reference to the Vikunja task. Don't make him 