# MLflow with Docker Compose (PostgreSQL + RustFS)

This directory provides a **Docker Compose** setup for running **MLflow** locally with a **PostgreSQL** backend store and **MinIO** (S3-compatible) artifact storage. It's intended for quick evaluation and local development.

---

## Overview

- **MLflow Tracking Server** — exposed on your host (default `http://localhost:5000`).
- **PostgreSQL** — persists MLflow's metadata (experiments, runs, params, metrics).
- **RustFS** — stores run artifacts via an S3-compatible API. RustFS is 2.3x faster than MinIO for small object payloads and is licensed under Apache 2.0.

Compose automatically reads configuration from a local `.env` file in this directory.

---


## Architecture

```
Client → MLflow Server (proxy) → RustFS (artifacts)
                ↓
           PostgreSQL (metadata)
```

## Quick Start

```bash
cp .env.example .env
# Edit .env with your credentials
docker compose up -d
```

MLflow UI: http://localhost:5000

### Services

| Service         | Description                          | Port  |
|-----------------|--------------------------------------|-------|
| `mlflow`        | Tracking server + artifact proxy     | 5000  |
| `postgres`      | Backend store (metadata)             | 5432  |
| `rustfs`        | S3-compatible artifact storage (API) | 9090  |
| `rustfs`        | RustFS console (Web UI)              | 9091  |
| `create-bucket` | Init: creates S3 bucket via boto3    | -     |
| `db-upgrade`    | Init: runs DB migration              | -     |

### Client Usage

```python
import mlflow

mlflow.set_tracking_uri("http://localhost:5000")

# No S3 credentials needed — server proxies artifacts
with mlflow.start_run():
    mlflow.log_param("lr", 0.01)
    mlflow.log_metric("accuracy", 0.95)
    mlflow.log_artifact("model.pkl")
```

## Prerequisites

- **Git**
- **Docker** and **Docker Compose**
  - Windows/macOS: [Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Linux: Docker Engine + the `docker compose` plugin

Verify your setup:

```bash
docker --version
docker compose version
```

---

## 1. Clone the Repository

```bash
git clone https://github.com/mlflow/mlflow.git
cd docker-compose
```

---

## 2. Configure Environment

Copy the example environment file and modify as needed:

```bash
cp .env.dev.example .env
```

The `.env` file defines container image tags, ports, credentials, and storage configuration. Open it and review values before starting the stack.

**Common variables** :

- **MLflow**
  - `MLFLOW_PORT=5000` — host port for the MLflow UI/API
  - `MLFLOW_ARTIFACTS_DESTINATION=s3://mlflow/` — artifact store URI
  - `MLFLOW_S3_ENDPOINT_URL=http://rustfs:9000` — S3 endpoint (inside the Compose network)
- **PostgreSQL**
  - `POSTGRES_USER=mlflow`
  - `POSTGRES_PASSWORD=mlflow`
  - `POSTGRES_DB=mlflow`
- **RustFS (S3-compatible)**
  - `RUSTFS_ACCESS_KEY=rustfs`
  - `RUSTFS_SECRET_KEY=rustfs123`
  - `RUSTFS_HOST=rustfs`
  - `RUSTFS_API_PORT=9090` — S3 API port (host-mapped)
  - `RUSTFS_CONSOLE_PORT=9091` — RustFS Console port (host-mapped)
  - `RUSTFS_BUCKET=mlflow`

---

## 3. Launch the Stack

```bash
docker compose up -d
```

This:

- Builds/pulls images as needed
- Creates a user-defined network
- Starts **postgres**, **rustfs**, and **mlflow** containers

Check status:

```bash
docker compose ps
```

View logs (useful on first run):

```bash
docker compose logs -f
```

---

## 4. Access MLflow

Open the MLflow UI:

- **URL**: `http://localhost:5000` (or the port set in `.env`)

You can now create experiments, run training scripts, and log metrics, parameters, and artifacts to this local MLflow instance.

---

## 5. Shutdown

To stop and remove the containers and network:

```bash
docker compose down
```

> Data is preserved in Docker **volumes**. To remove volumes as well (irreversible), run:
>
> ```bash
> docker compose down -v
> ```

---

## Tips & Troubleshooting

- **Verify connectivity**  
  If MLflow can't write artifacts, confirm your S3 settings:

  - `MLFLOW_DEFAULT_ARTIFACT_ROOT` points to your RustFS bucket (e.g., `s3://mlflow/`)
  - `MLFLOW_S3_ENDPOINT_URL` is reachable from the MLflow container (often `http://rustfs:9000`)

- **Resetting the environment**  
  If you want a clean slate, stop the stack and remove volumes:

  ```bash
  docker compose down -v
  docker compose up -d
  ```

- **Logs**

  - MLflow server: `docker compose logs -f mlflow`
  - PostgreSQL: `docker compose logs -f postgres`
  - RustFS: `docker compose logs -f rustfs`

- **Port conflicts**  
  If `5000` (or any other port) is in use, change it in `.env` and restart:
  ```bash
  docker compose down
  docker compose up -d
  ```

---

---

## Migration from MinIO to RustFS

This project recently migrated from MinIO to **RustFS** for artifact storage. RustFS is a high-performance, S3-compatible object storage system written in Rust, offering several advantages:

- **Performance**: RustFS is up to **2.3x faster** than MinIO for 4KB object payloads.
- **Licensing**: Released under the **Apache 2.0** license (MinIO uses AGPL).
- **Efficiency**: Lower memory footprint and high concurrency support.

### Key Changes
- **Environment Variables**: Updated from `MINIO_*` to `RUSTFS_*` (e.g., `RUSTFS_ACCESS_KEY`).
- **Ports**: 
  - API (S3): Internal `9000`, Host mapped to `9090`.
  - Console (UI): Internal `9001`, Host mapped to `9091`.
- **Database**: Added `mlflow db upgrade` to the startup command to ensure schema compatibility across version updates.
- **Client Compatibility**: Uses `boto3` (via a Python script) for automated bucket creation on startup, ensuring full compatibility with RustFS's S3-compliant API.

---

## How It Works (at a Glance)

- MLflow uses **PostgreSQL** as the _backend store_ for experiment/run metadata.
- MLflow uses **RustFS** as the _artifact store_ via S3 APIs.
- Docker Compose wires services on a shared network; MLflow talks to PostgreSQL and RustFS by container name (e.g., `postgres`, `rustfs`).

---

## Next Steps

- Point your training scripts to this server:
  ```bash
  export MLFLOW_TRACKING_URI=http://localhost:5000
  ```
- Start logging runs with `mlflow.start_run()` (Python) or the MLflow CLI.
- Customize the `.env` and `docker-compose.yml` to fit your local workflow (e.g., change image tags, add volumes, etc.).

---

**You now have a fully local MLflow stack with persistent metadata and artifact storage—ideal for development and experimentation.**
