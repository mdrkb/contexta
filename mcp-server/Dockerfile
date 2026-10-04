FROM python:3.12-slim

WORKDIR /app

# Install deps first for cache-friendly rebuilds.
COPY pyproject.toml ./
RUN pip install --no-cache-dir \
      "mcp>=2.3.0" \
      "qdrant-client>=1.11.0" \
      "httpx>=0.27.0" \
      "pydantic>=2.0" \
      "uvicorn>=0.30" \
      "starlette>=0.37"

COPY src/ ./src/
ENV PYTHONPATH=/app/src

EXPOSE 3333

CMD ["python", "-m", "contexta_mcp"]