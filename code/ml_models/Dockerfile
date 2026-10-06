FROM python:3.12-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --prefix=/install \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    -r requirements.txt

FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r fluxion && useradd -r -g fluxion -d /app -s /sbin/nologin fluxion

WORKDIR /app

COPY --from=builder /install /usr/local
COPY --chown=fluxion:fluxion . /app/ml_models

RUN mkdir -p /app/models /app/logs && chown -R fluxion:fluxion /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000 \
    METRICS_PORT=9091 \
    MODEL_PATH=/app/models

USER fluxion

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

EXPOSE 8000 9091

CMD ["python", "-m", "ml_models.serving"]
