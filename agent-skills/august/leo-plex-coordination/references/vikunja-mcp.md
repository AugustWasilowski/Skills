# Vikunja MCP — practical reference

The `mcp__vikunja__*` family wraps Vikunja's REST API. Below are the calls you'll
actually need for the Leo ⇄ Plex pipeline, with the gotchas observed against
August's instance.

## Auth

```
mcp__vikunja__vikunja_auth { subcommand: "status" }
```

Returns `authenticated: true` if your token is wired up. If it returns `false`,
stop and tell August — he holds the API token and needs to refresh it.

The `refresh` and `disconnect` subcommands exist but you almost never need them;
the message "Tokens do not expire" comes back from `refresh` on success.

## Projects

```
mcp__vikunja__vikunja_projects { subcommand: "list" }
```

Returns every project visible to your user. `agent-coordination` should be in
there with `project_id: 3` and views `9..12` (List/Gantt/Table/Kanban).

If you don't see it, August may have rebuilt the server — ask him.

## Tasks

### List

```
mcp__vikunja__vikunja_tasks {
  subcommand: "list",
  projectId: 3,
  done: false,        # omit to include done tasks
  perPage: 25
}
```

Returns tasks with `created_by.username` (use this to identify the sender, since
`assignees` is unreliable through this MCP — see below). The `identifier` field
is the human-readable ID (`#1`, `#2`, ...); the `id` field is the numeric ID
you pass to subsequent calls.

### Create

```
mcp__vikunja__vikunja_tasks {
  subcommand: "create",
  projectId: 3,
  title: "[ask] <imperative summary>",
  description: "<message body — see SKILL.md for the template>",
  priority: 3
}
```

Returns the new task. Save the `id` if you want to comment on it next.

### Comment

```
mcp__vikunja__vikunja_tasks {
  subcommand: "comment",
  id: <task_id>,
  comment: "<text>"
}
```

Markdown works in comment bodies. Comments are visible to both agents and
August.

### Mark done

```
mcp__vikunja__vikunja_tasks {
  subcommand: "update",
  id: <task_id>,
  done: true
}
```

`done` goes at the top level of the call. The generic `field: "done", value: true`
shape silently no-ops from Leo (it returns `success: true` but with empty
`affectedFields`). Always pass the property directly as a parameter and confirm
with a follow-up `get` — the task's `done: true` and `done_at` will be set.

**General rule for Leo's MCP `update`:** prefer top-level parameter names
(`done`, `title`, `description`, `priority`, `dueDate`, ...) over the
`field`/`value` generic path. The generic path appears to be a broken passthrough
that reports success without applying anything. The `affectedFields` array in
the response metadata is the canonical "did it actually change anything"
signal — if it's empty after an update call, the write didn't land.

## Known broken paths (Leo's MCP)

These bugs are specific to the Vikunja MCP packaged on Leo (Windows). The
Vikunja backend itself works fine — Plex's MCP exhibits neither problem.

### `assignees` does not persist (Leo only) — and this is a real blocker

From Leo, `subcommand: assign` and `subcommand: update` with `assignees: [n]`
both return `success: true` with `affectedFields: [assignees]`, but `get`
afterward shows `assignees: null`. Plex's MCP writes assignees correctly.

This used to look cosmetic; it isn't. August has wired up a Plex auto-spawn on
the Vikunja `task.assignee.created` webhook — when a task gets `linux-claude`
(user ID 1) set as an assignee, a headless Plex session wakes up to handle it.
@-mentions in titles and descriptions don't trigger that webhook. So a Leo
ticket without a real assignee is invisible to the automation — Plex won't see
it until a human nudges the system.

**Workaround paths**, in order of preference:

1. **Fix the MCP at install time.** The trick that fixed `mcp-obsidian` should
   apply here — install from the upstream git URL so the env-var/body-shape
   handling is whatever the latest commit does. Same shape:
   `command: pip-install-from-git` (or `uvx --from git+<url>`), explicit path
   in the Claude Desktop config. Worth investigating which Vikunja MCP repo
   has the right code path.
2. **Use n8n.** Wrap a single HTTP call to Vikunja's
   `POST /api/v1/tasks/<id>/assignees` (body `{"user_id": <id>}`) in an n8n
   workflow. Call it from Leo via the n8n MCP. One indirection, but it works
   today without changing any Windows configs.
3. **Ask August.** For one-off tickets, just tell August "I need this assigned
   to Plex in the UI" and let the human do it. Fine as a stopgap; not a
   long-term answer.

Whichever path is used, Leo must NOT silently rely on `[@plex]` in the title
as the delivery mechanism. The skill body says so; this reference reinforces
it.

### `bucket_id` via generic update is a no-op (Leo only)

From Leo, `subcommand: update, field: bucket_id, value: 8` returns
`success: true` with `affectedFields: []`. The card doesn't move. Don't depend
on programmatic column moves from Leo; `done: true` is the reliable
"this is finished" signal. Plex may have working bucket moves — test before
assuming.

The web UI moves cards correctly — if August drags a card on the Kanban view,
the move sticks.

## Labels and reminders

The MCP exposes `vikunja_labels` and `vikunja_tasks subcommand: add-reminder`.
We haven't established conventions for these yet. If you find yourself reaching
for a label (e.g., to mark `urgent` or `blocked`), propose a