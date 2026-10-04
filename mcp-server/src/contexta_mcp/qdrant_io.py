"""Qdrant client wrapper tuned for contexta's one collection."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from qdrant_client import AsyncQdrantClient, models

# Deterministic namespace so (repo, subsection) → the same UUID across runs.
_POINT_NAMESPACE = uuid.UUID("8f5a9b2c-1d4e-4a8b-9c3d-5e6f7a8b9c0d")


def point_id_for(repo: str, subsection: str) -> str:
    return str(uuid.uuid5(_POINT_NAMESPACE, f"{repo}\x1f{subsection}"))


@dataclass
class ChunkPayload:
    repo: str
    repo_url: str
    section: str
    subsection: str
    text: str
    git_sha: str
    updated_at: str


async def ensure_collection(
    client: AsyncQdrantClient, name: str, dim: int
) -> None:
    """Create the collection + payload indexes if missing. Idempotent."""
    existing = {c.name for c in (await client.get_collections()).collections}
    if name not in existing:
        await client.create_collection(
            collection_name=name,
            vectors_config=models.VectorParams(
                size=dim,
                distance=models.Distance.COSINE,
            ),
        )
    # Payload indexes are idempotent to create.
    for field in ("repo", "section", "subsection"):
        await client.create_payload_index(
            collection_name=name,
            field_name=field,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )


async def replace_repo_points(
    client: AsyncQdrantClient,
    collection: str,
    repo: str,
    points: list[models.PointStruct],
) -> None:
    """Delete all existing points for `repo`, then upsert the new set.

    This makes re-indexing idempotent and removes orphan points when a
    subsection disappears from a KNOWLEDGE.md.
    """
    await client.delete(
        collection_name=collection,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="repo",
                        match=models.MatchValue(value=repo),
                    )
                ]
            )
        ),
    )
    if points:
        await client.upsert(collection_name=collection, points=points)


async def search(
    client: AsyncQdrantClient,
    collection: str,
    vector: list[float],
    repo: str | None = None,
    section: str | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    must: list[models.FieldCondition] = []
    if repo:
        must.append(
            models.FieldCondition(key="repo", match=models.MatchValue(value=repo))
        )
    if section:
        must.append(
            models.FieldCondition(key="section", match=models.MatchValue(value=section))
        )
    flt = models.Filter(must=must) if must else None
    hits = await client.query_points(
        collection_name=collection,
        query=vector,
        query_filter=flt,
        limit=limit,
        with_payload=True,
    )
    return [
        {"id": str(h.id), "score": h.score, "payload": h.payload}
        for h in hits.points
    ]


async def list_distinct_repos(
    client: AsyncQdrantClient, collection: str
) -> list[str]:
    # No native DISTINCT; scroll with payload-only, dedupe client-side.
    # Fine at contexta's scale (<<10k points).
    seen: set[str] = set()
    offset = None
    while True:
        batch, offset = await client.scroll(
            collection_name=collection,
            limit=256,
            with_payload=["repo"],
            with_vectors=False,
            offset=offset,
        )
        for p in batch:
            repo = (p.payload or {}).get("repo")
            if repo:
                seen.add(repo)
        if offset is None:
            break
    return sorted(seen)


async def get_point(
    client: AsyncQdrantClient, collection: str, point_id: str
) -> dict[str, Any] | None:
    results = await client.retrieve(
        collection_name=collection,
        ids=[point_id],
        with_payload=True,
        with_vectors=False,
    )
    if not results:
        return None
    p = results[0]
    return {"id": str(p.id), "payload": p.payload}