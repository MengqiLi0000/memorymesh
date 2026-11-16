FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 MESH_DATA_DIR=/data
RUN pip install --no-cache-dir uv
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY packages ./packages
COPY apps/api ./apps/api
RUN uv sync --all-packages --frozen --no-dev
EXPOSE 8765
VOLUME ["/data"]
CMD ["uv", "run", "--no-sync", "memory-mesh", "serve", "--host", "0.0.0.0", "--port", "8765"]
