# Running contexta locally

Three containers run alongside each other for local development, all defined in [`compose.yaml`](../compose.yaml) at the repo root:

- **Qdrant** — vector database
- **Ollama** — embedding model runner (local-dev stand-in for TEI in k8s)
- **contexta-mcp** — Python MCP server (chunking + embedding + Qdrant upserts + search)

All three bind to `127.0.0.1` only. No API keys. Nothing on your LAN reaches them.

## Start

```sh
docker compose up -d
```

| Service | Host port | What's on it |
|---|---|---|
| Qdrant | 6333 | REST API + dashboard at http://localhost:6333/dashboard |
| Qdrant | 6334 | gRPC |
| Ollama | 11434 | REST API (`/api/embeddings`, `/api/tags`, …) |
| contexta-mcp | 3333 | MCP streamable-HTTP endpoint at http://localhost:3333/mcp |

To actually use the MCP server from Claude Code, register it once — see [connect-mcp.md](connect-mcp.md).

## One-time: pull the embedding model

The Ollama container starts empty. Pull the model once; it's cached in the `ollama_models` volume afterwards.

```sh
docker exec contexta-ollama ollama pull nomic-embed-text:v1.5
```

This is ~274 MB. The model name and version are pinned to match prod (see `docs/architecture.md`).

## Verify it's up

```sh
# Qdrant
curl -s http://localhost:6333/readyz
# → "all shards are ready"

# Ollama has the model
curl -s http://localhost:11434/api/tags | jq '.models[].name'
# → "nomic-embed-text:v1.5"

# End-to-end: get a 768-dim embedding
curl -s http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text:v1.5","prompt":"hello"}' \
  | jq '.embedding | length'
# → 768
```

## Stop

```sh
docker compose down         # stop, keep volumes
docker compose down -v      # stop AND wipe both qdrant_storage and ollama_models
```

## Logs

```sh
docker compose logs -f qdrant
docker compose logs -f ollama
```

## Data

Two named volumes, both prefixed with the compose project name (`contexta_`):

- `contexta_qdrant_storage` — vectors + payloads
- `contexta_ollama_models` — downloaded model weights

```sh
docker volume ls | grep contexta_
```

To reset just Qdrant without re-downloading the model:

```sh
docker compose rm -sfv qdrant
docker volume rm contexta_qdrant_storage
docker compose up -d qdrant
```

## Dev / prod runner split

Local dev uses **Ollama** (arm64-native, fast on Apple Silicon). Production in k8s uses **TEI** (`ghcr.io/huggingface/text-embeddings-inference`). Both serve the same model weights (`nomic-ai/nomic-embed-text-v1.5`, 768 dim) and produce identical vectors. Downstream services (indexer, MCP server) connect via an `EMBEDDINGS_URL` env var so the runner is swappable.

One caveat: Ollama caps the context at 2k tokens while TEI's default is 8k. For `KNOWLEDGE.md` H3 subsections this is well within bounds, but keep it in mind if you ever embed a whole file at once.

## Upgrading

Edit the image tag in `compose.yaml` and:

```sh
docker compose pull
docker compose up -d
```

Volumes carry over.