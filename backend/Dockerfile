# syntax=docker/dockerfile:1

# Etapa 1: resolución de dependencias con uv.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# uv se instala sin pin en esta etapa; fijar versión/digest antes de producción.
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml README.md ./
# Sin uv.lock todavía: uv resuelve en el build. Cuando se genere, copiarlo y usar --frozen.
RUN uv sync --no-dev --no-install-project

COPY app ./app
RUN uv sync --no-dev

# Etapa 2: imagen de ejecución.
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN groupadd --system --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --home-dir /app --shell /usr/sbin/nologin --no-create-home appuser \
    && mkdir -p /app \
    && chown -R appuser:appuser /app

WORKDIR /app

COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
