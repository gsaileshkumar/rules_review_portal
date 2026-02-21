# Rules Review Portal

An AI-powered portal for auditing firewall rules against user access requests. The system uses vector embeddings and semantic search to match physical firewall rules with submitted access requests, identifying deficiencies with high accuracy even when address formats differ (e.g., CIDR vs IP range notation).

## Overview

The portal compares user access requests against physical firewall rules using two review strategies:

- **Exact-match review** — fingerprint-based matching that requires identical source, destination, and port sets
- **Semantic review** — embedding-based matching using cosine similarity that tolerates format variations

When rules and requests cannot be matched, the system records them as **deficiencies** for follow-up.

## Tech Stack

| Layer | Technology |
|---|---|
| API | FastAPI 0.115 + Uvicorn |
| Database | PostgreSQL 16 + pgvector |
| ORM / Migrations | SQLAlchemy 2.0 + Alembic |
| Embeddings | Ollama (`qwen3-embedding:0.6b`, 1024 dims) |
| AI Integration | MCP (Model Context Protocol) server |
| Containerization | Docker + Docker Compose |

## Quick Start

```bash
# Start all services (PostgreSQL, API, MCP server)
docker compose up --build

# Seed the database with sample data
curl -X POST http://localhost:8000/api/seed

# Run a semantic review
curl -X POST http://localhost:8000/api/review/run-semantic
```

The API will be available at `http://localhost:8000` and the MCP server at `http://localhost:8090`.

Interactive API docs: `http://localhost:8000/docs`

## Documentation

Full documentation lives in the [`docs/`](docs/) folder:

| Document | Description |
|---|---|
| [Setup Guide](docs/setup.md) | Installation, configuration, and first run |
| [Architecture](docs/architecture.md) | System design and component overview |
| [API Reference](docs/api-reference.md) | All REST endpoints with request/response examples |
| [Database](docs/database.md) | Schema, models, and migration history |
| [Services](docs/services.md) | Business logic and embedding pipeline |
| [MCP Server](docs/mcp-server.md) | AI tool integration via Model Context Protocol |

## Project Structure

```
rules_review_portal/
├── app/                    # FastAPI application
│   ├── models/             # SQLAlchemy ORM models
│   ├── routers/            # API route handlers
│   ├── schemas/            # Pydantic request/response schemas
│   └── services/           # Business logic (review, embeddings)
├── mcp_server/             # MCP server for AI tool integration
├── alembic/                # Database migrations
├── docs/                   # Project documentation
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```
