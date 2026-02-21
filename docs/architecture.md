# Architecture

## System Overview

The Rules Review Portal is a backend service that audits firewall rule coverage. It compares **user access requests** (what users want to be allowed) against **physical firewall rules** (what is actually configured), finding gaps and inconsistencies.

```
┌─────────────────────────────────────────────────────────┐
│                    Client Layer                          │
│                                                         │
│   REST API Clients          AI Assistants (Claude, etc) │
│   (curl, apps, scripts)     via MCP protocol            │
└──────────────┬──────────────────────────┬───────────────┘
               │                          │
               ▼                          ▼
┌──────────────────────┐     ┌────────────────────────────┐
│   FastAPI Service    │     │       MCP Server           │
│   :8000              │◄────│       :8090                │
│                      │     │                            │
│  ┌────────────────┐  │     │  Tools:                    │
│  │    Routers     │  │     │  - find_matching_rules     │
│  │  (8 modules)   │  │     │  - find_matching_requests  │
│  └───────┬────────┘  │     │  - search_rules            │
│          │           │     │  - run_semantic_review     │
│  ┌───────▼────────┐  │     │  - generate_embeddings     │
│  │   Services     │  │     │  - get_request_details     │
│  │  - review      │  │     │  - get_rule_details        │
│  │  - semantic    │  │     └────────────────────────────┘
│  │  - embedding   │  │
│  └───────┬────────┘  │
└──────────┼───────────┘
           │
           ▼
┌──────────────────────┐     ┌────────────────────────────┐
│  PostgreSQL + pgvec  │     │   Ollama (host machine)    │
│  :5432               │     │   :11434                   │
│                      │     │                            │
│  Tables:             │     │  Model:                    │
│  - requests          │     │  qwen3-embedding:0.6b      │
│  - physical_rules    │     │  (1024-dim vectors)        │
│  - deficiencies      │◄────│                            │
│  - semantic_defic.   │     └────────────────────────────┘
│  - phys_rule_sources │
│  - phys_rule_dests   │
└──────────────────────┘
```

---

## Components

### FastAPI Application (`app/`)

The core backend service. It exposes a REST API and contains all business logic.

**Routers** handle HTTP request routing and input validation via Pydantic schemas. Each router delegates to a service or queries the database directly.

**Services** contain business logic:
- `review_service` — exact-match fingerprint comparison
- `semantic_review_service` — vector-based cosine similarity comparison
- `embedding_service` — text normalization and Ollama API calls

**Models** are SQLAlchemy ORM classes that map to PostgreSQL tables.

**Schemas** are Pydantic models used for request/response serialization and validation.

### MCP Server (`mcp_server/`)

An independent Python service that wraps the FastAPI REST API and exposes it as MCP tools. AI assistants (such as Claude) connect to the MCP server via SSE (Server-Sent Events) and call tools conversationally.

The MCP server does not contain business logic — it translates tool calls into HTTP requests to the FastAPI backend.

### PostgreSQL + pgvector

The database stores all entities and their vector embeddings. The `pgvector` extension enables:
- Storing 1024-dimensional float vectors in `vector(1024)` columns
- HNSW index-based approximate nearest neighbor (ANN) search
- Cosine distance queries using the `<=>` operator

### Ollama (Embedding Provider)

Ollama runs locally on the host machine (outside Docker). The FastAPI service calls the Ollama API to generate embeddings for requests and rules. The model `qwen3-embedding:0.6b` produces 1024-dimensional vectors.

---

## Data Flow

### Creating a Request or Rule

```
Client POST /api/requests
  │
  ├─ Validate payload (Pydantic schema)
  ├─ Build normalized embedding text
  │    normalize_address() → build_request_text()
  ├─ Call Ollama API → get 1024-dim vector
  ├─ Persist to PostgreSQL (request + embedding)
  └─ Return response
```

### Exact-Match Review

```
POST /api/review/run
  │
  ├─ Load all physical_rules (with sources/destinations)
  ├─ Load all requests
  ├─ Build fingerprints: (frozenset(sources), frozenset(dests), frozenset(ports))
  ├─ For each rule fingerprint:
  │    ├─ If matching request fingerprint found → MatchedPair
  │    └─ If no match → Deficiency(type="no_matching_request")
  ├─ For each unmatched request → Deficiency(type="no_matching_rule")
  ├─ Persist deficiencies
  └─ Return ReviewResult
```

### Semantic Review

```
POST /api/review/run-semantic?threshold=0.7
  │
  ├─ Load all rules with embeddings
  ├─ Load all requests with embeddings
  │
  ├─ For each rule:
  │    ├─ KNN query: find top-N requests by cosine similarity (HNSW index)
  │    ├─ Best similarity >= threshold → SemanticMatch
  │    └─ Best similarity < threshold → SemanticDeficiency(type="no_matching_request")
  │
  ├─ For each request:
  │    ├─ KNN query: find top-N rules by cosine similarity
  │    ├─ Best similarity >= threshold → SemanticMatch
  │    └─ Best similarity < threshold → SemanticDeficiency(type="no_matching_rule")
  │
  └─ Return SemanticReviewResult
```

### Semantic Search

```
POST /api/semantic-search/by-request/{id}?threshold=0.7&limit=10
  │
  ├─ Fetch request; generate embedding if missing
  ├─ KNN query against physical_rules (HNSW cosine distance)
  ├─ Over-fetch by 4x, then filter by threshold
  └─ Return top-limit matches with similarity scores
```

---

## Why Semantic Matching?

Exact-match review fails when address formats differ. For example:

| User Request | Physical Rule | Exact Match? | Semantic Match? |
|---|---|---|---|
| `10.0.10.0/24` | `10.0.10.0-10.0.10.255` | No | Yes (~0.95) |
| `host 10.0.1.10` | `10.0.1.10` | No | Yes (~1.0) |
| `10.0.0.0/8` | `10.0.0.0/8` | Yes | Yes |

The embedding pipeline normalizes both notations into equivalent text before embedding, so semantically identical networks produce near-identical vectors and high cosine similarity.

**Normalization examples:**

| Input | Normalized Text |
|---|---|
| `10.0.1.10` | `host 10.0.1.10` |
| `10.0.10.0/24` | `subnet 10.0.10.0/24 range 10.0.10.0 to 10.0.10.255` |
| `10.0.10.0-10.0.10.255` | `range 10.0.10.0 to 10.0.10.255 subnet 10.0.10.0/24` |

---

## Deployment Topology

```
Host Machine
├── Ollama service (:11434)
│
└── Docker network
    ├── db      (pgvector/pgvector:pg16, :5432)
    ├── api     (FastAPI, :8000)
    │   └── depends_on: db (health check)
    └── mcp-server (MCP SSE server, :8090)
        └── depends_on: api
```

The API container runs `alembic upgrade head` before starting Uvicorn, ensuring the schema is always up to date.
