# Connecting Claude Code to the contexta MCP server

Once the local stack is running (see [run-local.md](run-local.md)), register the MCP server with Claude Code so you can call `search`, `upsert_knowledge`, `list_services`, and `get_chunk` from any chat.

## One-time setup

Pick a scope:

- **User scope** — available in every Claude Code session on your machine. Right for your personal setup.
- **Project scope** — written to `.mcp.json` at the current repo root, committed with the repo. Right if everyone cloning contexta should get the connection automatically.

### User scope (recommended for individuals)

```sh
claude mcp add --scope user --transport http contexta http://localhost:3333/mcp
```

### Project scope (commits a `.mcp.json`)

Run from the contexta repo root:

```sh
claude mcp add --scope project --transport http contexta http://localhost:3333/mcp
```

Then commit the generated `.mcp.json`.

## Verify

```sh
claude mcp list | grep contexta
```

Should print:

```
contexta: http://localhost:3333/mcp (HTTP) - ✓ Connected
```

If you added the server during an already-open Claude Code session, restart Claude Code (or re-open the project) so it rereads the MCP config. Then `/mcp` in Claude Code should show `contexta` with its four tools.

## Troubleshooting

- **Not appearing under `/mcp`** — most likely added to the wrong scope. `claude mcp add` defaults to `--scope local`, which is per-directory. Check with `claude mcp list` from the directory you ran the command in; use `--scope user` to make it global.
- **`✗ Failed to connect`** — the stack isn't running or the port isn't reachable. `docker compose ps` should show `contexta-mcp` healthy on `127.0.0.1:3333`. `curl -s -o /dev/null -w "HTTP %{http_code}\n" -X POST http://localhost:3333/mcp -H 'Content-Type: application/json' -H 'Accept: application/json, text/event-stream' -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"probe","version":"0"}}}'` should return `HTTP 200`.
- **Added to the wrong scope** — `cd` to the directory it was added from, then `claude mcp remove contexta`. Re-add with the right `--scope`.

## Removing

```sh
# For user or project scope — works from any directory:
claude mcp remove --scope user contexta
claude mcp remove --scope project contexta  # from the contexta repo root

# For local scope — must run from the directory it was added from:
claude mcp remove contexta
```

## What it gives you

Once connected, you can ask Claude Code things like:

- *"Use contexta to find out who's on call for order-api."*
- *"Which services does contexta currently have indexed?"*
- *"Read `/path/to/my-service/KNOWLEDGE.md` and upsert it into contexta as repo `my-service`."*

See [how-it-works.md](how-it-works.md) for a walkthrough of what happens under the hood.