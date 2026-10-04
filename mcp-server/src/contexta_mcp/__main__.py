"""`python -m contexta_mcp` → launch the HTTP server with uvicorn."""

from __future__ import annotations

import uvicorn

from contexta_mcp.config import load


def main() -> None:
    cfg = load()
    uvicorn.run(
        "contexta_mcp.server:app",
        host=cfg.mcp_host,
        port=cfg.mcp_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
