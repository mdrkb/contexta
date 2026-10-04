# KNOWLEDGE: <REPO_NAME>

<!-- generated-by: contexta-init skill. Last updated: <YYYY-MM-DD> -->

<!--
This file is consumed by contexta's RAG indexer. Keep the H2/H3 heading
structure below exactly as-is — the indexer chunks on these headings and
attaches them as metadata for filtered retrieval. Free-form prose inside
each subsection is fine; add bullet lists where they fit naturally.

If a subsection genuinely does not apply, replace its placeholder with a
one-line `N/A — <reason>`. Do not delete the heading. Use `_WIP_` for
subsections you intend to fill in soon so re-runs of the skill can flag
them.
-->

## Business context

### Why this exists
<!-- The business or technical problem this repo solves. What would be
missing or broken without it? Avoid implementation detail — focus on the
outcome. -->
_TBD_

### Impact if it breaks
<!-- Blast radius when the repo's output is unavailable or broken: which
user flows stop working, which downstream systems stall, revenue/SLA
exposure. For libraries: which services would be unable to ship. -->
_TBD_

### Who uses it
<!-- Direct consumers (teams, services, external customers) and, if
known, approximate volume or criticality tier. -->
_TBD_

## Getting started

### Local setup and smoke test
<!-- The one command (or short sequence) that tells a new contributor
their environment works end-to-end. Include approximate time to green.
This complements the README, which has install steps — this is the
"am I set up correctly?" check. -->
_TBD_

### Common pitfalls on first run
<!-- The things that always trip people up: VPN requirements, missing
env vars, platform-specific gotchas, order-of-operations surprises. -->
_TBD_

## High-level components and workflows

### Components
<!-- The main internal modules/services and what each is responsible
for. One or two sentences per component. Include external systems this
repo depends on (DBs, queues, third-party APIs). -->
_TBD_

### Key workflows
<!-- The 2–5 most important end-to-end flows, described conceptually
(not as code paths). Example format: "**User signup**: request hits API
→ validation → user row created → welcome email queued." -->
_TBD_

## Interfaces and contracts

### Public API
<!-- The API this repo exposes: HTTP routes, gRPC services, CLI
surface, exported library symbols. Link to generated docs or schema
files; don't try to recreate them. State stability guarantees (v1
frozen, v2 evolving, etc.). -->
_TBD_

### Consumed APIs
<!-- External/internal APIs this repo calls, and what it needs from
each. Links to those services' KNOWLEDGE.md where helpful. -->
_TBD_

### Events published / consumed
<!-- Message-bus or event-stream contracts: what this repo emits, what
it listens for. Topic names, schema registry pointers, delivery
guarantees. -->
_TBD_

## Data

### Primary data store
<!-- Where state lives: database/cluster name, environment, approximate
size. One line is often enough. -->
_TBD_

### Schema overview
<!-- A 10-foot view of the main tables/collections and their roles.
Link to the authoritative schema source; do not duplicate it here. -->
_TBD_

### Retention and PII
<!-- What personal/sensitive data is stored, retention windows, legal
or compliance drivers (GDPR, SOX, internal policy). -->
_TBD_

## Architecture patterns and decisions

### Patterns in use
<!-- Architectural patterns applied in this codebase (event-driven,
CQRS, hexagonal, saga, etc.) and where they show up. Only patterns
that would help a new engineer orient — skip generic things like
"we use HTTP". -->
_TBD_

### Notable decisions / trade-offs
<!-- Decisions that are non-obvious from the code and would surprise a
reader. Include the trade-off accepted. Link to ADRs if they exist.
Example: "We chose eventual consistency for the inventory read model
to keep writes fast; stale reads up to 5s are acceptable per
product." -->
_TBD_

## Testing

### How to test locally
<!-- Commands to run unit, integration, and e2e tests locally. What
each tier covers. Which require external services (Docker, test
accounts). -->
_TBD_

### What CI covers (and doesn't)
<!-- The actual guarantees CI provides on PRs: which tests run, which
only run on main or on deploy, what performance/security scans fire.
Equally important: what CI does *not* check. -->
_TBD_

## Operational context

### Deployment
<!-- Where this runs (cluster/region/environment), how it's deployed
(Helm chart path, CI pipeline, release cadence), notable config
toggles. -->
_TBD_

### Dashboards and runbooks
<!-- Links to primary dashboards (Grafana, Datadog, etc.) and
runbooks. One line per link with what it's for. -->
_TBD_

### On-call
<!-- Owning team, on-call rotation (PagerDuty schedule, Slack
channel), escalation path. -->
_TBD_

## Ownership and contacts

### Primary and secondary owners
<!-- Who owns this repo day-to-day. Teams or individuals; include
backup. Code review authority lives here if it differs from the
on-call team. -->
_TBD_

### Specific contacts
<!-- Who to ask about specific concerns: security sign-off, API
deprecation decisions, legal/compliance, SRE escalation. Only list
contacts that differ from the primary owner. -->
_TBD_

## Gotchas and tribal knowledge

### Footguns
<!-- The dangerous things: destructive commands, order-of-operations
traps, data that looks safe to touch but isn't. Example: "`make
clean` also wipes the local test DB — use `make clean-build`
instead." -->
_TBD_

### Weird-looking things that are actually fine
<!-- Code or structure that looks dead, redundant, or wrong but is
intentional. Saves future readers from "cleaning up" something
load-bearing. Example: "The `pricing_engine_v2/` directory looks
unused but is still called from `jobs/overnight/`." -->
_TBD_

## Lifecycle and status

### Maturity
<!-- Experimental / stable / mature / deprecated. If deprecated,
name the replacement and the sunset timeline. -->
_TBD_

### Known tech debt
<!-- The 2–5 largest known debt items an engineer should be aware of
before building on this. Not an exhaustive backlog — just the shape
of the biggest rocks. -->
_TBD_

## Related services and docs

### Upstream
<!-- Repos/services this one depends on. Short reason for each
dependency. -->
_TBD_

### Downstream
<!-- Repos/services that depend on this one. Helps gauge blast radius
when planning changes. -->
_TBD_

### Design docs and ADRs
<!-- Links to the authoritative design docs, ADRs, RFCs, or wiki
pages that go deeper than this file does. One line per link with
what it covers. -->
_TBD_

## Q/A

<!--
Free-form question-and-answer entries for information that doesn't
fit the structured sections above but comes up often enough to be
worth capturing. Format each entry as:

### <The question as someone would actually ask it>
<The answer, in a sentence or two. Link out when the full answer
is somewhere else.>

Keep questions phrased as questions — they embed better for
retrieval because real users phrase queries the same way. Prune
answered-and-no-longer-relevant entries during re-runs of the
skill.
-->

### <Example: Why can't I build this on an M1 Mac?>
_TBD_
