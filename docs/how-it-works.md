# How contexta works, end-to-end

A walkthrough of a single `KNOWLEDGE.md` moving through the system — the write path (indexing) and the read path (searching) — with the data shapes at each stage.

## The example

A tiny `KNOWLEDGE.md` in a repo called `order-api`:

```markdown
# KNOWLEDGE: order-api

## Business context

### Why this service exists
Handles customer purchases and payment processing. Core revenue path.

### Impact if it breaks
Customers cannot complete checkout. Direct revenue loss, roughly $X/hour.

### Who uses it
_TBD_

## Operational context

### On-call
Team Payments, PagerDuty rotation `payments-oncall`, #payments-sos Slack.
```

4 subsections total: 3 with real content, 1 placeholder.

---

## Stage 1 — Write path: calling `upsert_knowledge`

You prompt Claude Code: *"Read `/path/to/order-api/KNOWLEDGE.md` and upsert it to contexta as repo `order-api`, repo_url `https://github.com/example/order-api`, git_sha `abc123`."*

Claude reads the file, then calls the MCP tool. The MCP request going out:

```json
{
  "method": "tools/call",
  "params": {
    "name": "upsert_knowledge",
    "arguments": {
      "repo": "order-api",
      "repo_url": "https://github.com/example/order-api",
      "git_sha": "abc123",
      "markdown": "# KNOWLEDGE: order-api\n\n## Business context\n\n### Why this service exists\n..."
    }
  }
}
```

The HTTP server (uvicorn + Starlette + MCP) routes it to the `upsert_knowledge` function in `tools.py`.

## Stage 2 — Chunking (`chunker.py`)

The function parses the markdown line by line. It tracks the current H2 and H3; the body of each H3 becomes a candidate chunk.

Pseudo-trace:

```
line "# KNOWLEDGE: order-api"            → service_name = "order-api"
line "## Business context"               → current_section = "Business context"
line "### Why this service exists"       → start chunk ("Business context", "Why this service exists")
line "Handles customer purchases..."     → append to body
line "### Impact if it breaks"           → flush previous chunk, start next
...
line "### Who uses it"                   → start chunk
line "_TBD_"                             → body is just _TBD_
                                          → when we flush, _is_placeholder() returns True
                                          → skip (skipped counter += 1)
line "## Operational context"            → ...
line "### On-call"                       → start chunk
```

Output of the chunker — a `ParsedKnowledge` object:

```python
ParsedKnowledge(
    service_name="order-api",
    skipped=1,
    chunks=[
        Chunk(section="Business context",   subsection="Why this service exists",
              text="Handles customer purchases and payment processing. Core revenue path."),
        Chunk(section="Business context",   subsection="Impact if it breaks",
              text="Customers cannot complete checkout. Direct revenue loss, roughly $X/hour."),
        Chunk(section="Operational context",subsection="On-call",
              text="Team Payments, PagerDuty rotation `payments-oncall`, #payments-sos Slack."),
    ]
)
```

Why this chunking choice: each H3 is semantically a self-contained unit — "why it exists" and "on-call" are different concepts and should land in different vectors. If we chunked by whole file, "payment processing" and "PagerDuty" would be averaged into one blurry vector, and the search *"who's on call?"* might not find the on-call section cleanly.

## Stage 3 — Embedding (`embeddings.py`)

The tool now needs vectors for the three chunks' bodies. It calls `embedder.embed(texts)` which, in local dev, means a POST per text to Ollama:

```http
POST http://ollama:11434/api/embeddings
{"model": "nomic-embed-text:v1.5",
 "prompt": "Handles customer purchases and payment processing. Core revenue path."}
```

Ollama runs the chunk text through the `nomic-embed-text` neural network. Internally that's: tokenize → forward pass through the transformer → mean-pool the token embeddings → L2 normalize (or not — Ollama returns raw). Output is 768 floats.

Response:

```json
{ "embedding": [-0.693, 1.095, -2.839, 0.421, ..., 0.117] }
```

That number sequence is the chunk's **meaning as a point in 768-dimensional space**. Chunks about similar topics land in similar regions of that space; unrelated chunks land far apart. The network has learned this mapping from training on billions of text pairs.

The tool loops once per chunk and ends up with:

```python
vectors = [
  [-0.693, 1.095, ...],   # for "Why this service exists" body
  [ 0.021, -0.447, ...],  # for "Impact if it breaks" body
  [ 0.558,  0.102, ...],  # for "On-call" body
]
```

Three vectors, 768 floats each. **At this point the system has traded human-readable prose for a mathematical representation of its meaning.** This is the one and only step where "understanding" happens. Everything downstream is just storage and distance math.

## Stage 4 — Building Qdrant points

The tool bundles each vector with metadata. Deterministic IDs come from UUIDv5 of `(repo, subsection)` — so re-indexing the same subsection always produces the same ID:

```python
PointStruct(
  id="7f3a8b2c-...",   # uuid5(namespace, "order-api\x1fWhy this service exists")
  vector=[-0.693, 1.095, ...],  # the 768-float embedding
  payload={
    "repo": "order-api",
    "repo_url": "https://github.com/example/order-api",
    "section": "Business context",
    "subsection": "Why this service exists",
    "text": "Handles customer purchases and payment processing. Core revenue path.",
    "git_sha": "abc123",
    "updated_at": "2026-10-03T14:22:11+00:00"
  }
)
```

Important: **the chunk's text is stored in the payload** alongside the vector. The vector is for *finding*; the text is for *reading back*. Qdrant doesn't need the text — but we do, so the search tool can return it to Claude.

## Stage 5 — Idempotent upsert (`qdrant_io.replace_repo_points`)

Two Qdrant operations, in order:

1. **Delete every existing point with `payload.repo == "order-api"`**. Uses Qdrant's filter-selector delete.
2. **Upsert the three new points.**

Why delete-then-upsert instead of just upsert: if the author removes a subsection in a later edit (say they delete "On-call"), a plain upsert leaves the old on-call point as an orphan — queries would still surface stale content. Delete-first guarantees Qdrant exactly reflects the current `KNOWLEDGE.md`.

Qdrant stores the three points in its **HNSW** index (Hierarchical Navigable Small World — a graph-based data structure that makes nearest-neighbor queries fast; think of it as a skip-list for vectors). Points also get indexed on `repo`, `section`, `subsection` because the collection was created with payload indexes.

The MCP tool returns to Claude:

```json
{"indexed_chunks": 3, "skipped": 1, "service_name": "order-api"}
```

Done with the write path. State of the world: Qdrant has 3 new points (plus whatever was already there for other repos); Ollama is unchanged; the `KNOWLEDGE.md` file on disk is untouched.

---

## Read path: searching

Now someone asks in Claude Code: *"Who's on call for the order-api?"*

Claude decides this is a `search` call and sends:

```json
{"name": "search", "arguments": {"query": "Who's on call for the order-api?", "limit": 5}}
```

Steps inside `search`:

### 1. Embed the query (same embedder, same model)

Critical point: **the query goes through the exact same model that embedded the chunks**. Different model = different vector space = garbage retrieval.

```http
POST http://ollama:11434/api/embeddings
{"model": "nomic-embed-text:v1.5", "prompt": "Who's on call for the order-api?"}
```

Result: a 768-dim query vector `q = [0.512, 0.089, ..., 0.311]`.

### 2. Qdrant nearest-neighbor search

```python
await qdrant.query_points(
    collection_name="knowledge",
    query=q,
    query_filter=None,       # no repo/section filter in this example
    limit=5,
    with_payload=True,
)
```

Qdrant walks the HNSW graph to find the 5 points whose vectors have the highest cosine similarity to `q`. Cosine similarity ranges from -1 (opposite meaning) to +1 (identical meaning). For a well-posed query, good hits are usually 0.5–0.8.

The result (ordered by score descending):

```python
[
  Hit(id="...", score=0.812, payload={
      "section": "Operational context", "subsection": "On-call",
      "text": "Team Payments, PagerDuty rotation `payments-oncall`...",
      "repo": "order-api", ...}),
  Hit(id="...", score=0.421, payload={
      "section": "Business context", "subsection": "Why this service exists",
      "text": "Handles customer purchases...", "repo": "order-api", ...}),
  ...
]
```

Notice: the "On-call" chunk wins decisively (0.81 vs 0.42) even though its text contains neither the word "who" nor the string "order-api" — because semantically it's the answer. **This is the whole payoff of using embeddings instead of grep.**

### 3. Return the shaped result

```json
{
  "result": [
    {"id": "...", "score": 0.812, "payload": {...on-call payload...}},
    ...
  ]
}
```

### 4. Claude writes the final answer

Claude sees the chunks in its context window and synthesizes a reply: *"Team Payments is on call for order-api, via the `payments-oncall` PagerDuty rotation. The team's Slack channel is `#payments-sos`."*

It cites the specific subsection it drew from. That's the "G" in RAG: generation grounded in retrieved chunks.

---

## The whole picture in one diagram

```
   KNOWLEDGE.md
        │
        ▼  (your prompt: "upsert this")
   ┌────────────────────────────────────────────────────────────┐
   │ contexta-mcp.upsert_knowledge                              │
   │   1. chunker.parse(md)                                     │
   │        → [Chunk(section, subsection, text), ...]           │
   │   2. embedder.embed([c.text for c in chunks])              │
   │        → calls Ollama /api/embeddings (one req per chunk)  │
   │        → [[768 floats], [768 floats], ...]                 │
   │   3. build Point(id, vector, payload)                      │
   │   4. qdrant.delete(where repo=X)                           │
   │   5. qdrant.upsert(points)                                 │
   └────────────────────────────────────────────────────────────┘
                      │
                      ▼
                 [Qdrant HNSW index + payloads]
                      ▲
                      │
   ┌────────────────────────────────────────────────────────────┐
   │ contexta-mcp.search                                        │
   │   1. embedder.embed([query])  (SAME model as write path)   │
   │        → [768 floats]                                      │
   │   2. qdrant.query_points(vec, filter, limit=5)             │
   │        → top-N points ranked by cosine similarity          │
   │   3. return [{id, score, payload}, ...]                    │
   └────────────────────────────────────────────────────────────┘
                      ▲
                      │   ◄── your prompt: "who's on call?"
                 Claude Code
                      │
                      ▼   final answer with cited chunks
```

## Three invariants that make it all work

1. **Same embedding model on write and read paths.** If someone swaps the model, every stored vector becomes meaningless against new queries. That's why `EMBEDDINGS_MODEL` is pinned.
2. **Vector dimension is fixed at collection creation (768).** Switching models with a different dim means creating a new collection and re-embedding everything.
3. **Idempotency comes from deterministic IDs + delete-then-upsert, not from caller discipline.** You can call `upsert_knowledge` twice with the same markdown and the point count stays constant.

## What you can inspect by hand

```sh
# Count points in the collection
curl -s http://localhost:6333/collections/contexta-knowledge \
  | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['result']['points_count'])"

# Browse all points in the dashboard
open http://localhost:6333/dashboard

# Hit the embedding endpoint directly to see what a vector looks like
curl -s http://localhost:11434/api/embeddings \
  -d '{"model":"nomic-embed-text:v1.5","prompt":"on-call rotation"}' \
  | python3 -c "import json,sys; v=json.load(sys.stdin)['embedding']; print('dim', len(v), 'first 5', v[:5])"
```

## TL;DR mental model

**Write**: markdown → chunks → vectors (via Ollama) → Qdrant points (vector + payload).
**Read**: query → vector (via Ollama) → nearest Qdrant points → payload text → Claude synthesizes.

Qdrant is a storage index with fast nearest-neighbor math. Ollama is the "meaning extractor." The MCP server is the glue that owns chunking strategy and talks to both. Everything you'd want to improve (chunking boundaries, reranking, hybrid search) plugs into the MCP server; the two external services stay as-is.