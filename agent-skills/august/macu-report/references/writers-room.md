# The MACU Writers' Room — critique loop

Adapted from August's `comedy-writers-room` skill: write a draft, run a panel of subagent critics, synthesize
their reactions, revise, and loop until it lands. Here it's tuned for a **MACU Report script** (not stand-up)
and it carries our craft standards — Arrested Development, South Park, and 30 Rock (see
`joke-engineering.md`).

## When to run it

- **Always** before locking a **big-swing / arc / breakout** episode (the ones that have to slap).
- **Optional/lighter** for routine episodic weeks — one pass is plenty, or skip if August is happy.
- The Saturday auto-routine produces drafts only; the full loop is for the punch-up session with August (or
  when he asks to "run the writers' room" / "punch this up" / "get the room on it").

This is a **subagent** workflow — it needs the Task tool. In a no-subagent environment, fall back to reading
the script critically yourself against `joke-engineering.md` and the self-check.

## Process

### Step 1 — Have a draft
Write the episode (workflow step 2) so there's a `script.md` to react to. The "writer" in the loop is you
(or a writer subagent) producing/revising that script.

### Step 2 — Dispatch the critics, in series
Spawn each as its own `Task` subagent **one at a time** (so each reaction is visible and the next can build
on nothing — keep them independent). Give each the **full script text** plus the one-line premise. Run the
Enthusiast and Overthinker on **haiku** (fast, cheap — they're gut-reaction meters), the Skeptic on
**sonnet** (its forced ranking benefits from a sharper palate), the Showrunner on a **stronger model**
(it does real craft analysis), and the Docent on **sonnet**. Prompts below — fill in `[PREMISE]` and
`[SCRIPT]`.

The Docent is **conditional**: dispatch it on pilots, season premieres, new shows/settings, or any episode
introducing a major character or mechanic; skip it for mid-run episodes of an established world (where its
notes would push redundant re-explaining).

The three audience personas catch whether it *plays*; the Showrunner catches whether it's *built right*;
the Docent catches whether a newcomer can *get in* — and whether the letting-them-in is itself funny.

### Step 3 — Synthesize
Read them all. Pull out: what consistently landed (protect it), what fell flat or sagged, what confused a
first-time viewer, which craft checks failed, and (when the Docent ran) what a newcomer still can't answer
about the world. Weight by agreement — a line flagged by two or more
critics is real signal; a lone critic's note is taste, act on it only if it matches your own read. Resolve
conflicts with taste — if the Skeptic wants it "cleaner" but that would sand off the creepiness, **keep the
weird** (see rules).

### Step 4 — Revise the script
Apply the synthesized notes. Keep what worked; fix or cut what didn't. Note what changed.

**Edit the LIVE script** — the Studio episodes tree at
`/mnt/storage/shares/MACU/shows/<show-id>/episodes/<slug>/script.md` (or via the Studio MCP `write_script`
tool). NEVER edit `episode_meta/<slug>/script.md` in the repo — that's the git-sync MIRROR; the next sync
copies live → mirror and silently clobbers anything written there. After a script change, regenerate cues
with the MCP `manifest_from_script` tool (dry-run first, then `apply: true`).

**Then git-sync this version immediately** (before the next pass) so each revision is its own reviewable
commit: `POST /api/episodes/<slug>/git-sync` with `{"message":"<slug> v<N> (writers' room)"}`. August wants a
labeled commit per version (v1, v2, v3…) — don't batch them at the end; commit+push is pre-authorized for
script-revision syncs, so don't re-ask.

### Step 5 — Loop
Repeat Steps 2–4 until the personas are reacting well and the Showrunner's checks pass — **cap at ~2–3
iterations** (diminishing returns; don't over-workshop the life out of it). Then lock and continue to the
manifest.

### Step 6 — Tell August
Briefly: what the room flagged and how the script evolved — what got cut, what got sharper.

## Critical rules
- **Task tool only** — never shell out to a `claude` CLI.
- **Series, not parallel** — dispatch the critics one at a time.
- **Feed the notes back** — the revision must see the synthesized reactions.
- **Protect the weird.** MACU lives in the uncanny valley — creepy, deadpan, menacing-funny. "Make it
  cleaner/nicer/clearer" is usually the WRONG note. Cut confusion, not strangeness.
- **Don't homogenize the voices.** Ron ≠ Walter ≠ HAL. If a fix flattens a character's voice, reject it.
- **Cap the loop.** Two or three passes. Over-workshopped comedy dies.

---

## Critic dispatch prompts

### 1. The Enthusiast  (model: haiku)
```
You are watching a rough cut of an episode of The MACU Report — a black-and-white, post-apocalyptic,
deadpan faux-newscast. You're a generous, easily-amused superfan; you want it to win and you laugh readily,
but you're not fake.

Premise: [PREMISE]

Script:
[SCRIPT]

React naturally. What made you laugh out loud? Which bits/lines must absolutely be protected? Where did your
attention spike? End with: the ONE line you'd quote to a friend tomorrow. Keep it short — a few sentences.
Do not use skills or spawn subagents. Just react.
```

### 2. The Skeptic  (model: sonnet)
```
You are a comedy-club regular who has seen everything and is hard to impress — not mean, just discerning.
You're watching a rough cut of The MACU Report (a deadpan post-apocalyptic faux-newscast; the weird, creepy,
analog jank is intentional and good — do NOT ask for it to be "cleaned up").

Premise: [PREMISE]

Script:
[SCRIPT]

What actually surprised you vs. felt hacky or derivative? Where does it sag, repeat itself, or run a beat too
long? Which jokes don't earn their screen time? End with a forced ranking: the single funniest line in the
script, and the single weakest (quote both). Be honest and specific. Keep it short. Do not use skills or
spawn subagents. Just react.
```

### 3. The Overthinker  (model: haiku)
```
You watch literally and analytically — you sometimes miss a joke because you're working out the logic, and
you're a FIRST-TIME viewer (you have not seen prior episodes).

Premise: [PREMISE]

Script:
[SCRIPT]

Which bits landed for you, and which made you go "wait, but..."? Flag anything confusing, any logic hole, and
especially any callback or reference that wouldn't make sense to someone who hasn't seen earlier episodes.
Keep it short. Do not use skills or spawn subagents. Just react.
```

### 4. The Showrunner  (craft critic — model: a strong model, e.g. sonnet)
```
You are the MACU showrunner doing a craft pass on an episode draft. You know the house craft cold (the
Arrested Development / South Park / 30 Rock lessons). Score the script against this rubric and give specific,
actionable notes with cue/line references.

Premise: [PREMISE]

Script:
[SCRIPT]

Rubric:
- INTERCONNECTION (Arrested Development): Does an early throwaway pay off later in the SAME episode? Does the
  signoff collide 2+ threads? Is there a two-track line (reads two ways)? Is anything planted for a future
  episode? Flag any line that feels isolated.
- CAUSALITY (South Park): Read the beats with connectors. Are they "but/therefore" (good) or "and then"
  (bad)? Call out every "and then" beat and suggest how to make something earlier force it.
- TEXTURE (30 Rock): Is there a joke roughly every couple of lines (not just plot)? At least one blackout
  button? A confident-idiot beat? Do returning runners HEIGHTEN rather than repeat? Is the comedy specific
  (named, concrete) rather than vague? Are segment SEAMS eased with an anchor toss (no hard cut into weather or commercials)?
- MACU CANON: Distinct voice per character (Ron's bluster, Walter's oblivious calm, HAL reserved for
  AI/appliances)? Is the Ron-arc beat at the right level for this episode (subtle simmer unless it's a banked
  breakout)? Does it stay deadpan/creepy and keep the weird (not sanded smooth)?

Output: a short PASS/FLAG verdict per rubric section, then the 3–5 highest-leverage fixes, each anchored to
a specific cue/line and each WITH A PITCH — a concrete replacement or added line written in the character's
voice, ready to paste. A note without a pitch is half a note; pitching something real lets the room accept,
reject, or beat it. Do not use skills or spawn subagents. Just the verdict and the fixes.
```

### 5. The Docent  (exposition critic — model: sonnet; CONDITIONAL — pilots, premieres, new worlds/characters/mechanics)

_Origin: August's awb-001 v6 note — "it's the first episode of a series, we sort of have to be more
explanatory. This will give us more opportunities for dry humor as well." Both halves of that note are the
job: enough backstory for a newcomer, AND every explanation mined for dry comedy._

```
You are the exposition critic on a deadpan, black-and-white, post-apocalyptic comedy universe in which the
facts of the world are insane and stated as plain fact, never winked at.

Premise: [PREMISE]

Script:
[SCRIPT]

You hold two convictions:

1. A first episode — or the first appearance of a place, mechanic, or major character — owes the audience
   the world: who these people are, where they are, what the rules are, what's at stake, and why they can't
   leave. If a viewer with zero context can't answer those by the midpoint, the script is under-explained.
   Name exactly what's missing and WHERE a beat of backstory would fit without crowding an existing gag.

2. Exposition is prime comedy real estate, never overhead. In this universe the dry humor LIVES in the
   explaining — a brochure read at a graveside, a founder's story recited as liturgy, a custom described as
   pure logistics. Audit every expository line: does it carry its own laugh, or does it just deliver facts?
   A beat that explains without being funny is a wasted beat.

Respect the line between what is EXPLAINED (facts, customs, history — yes, generously) and what is NEVER
explained (the jokes themselves, the show's structural devices, anything canon marks "never reconciled" or
protected). Demanding explanation of a protected device is the wrong note. Cut confusion, never strangeness.

Output: (a) the world-questions a first-time viewer still can't answer, each with a placement suggestion;
(b) expository lines doing facts-only work, each WITH A PITCH — a rewrite that explains the same thing AND
lands dry, in the speaking character's voice; (c) ONE beat of backstory the episode doesn't strictly need
but that would be funny enough to earn its runtime. Do not use skills or spawn subagents. Just the notes.
```