# Setup Guide

## Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Docker | 24+ | Required for containerised deployment |
| Docker Compose | 2.x | Included with Docker Desktop |
| Ollama | Latest | Required for embedding generation |
| Python | 3.11+ | Only needed for local development without Docker |

## Running with Docker (recommended)

### 1. Start Ollama and pull the embedding model

The embedding service runs on your host machine and is accessed by the Docker containers via `host.docker.internal`.

```bash
# Start Ollama (if not already running as a system service)
ollama serve

# Pull the embedding model
ollama pull qwen3-embedding:0.6b
```

### 2. Start the application stack

```bash
git clone <repository-url>
cd rules_review_portal

docker compose up --build
```

This starts three services:
- **db** — PostgreSQL 16 with pgvector on port `5432`
- **api** — FastAPI application on port `8000` (runs Alembic migrations on startup)
- **mcp-server** — MCP server on port `8090`

### 3. Verify the services are running

```bash
curl http://localhost:8000/health
# {"status": "ok"}
```

Interactive API docs are available at `http://localhost:8000/docs`.

### 4. Seed the database (optional)

Load sample data to explore the system:

```bash
curl -X POST http://localhost:8000/api/seed
```

This creates 7 sample access requests and 7 sample firewall rules with pre-generated embeddings.

---

## Environment Variables

All configuration is managed via environment variables. Create a `.env` file in the project root to override defaults.

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql://portal_user:portal_pass@localhost:5432/rules_review` | PostgreSQL connection string |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API base URL |
| `EMBEDDING_MODEL` | `qwen3-embedding:0.6b` | Ollama model name for embeddings |
| `EMBEDDING_DIMENSIONS` | `1024` | Vector dimensions (must match the model) |
| `SIMILARITY_THRESHOLD` | `0.7` | Default cosine similarity threshold for semantic matching |

> **Docker note:** The `docker-compose.yml` sets `OLLAMA_BASE_URL=http://host.docker.internal:11434` so containers can reach the host Ollama service.

---

## Running Locally (without Docker)

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Start PostgreSQL with pgvector

You need a PostgreSQL instance with the `pgvector` extension. The easiest option is the pgvector Docker image:

```bash
docker run -d \
  --name rules-db \
  -e POSTGRES_USER=portal_user \
  -e POSTGRES_PASSWORD=portal_pass \
  -e POSTGRES_DB=rules_review \
  -p 5432:5432 \
  pgvector/pgvector:pg16
```

### 3. Run database migrations

```bash
alembic upgrade head
```

### 4. Start the API

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 5. Start the MCP server (optional)

```bash
pip install -r requirements-mcp.txt
python -m mcp_server.server
```

---

## First Run Workflow

After starting the services, a typical first run looks like:

```bash
# 1. Check health
curl http://localhost:8000/health

# 2. Seed sample data
curl -X POST http://localhost:8000/api/seed

# 3. Check embedding coverage
curl http://localhost:8000/api/embeddings/status

# 4. Run exact-match review
curl -X POST http://localhost:8000/api/review/run

# 5. Run semantic review
curl -X POST "http://localhost:8000/api/review/run-semantic?threshold=0.7"

# 6. View deficiencies
curl http://localhost:8000/api/deficiencies
curl http://localhost:8000/api/semantic-deficiencies
```

---

## Stopping and Cleaning Up

```bash
# Stop containers
docker compose down

# Remove containers and database volume
docker compose down -v
```
