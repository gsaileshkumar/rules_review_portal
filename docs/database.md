# Database

## Overview

The portal uses **PostgreSQL 16** with the **pgvector** extension. Vector columns store 1024-dimensional embeddings used for semantic similarity search via HNSW indexes.

Database: `rules_review`
Default user: `portal_user`
Default password: `portal_pass`

---

## Schema

### Table: `requests`

Stores user access requests.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `request_id` | `integer` | No | auto-increment | Primary key |
| `name` | `varchar(255)` | No | — | Request name |
| `status` | `varchar(50)` | No | `'pending'` | Status (e.g., `pending`, `completed`) |
| `request_json` | `jsonb` | No | — | Sources, destinations, ports as JSON |
| `created_at` | `timestamptz` | No | `now()` | Creation timestamp |
| `updated_at` | `timestamptz` | No | `now()` | Last update timestamp |
| `embedding_text` | `text` | Yes | `null` | Normalized text used to generate the embedding |
| `embedding` | `vector(1024)` | Yes | `null` | pgvector embedding |

**`request_json` shape:**
```json
{
  "sources": ["10.0.1.10", "10.0.1.11"],
  "destinations": ["10.0.2.20"],
  "ports": ["443", "80"]
}
```

**Indexes:**
- Primary key on `request_id`
- HNSW index on `embedding` using cosine distance (added in migration `004`)

---

### Table: `physical_rules`

Stores physical firewall rules.

| Column | Type | Nullable | Default | Description |
|---|---|---|---|---|
| `rule_id` | `integer` | No | auto-increment | Primary key |
| `rule_name` | `varchar(255)` | No | — | Rule identifier |
| `firewall_device` | `varchar(255)` | No | — | Firewall device name |
| `ports` | `text[]` | No | — | Array of port numbers |
| `action` | `varchar(50)` | No | — | Rule action (`allow`, `deny`, etc.) |
| `created_at` | `timestamptz` | No | `now()` | Creation timestamp |
| `embedding_text` | `text` | Yes | `null` | Normalized text for embedding |
| `embedding` | `vector(1024)` | Yes | `null` | pgvector embedding |

**Indexes:**
- Primary key on `rule_id`
- HNSW index on `embedding` using cosine distance (added in migration `004`)

---

### Table: `physical_rule_sources`

Source IP addresses or CIDR ranges for each physical rule. One-to-many with `physical_rules`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `integer` | No | Primary key |
| `rule_id` | `integer` | No | Foreign key → `physical_rules.rule_id` |
| `address` | `varchar(255)` | No | IP address, CIDR, or range string |

---

### Table: `physical_rule_destinations`

Destination IP addresses or CIDR ranges. Same structure as `physical_rule_sources`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `integer` | No | Primary key |
| `rule_id` | `integer` | No | Foreign key → `physical_rules.rule_id` |
| `address` | `varchar(255)` | No | IP address, CIDR, or range string |

---

### Table: `deficiencies`

Exact-match deficiencies recorded by the `/api/review/run` endpoint. Cleared and repopulated on each review run.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `deficiency_id` | `integer` | No | Primary key |
| `type` | `varchar(50)` | No | `no_matching_request` or `no_matching_rule` |
| `rule_id` | `integer` | Yes | Physical rule with no matching request |
| `request_id` | `integer` | Yes | Request with no matching rule |
| `created_at` | `timestamptz` | No | Timestamp |

Exactly one of `rule_id` or `request_id` is set per row.

---

### Table: `semantic_deficiencies`

Semantic similarity deficiencies recorded by `/api/review/run-semantic`.

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `integer` | No | Primary key |
| `type` | `varchar(50)` | No | `no_matching_request` or `no_matching_rule` |
| `rule_id` | `integer` | Yes | Rule that had no match (for `no_matching_request`) |
| `request_id` | `integer` | Yes | Request that had no match (for `no_matching_rule`) |
| `best_match_request_id` | `integer` | Yes | Closest request found (below threshold) |
| `best_match_rule_id` | `integer` | Yes | Closest rule found (below threshold) |
| `similarity_score` | `float` | Yes | Best cosine similarity score found |
| `threshold_used` | `float` | No | Threshold applied during this review |
| `created_at` | `timestamptz` | No | Timestamp |

---

### View: `physical_rules_view`

A denormalized view that aggregates `physical_rule_sources` and `physical_rule_destinations` into arrays on each rule row. Useful for reporting queries.

---

## Migrations

Migrations are managed with **Alembic**. Migration files live in `alembic/versions/`.

### Running migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Check current revision
alembic current

# View migration history
alembic history

# Roll back one step
alembic downgrade -1
```

### Migration history

| Revision | File | Description |
|---|---|---|
| `001` | `001_initial_schema.py` | Creates `requests`, `physical_rules`, `physical_rule_sources`, `physical_rule_destinations` |
| `002` | `002_add_deficiencies.py` | Creates `deficiencies` table |
| `003` | `003_add_physical_rules_view.py` | Creates `physical_rules_view` |
| `004` | `004_add_pgvector_embeddings.py` | Enables pgvector extension, adds `embedding_text` and `embedding` columns, creates HNSW indexes, creates `semantic_deficiencies` table |

### Adding a new migration

```bash
# Generate a new migration (auto-detect changes from models)
alembic revision --autogenerate -m "describe_what_changes"

# Or create an empty migration
alembic revision -m "describe_what_changes"
```

---

## pgvector

The `pgvector` extension enables vector operations in PostgreSQL.

### HNSW Indexes

Migration `004` creates HNSW (Hierarchical Navigable Small World) indexes on the `embedding` columns for fast approximate nearest neighbor (ANN) search:

```sql
CREATE INDEX ON requests USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON physical_rules USING hnsw (embedding vector_cosine_ops);
```

HNSW indexes activate automatically when queries use the cosine distance operator (`<=>`), enabling sub-linear KNN search even over large datasets.

### Cosine Distance Queries

The API uses cosine distance (not similarity) for KNN ordering. Cosine similarity is derived as:

```
similarity = 1.0 - cosine_distance
```

A similarity of `1.0` means identical vectors; `0.0` means orthogonal.

**Example KNN query:**
```sql
SELECT rule_id, (embedding <=> '[...]'::vector) AS distance
FROM physical_rules
WHERE embedding IS NOT NULL
ORDER BY distance
LIMIT 40;
```

---

## ORM Models

The SQLAlchemy models are in `app/models/`. All use the declarative `Base` from `app/database.py`.

| Model | Table | Key Fields |
|---|---|---|
| `Request` | `requests` | `request_id`, `request_json`, `embedding` |
| `PhysicalRule` | `physical_rules` | `rule_id`, `action`, `ports`, `embedding` |
| `PhysicalRuleSource` | `physical_rule_sources` | `id`, `rule_id`, `address` |
| `PhysicalRuleDestination` | `physical_rule_destinations` | `id`, `rule_id`, `address` |
| `Deficiency` | `deficiencies` | `deficiency_id`, `type`, `rule_id`, `request_id` |
| `SemanticDeficiency` | `semantic_deficiencies` | `id`, `type`, `similarity_score`, `threshold_used` |

`PhysicalRule` has SQLAlchemy relationships to `PhysicalRuleSource` and `PhysicalRuleDestination` via the `sources` and `destinations` attributes, loaded with `joinedload` in query handlers.
