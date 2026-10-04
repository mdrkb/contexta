"""ASGI entrypoint. Serve with uvicorn: `uvicorn contexta_mcp.server:app`."""

from __future__ import annotations

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from mcp.server.streamable_http import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.routing import Mount

from contexta_mcp.tools import mcp

# Hosts that may appear in the Host header. The streamable-HTTP transport
# validates this to prevent DNS rebinding attacks. Add any hostname a
# legitimate client would use.
_DEFAULT_HOSTS = "localhost,localhost:*,127.0.0.1,127.0.0.1:*,contexta-mcp,contexta-mcp:*"
_allowed_hosts = [
    h.strip()
    for h in os.environ.get("ALLOWED_HOSTS", _DEFAULT_HOSTS).split(",")
    if h.strip()
]
_transport_security = TransportSecuritySettings(allowed_hosts=_allowed_hosts)


@asynccontextmanager
async def _lifespan(app: Starlette) -> AsyncIterator[None]:
    async with mcp.session_manager.run():
        yield


app = Starlette(
    routes=[
        Mount("/", app=mcp.streamable_http_app(transport_security=_transport_security))
    ],
    lifespan=_lifespan,
)