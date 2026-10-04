# 0001 — `contexta-mcp` server design

**Status**: Implemented 2026-10-03. This records the design decisions made *before* building the server; it is **not** the current source of truth. For current state see:

- [`architecture.md`](../architecture.md) — system shape
- [`how-it-works.md`](../how-it-works.md) — end-to-end walkthrough
- [`../../mcp-server/README.md`](../../mcp-server/README.md) — live env vars and tool docs
- [`../../compose.yaml`](../../compose.yaml) — live service wiring

## Context

Qdrant and Ollama are running in `compose.yaml` and produce 768-dim vectors. The next piece is the thing that actually puts data into Qdrant and gets semantic search out of it: a Python MCP server at `contexta/mcp-server/`.

Building the MCP server **before** the k8s indexer gives us two things:

1. The indexer becomes a thin loop that calls one HTTP tool — no chunking/embedding duplicated in two places.
2. We can manually index one KNOWLEDGE.md and query it from Claude Code, validating the whole stack (chunking → embedding → Qdrant → retrieval), before writing any k8s YAML.

## Decisions (locked in questions above)

| | |
|---|---|
| Language | Python |
| MCP transport | HTTP/SSE only (same binary everywhere, pointed at a URL from Claude Code) |
| How `upsert_knowledge` receives files | Caller passes markdown + metadata; server never touches git |
| Qdrant collection | Auto-create on startup if missing (idempotent) |
| Embedder adapter | Explicit `EMBEDDINGS_API=ollama\|tei` + `EMBEDDINGS_URL` env vars |
| Repo layout | Subfolder: `contexta/mcp-server/` |

## MCP tools (v0 surface)

Build order top to bottom:

1. **`upsert_knowledge(repo, repo_url, git_sha, markdown)`** — chunks by H3, embeds each chunk, upserts to Qdrant. Replaces all points with matching `(repo, subsection)` so updates are idempotent and removed subsections don't orphan points.
2. **`search(query, repo=None, section=None, limit=5)`** — embeds query, nearest-neighbor in Qdrant with optional payload filters, returns chunks (payload + similarity score).
3. **`list_services()`** — distinct `payload.repo` currently indexed.
4. **`get_chunk(id)`** — fetch one point by ID.

(1) and (2) are the critical path. (3) and (4) are polish; cheap once the plumbing exists.

## Repo layout

The server lives at `mcp-server/` as a subfolder of the main contexta repo (not a separate repo, not under `.claude/`). See the live tree for current structure.

## Component sketches

### `embeddings.py` — Embedder adapter

Thin class, one method:

```python
class Embedder:
    def __init__(self, api: Literal["ollama", "tei"], url: str, model: str): ...
    async def embed(self, texts: list[str]) -> list[list[float]]: ...
```

Internals: on `api == "ollama"`, POST to `{url}/api/embeddings` once per text (Ollama doesn't batch), returns `.embedding`. On `api == "tei"`, POST to `{url}/embed` with `{"inputs": [...]}` once, returns the whole batch. Normalize nothing — Qdrant cosine distance normalizes internally. Tests mock `httpx.AsyncClient` and assert the request body + response parsing for each API.

### `chunker.py` — H3 chunker

Input: markdown string. Output: `list[Chunk]` where `Chunk = {section: str, subsection: str, text: str}`.

Algorithm:
1. Parse markdown with a minimal walker (no external parser needed — split on `\n## ` and `\n### ` with care for code fences; or use `markdown-it-py` if the regex gets gnarly).
2. Walk H2 → H3 pairs. Each H3 produces one chunk whose `section` is the parent H2 title, `subsection` is the H3 title, `text` is everything from the H3 heading up to the next H2/H3.
3. **Skip** chunks whose body is empty, `_TBD_`, or an `N/A — ...` single line. No signal to embed.
4. **Preserve** the service name parsed from the H1 (`# KNOWLEDGE: <SERVICE_NAME>`) and return it alongside the chunks so the tool layer can attach it to payloads. (The `contexta-init` template uses this exact H1 format.)

### `qdrant_io.py` — Qdrant wrapper

```python
async def ensure_collection(client, name="knowledge", dim=768): ...   # idempotent
async def upsert_chunks(client, name, chunks: list[PointStruct]): ...
async def search(client, name, vector, repo=None, section=None, limit=5): ...
async def list_distinct_repos(client, name): ...
async def get_point(client, name, point_id): ...
```

`ensure_collection` creates the collection with `size=768, distance=Cosine` if absent; also creates payload indexes for `repo`, `section`, `subsection` (keyword type) — needed for fast filtering in `search`.

### `tools.py` — the MCP tool functions

Thin orchestration. Example:

```python
async def upsert_knowledge(repo, repo_url, git_sha, markdown):
    chunks = chunker.chunk(markdown)                        # list[Chunk]
    vectors = await embedder.embed([c.text for c in chunks])  # list[list[float]]
    points = [to_point(repo, repo_url, git_sha, c, v, now) for c, v in zip(chunks, vectors)]
    await qdrant_io.replace_repo_points(repo, points)        # delete-then-upsert for idempotency
    return {"indexed_chunks": len(points), "skipped": chunker.last_skipped_count()}
```

Point IDs: deterministic UUIDv5 from `(repo, subsection)` — makes re-indexing idempotent without needing to track existing IDs on the client.

### `server.py` — FastMCP app

Uses the `mcp` Python SDK's `FastMCP` with `streamable-http` transport. Listens on `0.0.0.0:3333` inside the container (bound to `127.0.0.1` on the host). Registers the four tools with pydantic-typed args. Startup hook calls `ensure_collection`.

### `config.py` — env vars

The initial env surface was `QDRANT_URL`, `EMBEDDINGS_API`, `EMBEDDINGS_URL`, `EMBEDDINGS_MODEL`, `COLLECTION`, `MCP_PORT`. Current full list (including later additions like `SEARCH_DEFAULT_LIMIT`, `VECTOR_SIZE`, `MCP_HOST`, `ALLOWED_HOSTS`) is in [`../../mcp-server/README.md`](../../mcp-server/README.md).

## `compose.yaml` additions

The server was added as a third compose service alongside Qdrant and Ollama, bound to `127.0.0.1:3333`, with `depends_on` health conditions on both. Live wiring is in [`../../compose.yaml`](../../compose.yaml).

## Out of scope

- The k8s indexer CronJob (next plan after this).
- Hybrid dense+sparse search / reranking (defer until pure-dense retrieval shows gaps).
- Auth on the MCP endpoint (localhost-only for now; add bearer tokens when it goes to k8s).
- Multi-tenant / per-team visibility.
- Any TEI-side work — Ollama is enough for local; TEI gets wired in when we deploy to k8s.