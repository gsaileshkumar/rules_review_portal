# API Reference

Base URL: `http://localhost:8000`

Interactive docs (Swagger UI): `http://localhost:8000/docs`

---

## Health

### GET /health

Returns the service health status.

**Response**
```json
{"status": "ok"}
```

---

## Requests

Access requests represent what users or systems want to be permitted through the firewall.

### POST /api/requests

Create a new access request. Automatically generates a vector embedding on creation.

**Request Body**
```json
{
  "name": "web-to-app",
  "request_json": {
    "sources": ["10.0.1.10"],
    "destinations": ["10.0.2.20"],
    "ports": ["443", "80"]
  }
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable name for the request |
| `request_json.sources` | string[] | Yes | Source IP addresses or CIDR ranges |
| `request_json.destinations` | string[] | Yes | Destination IP addresses or CIDR ranges |
| `request_json.ports` | string[] | Yes | Port numbers (as strings) |

**Response** `201`
```json
{
  "request_id": 1,
  "name": "web-to-app",
  "status": "pending",
  "request_json": {
    "sources": ["10.0.1.10"],
    "destinations": ["10.0.2.20"],
    "ports": ["443", "80"]
  },
  "embedding_text": "request web-to-app sources host 10.0.1.10 destinations host 10.0.2.20 ports 443 80",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /api/requests

List all access requests. Optionally filter by status.

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `status` | string | Filter by status (e.g., `pending`, `completed`) |

**Response** `200` — array of request objects (same schema as above)

---

### GET /api/requests/{request_id}

Get a single access request by ID.

**Response** `200` — request object, or `404` if not found.

---

## Physical Rules

Physical rules represent firewall rules as actually configured on network devices.

### POST /api/physical-rules

Create a new physical firewall rule. Automatically generates a vector embedding on creation.

**Request Body**
```json
{
  "rule_name": "RULE-001",
  "firewall_device": "fw-prod-01",
  "action": "allow",
  "sources": ["10.0.1.0/24"],
  "destinations": ["10.0.2.0/24"],
  "ports": ["443", "80"]
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `rule_name` | string | Yes | Rule identifier |
| `firewall_device` | string | Yes | Name of the firewall device |
| `action` | string | Yes | Rule action (`allow`, `deny`, etc.) |
| `sources` | string[] | Yes | Source IP addresses or CIDR ranges |
| `destinations` | string[] | Yes | Destination IP addresses or CIDR ranges |
| `ports` | string[] | Yes | Port numbers (as strings) |

**Response** `201`
```json
{
  "rule_id": 1,
  "rule_name": "RULE-001",
  "firewall_device": "fw-prod-01",
  "action": "allow",
  "sources": ["10.0.1.0/24"],
  "destinations": ["10.0.2.0/24"],
  "ports": ["443", "80"],
  "embedding_text": "rule rule-001 allow sources subnet 10.0.1.0/24 range 10.0.1.0 to 10.0.1.255 destinations subnet 10.0.2.0/24 range 10.0.2.0 to 10.0.2.255 ports 443 80",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

### GET /api/physical-rules

List all physical firewall rules.

**Response** `200` — array of rule objects

---

### GET /api/physical-rules/{rule_id}

Get a single physical rule by ID.

**Response** `200` — rule object, or `404` if not found.

---

## Review

### POST /api/review/run

Run an **exact-match** review. Compares rules and requests using fingerprints (frozensets of sources, destinations, and ports). Clears previous deficiencies before running.

This mode requires exact string matches — format variations like CIDR vs IP range will not match.

**Response** `200`
```json
{
  "matched": [
    {
      "rule_id": 1,
      "request_id": 1,
      "sources": ["10.0.1.10"],
      "destinations": ["10.0.2.20"],
      "ports": ["443"]
    }
  ],
  "unmatched_physical_rules": [
    {
      "deficiency_id": 1,
      "rule_id": 2,
      "rule_name": "RULE-002",
      "sources": ["10.0.3.0/24"],
      "destinations": ["10.0.4.0/24"],
      "ports": ["22"]
    }
  ],
  "unmatched_requests": [
    {
      "deficiency_id": 2,
      "request_id": 2,
      "name": "ssh-access",
      "sources": ["10.0.3.0-10.0.3.255"],
      "destinations": ["10.0.4.0-10.0.4.255"],
      "ports": ["22"]
    }
  ],
  "summary": {
    "total_physical_rules": 7,
    "total_requests": 7,
    "matched_count": 5,
    "unmatched_rules_count": 2,
    "unmatched_requests_count": 2
  }
}
```

---

### POST /api/review/run-semantic

Run a **semantic similarity** review using vector embeddings. Tolerates format variations. Results are stored in the `semantic_deficiencies` table.

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | float | `0.7` | Minimum cosine similarity score (0.0–1.0) to consider a match |

**Response** `200`
```json
{
  "matched": [
    {
      "rule_id": 2,
      "rule_name": "RULE-002",
      "request_id": 2,
      "request_name": "ssh-access",
      "similarity_score": 0.94,
      "similarity_percent": 94
    }
  ],
  "unmatched_physical_rules": [
    {
      "rule_id": 3,
      "rule_name": "RULE-003",
      "best_match_request_id": 5,
      "similarity_score": 0.45,
      "similarity_percent": 45
    }
  ],
  "unmatched_requests": [],
  "summary": {
    "total_physical_rules": 7,
    "total_requests": 7,
    "matched_count": 6,
    "unmatched_rules_count": 1,
    "unmatched_requests_count": 0,
    "threshold_used": 0.7
  }
}
```

---

## Deficiencies

Deficiencies are exact-match mismatches recorded by `/api/review/run`.

### GET /api/deficiencies

List all deficiencies. Optionally filter by type.

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `type` | string | Filter by type: `no_matching_request` or `no_matching_rule` |

**Response** `200`
```json
[
  {
    "deficiency_id": 1,
    "type": "no_matching_request",
    "rule_id": 2,
    "request_id": null,
    "created_at": "2024-01-15T10:31:00Z"
  }
]
```

---

### GET /api/deficiencies/{deficiency_id}

Get a single deficiency by ID.

**Response** `200` — deficiency object, or `404` if not found.

---

## Semantic Deficiencies

Semantic deficiencies are similarity-based mismatches recorded by `/api/review/run-semantic`.

### GET /api/semantic-deficiencies

List all semantic deficiencies.

**Query Parameters**

| Parameter | Type | Description |
|---|---|---|
| `type` | string | Filter by type: `no_matching_request` or `no_matching_rule` |

**Response** `200`
```json
[
  {
    "id": 1,
    "type": "no_matching_request",
    "rule_id": 3,
    "request_id": null,
    "best_match_request_id": 5,
    "best_match_rule_id": null,
    "similarity_score": 0.45,
    "threshold_used": 0.7,
    "created_at": "2024-01-15T10:32:00Z"
  }
]
```

---

### GET /api/semantic-deficiencies/{deficiency_id}

Get a single semantic deficiency by ID.

---

## Semantic Search

On-demand similarity search without running a full review.

### POST /api/semantic-search/by-request/{request_id}

Find physical rules semantically similar to a given access request.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `request_id` | integer | ID of the access request |

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `threshold` | float | `0.7` | Minimum cosine similarity score |
| `limit` | integer | `10` | Maximum number of results |

**Response** `200`
```json
{
  "query_id": 1,
  "query_type": "request",
  "query_text": "request web-to-app sources host 10.0.1.10 ...",
  "matches": [
    {
      "rule_id": 1,
      "name": "RULE-001",
      "sources": ["10.0.1.0/24"],
      "destinations": ["10.0.2.0/24"],
      "ports": ["443", "80"],
      "similarity_score": 0.96
    }
  ],
  "total_matches": 1,
  "threshold_used": 0.7
}
```

---

### POST /api/semantic-search/by-rule/{rule_id}

Find access requests semantically similar to a given physical rule.

**Path Parameters**

| Parameter | Type | Description |
|---|---|---|
| `rule_id` | integer | ID of the physical rule |

**Query Parameters** — same as `by-request`

**Response** — same structure with `query_type: "rule"` and `request_id` in each match.

---

### POST /api/semantic-search/by-text

Free-form text search across rules, requests, or both.

**Request Body**
```json
{
  "query": "allow traffic from 10.0.1.x to 10.0.2.x on port 443",
  "search_in": "both",
  "threshold": 0.7,
  "limit": 10
}
```

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | string | — | Natural language or technical query |
| `search_in` | string | `"both"` | Target entities: `"rules"`, `"requests"`, or `"both"` |
| `threshold` | float | `0.7` | Minimum similarity score |
| `limit` | integer | `10` | Maximum results |

**Response** `200`
```json
{
  "query": "allow traffic from 10.0.1.x to 10.0.2.x on port 443",
  "matches": [
    {
      "entity_type": "rule",
      "rule_id": 1,
      "name": "RULE-001",
      "sources": ["10.0.1.0/24"],
      "destinations": ["10.0.2.0/24"],
      "ports": ["443"],
      "similarity_score": 0.89
    },
    {
      "entity_type": "request",
      "request_id": 1,
      "name": "web-to-app",
      "sources": ["10.0.1.10"],
      "destinations": ["10.0.2.20"],
      "ports": ["443"],
      "similarity_score": 0.85
    }
  ],
  "total_matches": 2,
  "threshold_used": 0.7
}
```

---

## Embeddings

### GET /api/embeddings/status

Get embedding coverage statistics.

**Response** `200`
```json
{
  "total_requests": 7,
  "requests_with_embeddings": 7,
  "total_rules": 7,
  "rules_with_embeddings": 7
}
```

---

### POST /api/embeddings/generate

Batch generate embeddings for all requests and rules that are missing them.

**Query Parameters**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `force` | boolean | `false` | If `true`, regenerates embeddings even for records that already have them |

**Response** `200`
```json
{
  "requests_generated": 2,
  "rules_generated": 3,
  "requests_skipped": 5,
  "rules_skipped": 4
}
```

---

## Seed Data

### POST /api/seed

Populate the database with sample access requests and physical rules for testing. Creates 7 requests and 7 rules with embeddings.

**Response** `200`
```json
{"message": "Seeded 7 requests and 7 physical rules"}
```

---

## Error Responses

All endpoints return standard HTTP error codes:

| Status | Meaning |
|---|---|
| `404` | Resource not found |
| `422` | Validation error (invalid request body or parameters) |
| `500` | Internal server error (e.g., Ollama is unreachable) |

Validation errors return a Pydantic error body:
```json
{
  "detail": [
    {
      "loc": ["body", "name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```
