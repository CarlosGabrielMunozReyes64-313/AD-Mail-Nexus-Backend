FROM python:3.14-slim
WORKDIR /app
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev
COPY . .
RUN useradd --system --uid 10001 nexus && chown -R nexus:nexus /app
USER nexus
EXPOSE 8000
CMD ["uv", "run", "--no-sync", "uvicorn", "app.main:crear_app", "--factory", "--host", "0.0.0.0", "--no-access-log"]
