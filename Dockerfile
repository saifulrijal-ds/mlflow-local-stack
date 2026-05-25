ARG MLFLOW_VERSION=latest
FROM python:3.12-slim

# Install uv for fast package management
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install MLflow and dependencies using uv
# Handles "latest" (no pin) vs a specific version (e.g., "2.21.3")
ARG MLFLOW_VERSION
RUN if [ "${MLFLOW_VERSION}" = "latest" ]; then \
        uv pip install --system --no-cache mlflow psycopg2-binary boto3; \
    else \
        uv pip install --system --no-cache "mlflow==${MLFLOW_VERSION}" psycopg2-binary boto3; \
    fi
