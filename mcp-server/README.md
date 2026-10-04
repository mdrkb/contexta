# contexta-mcp

MCP server for contexta. Ingests `KNOWLEDGE.md` files into Qdrant and serves semantic search.

## Tools

| Tool | Purpose |
|---|---|
| `upsert_knowledge(repo, repo_url, git_sha, markdown)` | Chunk a `KNOWLEDGE.md` by H3, embed each chunk, upsert to Qdrant. Idempotent. |
| `search(query, repo?, section?, limit?)` | Semantic search over indexed chunks with optional payload filters. |
| `list_services()` | Distinct `repo` values currently indexed. |
| `get_chunk(id)` | Fetch a single chunk by its point ID. |

## Env

| Var | Default | Purpose |
|---|---|---|
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant REST endpoint |
| `EMBEDDINGS_API` | `ollama` | `ollama` or `tei` |
| `EMBEDDINGS_URL` | `http://ollama:11434` | Embedder endpoint |
| `EMBEDDINGS_MODEL` | `nomic-embed-text:v1.5` | Model name — must match prod |
| `COLLECTION` | `knowledge` | Qdrant collection name |
| `VECTOR_SIZE` | `768` | Embedding dimension |
| `SEARCH_DEFAULT_LIMIT` | `5` | Default top-N for `search` when the caller omits `limit` |
| `MCP_HOST` | `0.0.0.0` | Listen host |
| `MCP_PORT` | `3333` | Listen port |

## Run locally (dev)

```sh
docker compose up -d contexta-mcp
```

The MCP endpoint is at `http://localhost:3333/mcp`. The simplest way to connect Claude Code is:

```sh
claude mcp add --scope user --transport http contexta http://localhost:3333/mcp
```

Or, by editing MCP config directly:

```json
{
  "mcpServers": {
    "contexta": { "type": "http", "url": "http://localhost:3333/mcp" }
  }
}
```

## Tests

```sh
cd mcp-server
pip install -e '.[dev]'
pytest
```