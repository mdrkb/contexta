---
name: contexta-init
description: Create or update KNOWLEDGE.md at the service repo root. Captures business context, components, architecture patterns, and operational info for contexta's RAG index. Use when the user asks to generate, refresh, or update KNOWLEDGE.md, onboard a service to contexta, or document a service for the team.
---

# contexta-init

Produce or refresh `./KNOWLEDGE.md` at the current repo root. The file follows a fixed H2/H3 structure (see `template.md` in this skill directory) because contexta's downstream indexer chunks on those headings.

Work through the five steps below in order. Keep user-facing text short — this is an interview, not a lecture.

## Step 1 — Preflight

Check whether `./KNOWLEDGE.md` already exists.

- **If absent** → full-generate mode. Announce: "No existing KNOWLEDGE.md found — I'll scrape the repo and then ask you a few questions." Jump to Step 2.
- **If present** → diff-aware mode (the common case for mature repos). Follow the detailed flow below.

### Diff-aware mode

The template has ~27 subsections. The user has already answered most of them in a prior run. The job here is to re-ask as little as possible while still catching stale content.

**1.1 Parse the existing file.** For each H3 subsection, classify its body into one of five states:

| State | Trigger | Default action |
|---|---|---|
| `empty` | Body is blank or only HTML comments | Must re-interview |
| `tbd` | Body is exactly `_TBD_` (case-insensitive, after stripping comments) | Must re-interview |
| `wip` | Body is exactly `_WIP_` | Must re-interview, highlight as in-progress |
| `na` | Body is a single line matching `N/A — …` | Preserve as-is unless user explicitly flags |
| `populated` | Anything else | Preserve unless user flags OR scraping says it's stale |

Keep every heading in place regardless of state — never drop sections.

**1.2 Detect template-schema drift.**

Read `template.md` from this skill directory and compare its H2/H3 heading set against the headings in the user's existing `KNOWLEDGE.md`.

- **Headings only in the template** → the template added new sections since the file was last generated. Add them to the file (with their guide comments and a `_TBD_` body) and route them into the must-refresh set below.
- **Headings only in the file** → the template dropped or renamed a section. **Do not delete** the user's content. Keep the heading in place and surface it to the user: "Template no longer includes `<section>`; the content is preserved but no longer part of the standard structure. Move the content into another subsection, add it to Q/A, or confirm you want it dropped." Default is preserve.
- **Headings in both** → nothing to do here; continue to 1.3.

This step guarantees that evolving `template.md` doesn't orphan existing `KNOWLEDGE.md` files, and that users get a consistent experience when the template grows.

**1.3 Cross-check populated sections against scrape findings (Step 2 output).**

For a small, named set of subsections, the scraper gives you ground truth and should flag drift to the user. The list:

| Subsection | Flag as stale if… |
|---|---|
| `High-level components and workflows / Components` | A top-level directory the file names as a component no longer exists, or a new top-level directory with substantial code isn't mentioned |
| `Interfaces and contracts / Public API` | OpenAPI/proto/CLI entrypoint files have changed shape since the `Last updated` date |
| `Interfaces and contracts / Events published / consumed` | New or removed topic names in config/code |
| `Data / Primary data store` | Database driver dependency changed (e.g. `pg` → `mongo`) |
| `Operational context / Deployment` | Helm chart values or k8s manifests show a different environment/cluster set |
| `Testing / What CI covers` | `.github/workflows/*` or `.gitlab-ci.yml` has new/removed jobs |
| `Lifecycle and status / Maturity` | README or package.json has a `"deprecated": true` or similar signal |

Don't be aggressive — only flag drift when the mismatch is clear. False positives waste the user's turn.

**1.4 Present the plan, then ask.**

Compose one message to the user with four parts:

1. One-line summary: `KNOWLEDGE.md last updated YYYY-MM-DD. 20 subsections populated, 4 _TBD_, 2 N/A, 1 _WIP_, 2 new sections from template, 3 flagged as possibly stale.`
2. **New sections** list (from 1.2) — just announce; these are always re-interviewed.
3. **Must-refresh** list (all `empty`/`tbd`/`wip`, plus any scrape-flagged stale ones). No user input needed on these — just announce.
4. **One AskUserQuestion** with `multiSelect: true` showing the populated subsections, so the user can tick any they want to refresh anyway. Pre-select ones the scraper flagged as stale.

Example message:

> KNOWLEDGE.md last updated 2026-07-14. 20 subsections populated, 4 _TBD_, 2 N/A, 1 _WIP_.
>
> **New sections added by the template since last run:**
> - Testing / What CI covers (and doesn't)
> - Lifecycle and status / Maturity
>
> **I'll re-interview you on these (empty or in-progress):**
> - Interfaces and contracts / Events published / consumed (_TBD_)
> - Data / Retention and PII (_TBD_)
> - Lifecycle and status / Known tech debt (_WIP_)
>
> **I noticed these may be stale (I'll pre-select them in the question below):**
> - Operational context / Deployment — Helm chart now also lists `prod-apac`
> - High-level components / Components — new top-level `pricing/` directory
>
> [Then AskUserQuestion with multiSelect of all populated subsections]

**1.5 Build the work queue.** Combine: new-sections set + must-refresh set + user-ticked set + scrape-flagged set. That's the subsection list Step 3 iterates over. Everything else is preserved verbatim.

## Step 2 — Scrape

Before asking the user anything, extract whatever the repo itself reveals. Read these if they exist (silently skip missing ones):

- `README.md`, `README.*` — service name, high-level purpose, any usage docs
- Package manifests — `package.json`, `pyproject.toml`, `go.mod`, `pom.xml`, `Cargo.toml`, `Gemfile`, `requirements.txt`: language, framework, notable deps
- Container / deploy — `Dockerfile`, `charts/*/values.yaml`, `k8s/**/*.yaml`, `.github/workflows/*`, `.gitlab-ci.yml`: deployment surface, environments, release cadence hints
- Architecture docs — `docs/`, `ADR*`, `architecture*`, `ARCHITECTURE*`: existing decisions, diagrams
- Top-level directory listing — rough component map

Compile a short internal findings list (not shown verbatim to the user) you'll use to pre-fill or cross-reference questions. Example findings:
- "Go service, uses `go-chi` router and `pgx` (Postgres)."
- "Helm chart at `charts/orderapi/` — deploys to `prod-eu`, `prod-us`."
- "ADR 0003 chooses outbox pattern for order events."

## Step 3 — Interview

Load `template.md` from this skill directory for the exact section layout. In **full-generate mode** you'll iterate every subsection; in **diff-aware mode** you only iterate the work queue from Step 1.5.

Walk subsections in template order (not queue order) so the interview feels sequential even when it skips most sections.

- **Lead with what you already know** from scraping. Example: "The repo looks like a Go/Postgres order API deployed via Helm to `prod-eu` and `prod-us`. Is that right for the Deployment subsection, or do you want to adjust?"
- **Prefer AskUserQuestion** when there's a reasonable set of choices (e.g. criticality tier, deployment target). Use free-form follow-ups when the answer is open-ended (why the service exists, notable trade-offs).
- **Always allow skip**. If the owner has no answer for a subsection, write `N/A — <short reason>`. For "I'll come back to this later," write `_WIP_`. Do not fabricate.
- **Keep it tight**. Batch tightly related subsections (e.g. all three Operational subsections) into a single AskUserQuestion with multiple questions.
- **In diff-aware mode specifically**: when re-interviewing a populated subsection the user flagged, *show them the current body first* and ask whether to replace, extend, or keep it. Most "stale" flags end up being "mostly fine but add one line."

For the Business context section — do not try to derive these from code. Ask the user directly. Code can't tell you *why* something exists or *who* depends on it.

For the Q/A section — don't drive it with structured questions. In diff-aware mode, ask: "Are there any new recurring questions worth capturing in Q/A, or any existing entries that are no longer relevant?" Add/remove as free-form H3s.

## Step 4 — Write

1. **Diff-aware mode:** start from the current `./KNOWLEDGE.md` text and *only* replace the bodies of subsections you re-interviewed. Preserve all other content byte-for-byte (whitespace, HTML comments, prose) so `git diff` shows a minimal change.
2. **Full-generate mode:** start from `template.md` in this skill directory.
3. For each subsection in the work queue: replace the old body with the new answer. Keep every heading and HTML comment guide intact. If the user said "N/A" write `N/A — <reason>`; if they said "later" write `_WIP_`.
4. Update the top comment to today's date: `<!-- generated-by: contexta-init skill. Last updated: YYYY-MM-DD -->`.
5. Replace `<REPO_NAME>` in the H1 with the actual repo/service name (from the repo README, package manifest, or user input). On re-runs this is already set — do not touch it unless the user explicitly asks.
6. Write to `./KNOWLEDGE.md` at the repo root.

Do not reorder sections. Do not add new H2s. If the user volunteered information that doesn't fit the schema, note it in the most relevant subsection as prose or add it to Q/A — don't invent a new heading.

## Step 5 — Verify

- Show the user a compact changelog:
  - `Updated: <N>` — subsections whose body changed
  - `Marked N/A: <N>` — subsections the user explicitly skipped
  - `Still _WIP_: <N>` — subsections the user wants to come back to
  - `Preserved: <N>` — subsections touched by neither interview nor scrape
- If this was a re-run, offer to show the full diff of the file.
- Tell the user the next step is **either**:
  - Commit `KNOWLEDGE.md` and wait for the contexta indexer's next sync (once the k8s indexer exists); **or**
  - Push it to contexta now via the `contexta` MCP server — point them at `docs/connect-mcp.md` for the one-line Claude Code prompt.

**Do not suggest any follow-up actions beyond these two.** No "run X separately", no graph refreshes, no reindexing commands — the write path for contexta is `commit` and/or `upsert_knowledge`, nothing else. If an action is not described in this `SKILL.md`, it is not part of this workflow.

## Scope guardrails

- Only touch `./KNOWLEDGE.md`. Do not edit code, docs, or other files during this skill.
- Do not run tests, builds, or deploy commands.
- If the user asks for something outside this scope mid-interview, finish or abort cleanly before switching tasks.