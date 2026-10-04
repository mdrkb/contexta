"""MCP tool implementations and FastMCP server wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from pydantic import Field
from qdrant_client import AsyncQdrantClient, models

from contexta_mcp import chunker, qdrant_io
from contexta_mcp.config import Config, load as load_config
from contexta_mcp.embeddings import Embedder


@dataclass
class AppContext:
    config: Config
    qdrant: AsyncQdrantClient
    embedder: Embedder


@asynccontextmanager
async def lifespan(server: MCPServer) -> AsyncIterator[AppContext]:
    cfg = load_config()
    qdrant = AsyncQdrantClient(url=cfg.qdrant_url)
    embedder = Embedder(
        api=cfg.embeddings_api, url=cfg.embeddings_url, model=cfg.embeddings_model
    )
    await qdrant_io.ensure_collection(qdrant, cfg.collection, cfg.vector_size)
    try:
        yield AppContext(config=cfg, qdrant=qdrant, embedder=embedder)
    finally:
        await embedder.aclose()
        await qdrant.close()


mcp = MCPServer("contexta", lifespan=lifespan)


@mcp.tool()
async def upsert_knowledge(
    ctx: Context[AppContext],
    repo: str = Field(..., description="Short repo/service identifier, e.g. 'order-api'."),
    repo_url: str = Field(..., description="HTTPS git URL for the service repo."),
    git_sha: str = Field(..., description="Commit SHA of the KNOWLEDGE.md being indexed."),
    markdown: str = Field(..., description="Full KNOWLEDGE.md content."),
) -> dict[str, Any]:
    """Chunk a KNOWLEDGE.md by H3 subsection, embed each chunk, and upsert to Qdrant.

    Idempotent: replaces every existing point for this `repo` so re-indexing
    with the same content yields the same point IDs and leaves no orphans.
    """
    app = ctx.request_context.lifespan_context
    parsed = chunker.parse(markdown)
    if not parsed.chunks:
        await qdrant_io.replace_repo_points(
            app.qdrant, app.config.collection, repo, []
        )
        return {"indexed_chunks": 0, "skipped": parsed.skipped, "service_name": parsed.service_name}

    vectors = await app.embedder.embed([c.text for c in parsed.chunks])
    now = datetime.now(timezone.utc).isoformat()
    points = [
        models.PointStruct(
            id=qdrant_io.point_id_for(repo, c.subsection),
            vector=v,
            payload={
                "repo": repo,
                "repo_url": repo_url,
                "section": c.section,
                "subsection": c.subsection,
                "text": c.text,
                "git_sha": git_sha,
                "updated_at": now,
            },
        )
        for c, v in zip(parsed.chunks, vectors)
    ]
    await qdrant_io.replace_repo_points(
        app.qdrant, app.config.collection, repo, points
    )
    return {
        "indexed_chunks": len(points),
        "skipped": parsed.skipped,
        "service_name": parsed.service_name,
    }


@mcp.tool()
async def search(
    ctx: Context[AppContext],
    query: str = Field(..., description="Natural-language question."),
    repo: str | None = Field(default=None, description="Optional repo filter."),
    section: str | None = Field(default=None, description="Optional H2 section filter."),
    limit: int | None = Field(
        default=None,
        ge=1,
        le=50,
        description="Top-N chunks to return. Defaults to SEARCH_DEFAULT_LIMIT (env).",
    ),
) -> list[dict[str, Any]]:
    """Semantic search over indexed KNOWLEDGE.md chunks."""
    app = ctx.request_context.lifespan_context
    effective_limit = limit if limit is not None else app.config.search_default_limit
    [vector] = await app.embedder.embed([query])
    return await qdrant_io.search(
        app.qdrant,
        app.config.collection,
        vector,
        repo=repo,
        section=section,
        limit=effective_limit,
    )


@mcp.tool()
async def list_services(ctx: Context[AppContext]) -> list[str]:
    """Return the distinct `repo` values currently indexed."""
    app = ctx.request_context.lifespan_context
    return await qdrant_io.list_distinct_repos(app.qdrant, app.config.collection)


@mcp.tool()
async def get_chunk(
    ctx: Context[AppContext],
    id: str = Field(..., description="Point ID as returned by `search`."),
) -> dict[str, Any] | None:
    """Fetch a single chunk by its point ID."""
    app = ctx.request_context.lifespan_context
    return await qdrant_io.get_point(app.qdrant, app.config.collection, id)