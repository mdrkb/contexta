# contexta

Shared team context for every service we own, served as a RAG system.

## What this is

Team knowledge about services — why they exist, who uses them, how they're built, where to look during an incident — tends to live in people's heads, Slack threads, and scattered wiki pages. contexta pulls that context into one place.

Each service keeps a `KNOWLEDGE.md` file at its repo root. A scheduled job scrapes those files from every registered repo and indexes them into a vector database (Qdrant). Agents and tools can then query the index to answer questions like "what breaks if the permission-manager goes down?" or "who owns the meta pipeline?".

## Repo layout

```
contexta/
├── compose.yaml          # local Qdrant + Ollama + contexta-mcp
├── mcp-server/           # Python MCP server (upsert_knowledge, search, …)
├── skills/
│   └── contexta-init/    # Claude Code skill that produces KNOWLEDGE.md
└── docs/
    ├── architecture.md     # system design (Qdrant + embedder + MCP + indexer)
    ├── connect-mcp.md      # how to register the MCP server in Claude Code
    ├── how-it-works.md     # end-to-end walkthrough with a worked example
    ├── install-skill.md    # how repo owners install the skill
    ├── run-local.md        # how to run the local stack
    └── decisions/          # ADR-style records of past design decisions
```

The k8s indexer cronjob is planned but not yet in this repo. See `docs/architecture.md`.

## Local development

Start the stack: `docker compose up -d`. On first run, pull the embedding model: `docker exec contexta-ollama ollama pull nomic-embed-text:v1.5`. Qdrant dashboard at http://localhost:6333/dashboard. See [docs/run-local.md](docs/run-local.md) for details. For a step-by-step walkthrough of how data flows through the system, read [docs/how-it-works.md](docs/how-it-works.md).

## Using it from Claude Code

Register the MCP server once:

```sh
claude mcp add --scope user --transport http contexta http://localhost:3333/mcp
```

Then restart Claude Code. See [docs/connect-mcp.md](docs/connect-mcp.md) for scope choices, verification, and troubleshooting.

## For repo owners: generating your KNOWLEDGE.md

See [docs/install-skill.md](docs/install-skill.md). Short version: copy `skills/contexta-init/` into your service's `.claude/skills/`, run `/contexta-init` in Claude Code, commit the generated `KNOWLEDGE.md`.

## Status

Early. The authoring skill, the MCP server, and the local stack work end-to-end. Next: index real services and build the k8s indexer cronjob.