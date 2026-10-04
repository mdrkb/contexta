# contexta architecture

A reference for the components, data flow, and the decisions behind them. Living document — update it when a decision changes.

## Goal

Give the team a single, queryable source of truth about every service they own. Repo owners write a `KNOWLEDGE.md` at the root of each service. A scheduled indexer picks those files up, embeds them, and stores the vectors in Qdrant. An MCP server exposes semantic search to Claude Code.

## Components

```
┌───────────────────────────────────────────────────────────────────────────┐
│                             WRITE PATH                                    │
│                                                                           │
│  service repos            Indexer (k8s CronJob)         Qdrant            │
│  ┌──────────┐             ┌────────────────────┐        ┌───────────────┐ │
│  │ repo A   │ ──clone──►  │ 1. read KNOWLEDGE  │        │               │ │
│  │ KNOWLEDGE│             │ 2. chunk by H2/H3  │        │ contexta-     │ │
│  └──────────┘             │ 3. embed via HTTP  │ ─────► │ knowledge     │ │
│  ┌──────────┐             │ 4. upsert points   │        │ collection    │ │
│  │ repo B   │ ──clone──►  └────────────────────┘        │ (768-d)       │ │
│  └──────────┘                     │                     └───────────────┘ │
│                                   ▼                                       │
│                           ┌───────────────┐                               │
│                           │ Embedding svc │  nomic-embed-text-v1.5        │
│                           │  (TEI/Ollama) │  768 dim, cosine              │
│                           └───────────────┘                               │
│                                   ▲                                       │
└───────────────────────────────────┼───────────────────────────────────────┘
                                    │
┌───────────────────────────────────┼───────────────────────────────────────┐
│                             READ PATH                                     │
│                                   │                                       │
│  Claude Code                      │                                       │
│       │                           │                                       │
│       │  MCP tool call            │                                       │
│       ▼                           │                                       │
│  ┌────────────┐                   │                                       │
│  │ MCP server │ ──embed query────►│                                       │
│  │ (contexta) │ ◄─── vector ──────┘                                       │
│  │            │                                                           │
│  │            │ ──search(vec)──► Qdrant ──top-N chunks──►                 │
│  │            │                                                           │
│  │            │ ──return chunks─────────────────────► Claude Code         │
│  └────────────┘                                                           │
└───────────────────────────────────────────────────────────────────────────┘
```

## Services

| Component | Role | Local dev | Prod (k8s) |
|---|---|---|---|
| **Qdrant** | Vector storage + nearest-neighbor search | Docker container, port 6333/6334 | StatefulSet + PVC |
| **Embedding model** | Turns text → 768-dim vector | Ollama (`ollama/ollama`) at :11434 | TEI (`ghcr.io/huggingface/text-embeddings-inference`) as a Deployment |
| **MCP server** (`contexta-mcp`) | Exposes `upsert_knowledge`/`search`/`list_services`/`get_chunk` tools to Claude Code. Owns chunking and embeds queries via the embedding service. See `mcp-server/`. | Docker container, port 3333 | Deployment + Service |
| **Indexer** (not built yet) | Walks registered repos, re-chunks + re-embeds changed `KNOWLEDGE.md`, upserts to Qdrant via `contexta-mcp` | TBD | CronJob (hourly or daily) |

`contexta-init` (the Claude Code skill, already built) is **not** a runtime component — it runs in a repo owner's editor to produce `KNOWLEDGE.md`.

## Data model

**Qdrant collection: `contexta-knowledge`**

| Property | Value |
|---|---|
| Vector size | 768 |
| Distance | Cosine |
| Vectors | Single unnamed vector per point |

**Point shape**

```json
{
  "id": "<uuid>",
  "vector": [0.021, -0.113, ...],
  "payload": {
    "repo": "order-api",
    "repo_url": "https://github.com/org/order-api",
    "section": "Operational context",
    "subsection": "On-call",
    "text": "<the chunk text>",
    "updated_at": "2026-10-02T00:00:00Z",
    "git_sha": "<commit sha of the KNOWLEDGE.md this chunk came from>"
  }
}
```

**Payload indexes** (so filters are fast):
- `repo` → keyword
- `section` → keyword
- `subsection` → keyword

## Chunking strategy

One chunk per **H3 subsection** of `KNOWLEDGE.md`. The template (see `skills/contexta-init/template.md`) is designed so each H3 is a self-contained unit (e.g. "Why this service exists", "Dashboards and runbooks").

Rationale:
- H3-level chunks are small (typically 50–500 tokens) → embed cleanly, retrieve precisely.
- Section/subsection metadata attached to the payload → downstream queries can filter ("only operational-context chunks") or boost by section.
- When Claude cites a chunk, it can name the service and the exact subsection, which is actionable.

Chunks under 20 tokens or `_TBD_` placeholders are skipped at index time — no signal to embed.

## Embedding model

**`nomic-ai/nomic-embed-text-v1.5`** — 768 dim, cosine distance, Apache 2.0, English-focused.

Trade-offs considered:
- **Local-only requirement** (team context must not leave infra) rules out OpenAI/Voyage/Cohere.
- **nomic-embed-text** was chosen over `bge-m3` (1024-d, multilingual) and `mxbai-embed-large` (1024-d, 512-ctx) because: Apache 2.0, 8k context in native TEI, strong English benchmarks, small enough to run on CPU, served natively by both TEI and Ollama.
- **768 dim** × a few thousand chunks total is negligible storage; no reason to compress.

The model name is pinned to the same version in both runners. Vectors are byte-for-byte interchangeable between Ollama and TEI output because the underlying weights are the same.

### Dev / prod runner split

| | Local (dev) | k8s (prod) |
|---|---|---|
| Runner | Ollama | TEI |
| Reason | arm64-native, fast on Apple Silicon; TEI's CPU image is amd64-only | Production features (batching, Prometheus metrics, long context) |
| API | `POST /api/embeddings` | `POST /embed` |
| Max context | 2k tokens | 8k tokens |

Downstream services (indexer, MCP server) talk to an `EMBEDDINGS_URL` env var. A thin adapter in each service picks the right request shape based on the URL's host or a `EMBEDDINGS_API` flag. Vectors are identical, so Qdrant doesn't care which was used.

Note: Ollama returns un-normalized vectors; TEI returns normalized. Qdrant with cosine distance normalizes internally, so the retrieval behavior is the same — but **don't mix** Ollama- and TEI-sourced vectors in a dot-product collection or similarity scores will diverge.

## MCP server surface (planned)

Minimum viable tool set for v1:

- `search(query: string, repo?: string, section?: string, limit?: int=5)` → list of chunks with payload. Does the embed-and-search dance server-side.
- `list_services()` → distinct values of `payload.repo` currently indexed.
- `get_chunk(id: string)` → full chunk by ID.
- `upsert_knowledge(repo, repo_url, git_sha, markdown)` → write-path tool the indexer calls. Chunks + embeds + upserts in one shot.

The MCP server owns the chunking logic too — the indexer sends a whole file, the server decides how it's split. This keeps the chunking strategy in one place and lets us iterate on it without changing the indexer.

## Indexer (planned)

- **Trigger**: k8s CronJob, hourly to start.
- **Input**: a ConfigMap or GitHub query listing registered repo URLs. (Mechanism TBD — the simplest v1 is a static list.)
- **Steps per repo**:
  1. Shallow-clone (or fetch via GitHub API) `KNOWLEDGE.md`.
  2. If the file's git SHA matches what's already in Qdrant payload for this repo, skip.
  3. Otherwise, call `contexta-mcp.upsert_knowledge` with the file content + metadata.
- **Idempotency**: upsert replaces all points for a given `(repo, subsection)` tuple. No orphan points when subsections are removed.

## Open questions

- **How does the indexer discover repos?** Static ConfigMap vs. GitHub org query vs. a `contexta-registered` topic/label on repos.
- **Hybrid search (dense + BM25)?** Qdrant supports it via a sparse vector alongside the dense one. Defer until we see what pure dense retrieval misses.
- **Chunk-text storage**: payload holds the raw text now, which doubles effective storage. Alternative: store only the vector + a pointer to a git URL + line range, re-fetch on read. Simpler to start with text in the payload.
- **Access control**: v0 assumes the whole team can read every indexed service. If per-team visibility is ever needed, add a `visibility` payload field and filter at the MCP layer.

## Non-goals (for v0)

- Indexing anything other than `KNOWLEDGE.md` (no code, no READMEs, no ADRs — those come later if the pattern works).
- Reranking (cross-encoder step after retrieval). Add if quality is poor.
- Multiple embedding models or multi-vector points.
- A web UI. Query via Claude Code; inspect via Qdrant's built-in dashboard at `/dashboard`.