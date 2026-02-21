# Services

Business logic lives in `app/services/`. There are three service modules.

---

## Embedding Service (`app/services/embedding_service.py`)

Handles text normalization and communication with the Ollama embedding API.

### Address Normalization

The key challenge is that the same network can be expressed in multiple formats:
- Single host: `10.0.1.10`
- CIDR: `10.0.10.0/24`
- Range: `10.0.10.0-10.0.10.255`

The `normalize_address(address)` function expands each format into a canonical multi-token text representation so that semantically equivalent addresses produce near-identical embeddings.

| Input | Normalized Output |
|---|---|
| `10.0.1.10` | `host 10.0.1.10` |
| `10.0.10.0/24` | `subnet 10.0.10.0/24 range 10.0.10.0 to 10.0.10.255` |
| `10.0.10.0-10.0.10.255` | `range 10.0.10.0 to 10.0.10.255 subnet 10.0.10.0/24` |

For CIDR inputs, Python's `ipaddress.IPv4Network` is used to compute the broadcast address. For range inputs, `ipaddress.summarize_address_range` attempts to express the range as a single CIDR.

### Embedding Text Builders

**`build_request_text(name, sources, destinations, ports)`**

Produces a normalized text string for a user request:
```
request web-to-app sources host 10.0.1.10 destinations host 10.0.2.20 ports 443 80
```

- Source addresses are individually normalized and sorted.
- Destination addresses are individually normalized and sorted.
- Ports are sorted.

**`build_rule_text(rule_name, action, sources, destinations, ports)`**

Produces a normalized text string for a physical rule:
```
rule rule-001 allow sources subnet 10.0.1.0/24 range 10.0.1.0 to 10.0.1.255 destinations host 10.0.2.20 ports 443
```

Same normalization as requests, but prefixed with `rule <name> <action>`.

### Embedding API

**`embed(text) -> list[float]`**

Calls `POST /api/embed` on the Ollama API with a single text string. Returns a 1024-dimensional float vector. Timeout: 120 seconds.

**`embed_batch(texts) -> list[list[float]]`**

Calls `POST /api/embed` with multiple text strings in one request. Returns a list of vectors. Timeout: 300 seconds.

Ollama request format:
```json
{
  "model": "qwen3-embedding:0.6b",
  "input": "text to embed"
}
```

The response field used is `embeddings[0]` for single inputs, or `embeddings` (list) for batch inputs.

---

## Review Service (`app/services/review_service.py`)

Performs exact-match review between physical rules and user requests.

### Algorithm

1. **Load all data** — fetches all `PhysicalRule` records (with `sources` and `destinations` via joinedload) and all `Request` records.

2. **Build fingerprints** — for each entity, creates a tuple of three frozensets:
   ```python
   fingerprint = (
       frozenset(sources),       # set of source address strings
       frozenset(destinations),  # set of destination address strings
       frozenset(ports),         # set of port strings
   )
   ```

3. **Build lookup map** — creates a dict mapping each request fingerprint to its `request_id`.

4. **Match rules** — for each rule fingerprint:
   - If a matching request fingerprint exists → record as `MatchedPair`.
   - If no match → create a `Deficiency(type="no_matching_request", rule_id=...)`.

5. **Find unmatched requests** — requests not referenced in any match → create `Deficiency(type="no_matching_rule", request_id=...)`.

6. **Persist** — all new deficiencies are flushed and committed. Previous deficiencies are deleted at the start of each run.

### Limitations

- Fingerprint comparison is string-exact. `10.0.10.0/24` and `10.0.10.0-10.0.10.255` will not match even though they represent the same network.
- This is by design — the semantic review service handles format variations.

### Complexity

O(R + P) where R = number of requests and P = number of physical rules, due to the hash-map lookup.

---

## Semantic Review Service (`app/services/semantic_review_service.py`)

Performs similarity-based review using vector embeddings and the pgvector HNSW index.

### Algorithm

1. **Load data** — fetches all rules and requests that have embeddings.

2. **For each rule**, find the best-matching request:
   - Run a KNN query against the `requests` table using cosine distance.
   - Query uses the pgvector `<=>` operator, which activates the HNSW index.
   - Best similarity ≥ threshold → record as a semantic match.
   - Best similarity < threshold → record as `SemanticDeficiency(type="no_matching_request")`.

3. **For each request**, find the best-matching rule:
   - Run a KNN query against the `physical_rules` table.
   - Best similarity ≥ threshold → semantic match.
   - Best similarity < threshold → `SemanticDeficiency(type="no_matching_rule")`.

4. **Persist** — previous semantic deficiencies are cleared, new ones are committed.

### KNN Over-fetch Strategy

The semantic search endpoints over-fetch results by 4x before applying the similarity threshold:

```python
.limit(limit * 4)
```

This compensates for the fact that HNSW is approximate — some results near the threshold boundary may not be returned in exact order. Over-fetching and then filtering in Python ensures the threshold is applied accurately.

### Similarity Score Calculation

```python
distance = rule.embedding <=> request.embedding   # cosine distance (0.0 to 2.0)
similarity = round(1.0 - distance, 4)              # cosine similarity (-1.0 to 1.0)
```

In practice, normalized vectors produce similarity scores in the range [0.0, 1.0]. A score of `1.0` means the vectors are identical.

### Threshold Configuration

The default threshold is `0.7`, configurable via the `SIMILARITY_THRESHOLD` environment variable. It can also be overridden per request via the `threshold` query parameter.

A threshold of `0.7` means: entities must be at least 70% similar (by cosine similarity of their embeddings) to be considered a match.

---

## Configuration (`app/config.py`)

All service configuration comes from `app/config.py` via `pydantic-settings`:

```python
class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://portal_user:portal_pass@localhost:5432/rules_review"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    EMBEDDING_MODEL: str = "qwen3-embedding:0.6b"
    EMBEDDING_DIMENSIONS: int = 1024
    SIMILARITY_THRESHOLD: float = 0.7
```

Settings are loaded from environment variables first, then from a `.env` file if present.
