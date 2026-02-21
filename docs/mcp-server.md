# MCP Server

The MCP (Model Context Protocol) server exposes the Rules Review Portal's capabilities as tools that AI assistants can call conversationally. It runs as a separate service on port `8090`.

## What is MCP?

The Model Context Protocol is a standard for connecting AI models to external tools and data sources. An MCP server registers a set of named tools; an MCP client (such as Claude) can discover and call those tools during a conversation.

## Architecture

```
AI Assistant (Claude)
       │
       │  SSE (Server-Sent Events)
       ▼
MCP Server (:8090)               ← mcp_server/
  ├── server.py   (Starlette app, SSE transport)
  ├── tools.py    (tool definitions + handlers)
  └── api_client.py (HTTP → FastAPI)
       │
       │  REST HTTP
       ▼
FastAPI API (:8000)
```

The MCP server is a thin adapter. It does not contain business logic — all operations are delegated to the FastAPI backend via HTTP.

## Transport

The server uses SSE (Server-Sent Events) transport:

- **`GET /sse`** — AI client connects here to open the SSE stream
- **`POST /messages/`** — AI client sends tool call messages here

The server is built with Starlette and the `mcp` Python library.

## Available Tools

### `find_matching_rules`

Find physical firewall rules semantically similar to a given access request.

| Input | Type | Required | Description |
|---|---|---|---|
| `request_id` | integer | Yes | The access request ID |
| `threshold` | float | No | Minimum similarity score 0–1 (default: 0.7) |
| `limit` | integer | No | Maximum results to return (default: 10) |

**Example output:**
```
Semantic search for Request 1 (threshold: 0.7):

Query text: request web-to-app sources host 10.0.1.10...

Matching physical rules (2 found):
  - ID=1 | RULE-001 | Similarity: 96%
    Sources: 10.0.1.0/24
    Destinations: 10.0.2.0/24
    Ports: 443, 80
```

---

### `find_matching_requests`

Find access requests semantically similar to a given physical rule.

| Input | Type | Required | Description |
|---|---|---|---|
| `rule_id` | integer | Yes | The physical rule ID |
| `threshold` | float | No | Minimum similarity score (default: 0.7) |
| `limit` | integer | No | Maximum results (default: 10) |

---

### `search_rules`

Free-text semantic search across rules, requests, or both.

| Input | Type | Required | Description |
|---|---|---|---|
| `query` | string | Yes | Natural language or technical query |
| `search_in` | string | No | `"rules"`, `"requests"`, or `"both"` (default: `"both"`) |
| `threshold` | float | No | Minimum similarity score (default: 0.7) |
| `limit` | integer | No | Maximum results (default: 10) |

---

### `get_request_details`

Fetch the full details of a specific access request.

| Input | Type | Required | Description |
|---|---|---|---|
| `request_id` | integer | Yes | The access request ID |

Returns the full JSON representation of the request.

---

### `get_rule_details`

Fetch the full details of a specific physical firewall rule.

| Input | Type | Required | Description |
|---|---|---|---|
| `rule_id` | integer | Yes | The physical rule ID |

Returns the full JSON representation of the rule.

---

### `run_semantic_review`

Run a full semantic comparison between all access requests and physical rules. Stores results in the `semantic_deficiencies` table.

| Input | Type | Required | Description |
|---|---|---|---|
| `threshold` | float | No | Minimum similarity score (default: configured `SIMILARITY_THRESHOLD`) |

**Example output:**
```
=== Semantic Review Results ===
Total physical rules:  7
Total requests:        7
Matched pairs:         6
Unmatched rules:       1
Unmatched requests:    0
Similarity threshold:  0.7

--- Matched Pairs ---
  Rule 1 'RULE-001' <-> Request 1 'web-to-app' (96% similarity)
  ...

--- Unmatched Physical Rules (deficiencies) ---
  Rule 7 'RULE-007' — best match: Request 5 @ 45%

--- Unmatched Requests (deficiencies) ---
```

---

### `generate_embeddings`

Generate or regenerate vector embeddings for all rules and requests.

| Input | Type | Required | Description |
|---|---|---|---|
| `force` | boolean | No | If `true`, regenerates existing embeddings (default: `false`) |

**Example output:**
```
Embedding generation complete:
  Requests: 2 generated, 5 skipped
  Rules:    3 generated, 4 skipped
```

---

## Connecting Claude to the MCP Server

### In Claude Desktop (via `claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "rules-review-portal": {
      "url": "http://localhost:8090/sse"
    }
  }
}
```

### In `.mcp.json` (project-level, for Claude Code)

The project root contains a `.mcp.json` file that configures the MCP server for use with Claude Code sessions. The server connects to the running MCP service at `http://localhost:8090/sse`.

---

## API Client (`mcp_server/api_client.py`)

The `APIClient` class wraps all HTTP calls to the FastAPI backend. It is instantiated once at server startup and injected into the tool handlers.

Base URL is configured via the `API_BASE_URL` environment variable (default: `http://localhost:8000`). In Docker Compose, this is set to `http://api:8000` so the MCP container can reach the API container by service name.

**Methods:**
| Method | HTTP call |
|---|---|
| `search_by_request(request_id, threshold, limit)` | `POST /api/semantic-search/by-request/{id}` |
| `search_by_rule(rule_id, threshold, limit)` | `POST /api/semantic-search/by-rule/{id}` |
| `search_by_text(query, search_in, threshold, limit)` | `POST /api/semantic-search/by-text` |
| `get_request(request_id)` | `GET /api/requests/{id}` |
| `get_rule(rule_id)` | `GET /api/physical-rules/{id}` |
| `run_semantic_review(threshold)` | `POST /api/review/run-semantic` |
| `generate_embeddings(force)` | `POST /api/embeddings/generate` |

---

## Running the MCP Server

### With Docker Compose

The MCP server starts automatically as part of `docker compose up`. It depends on the `api` service being healthy before starting.

```yaml
mcp-server:
  build:
    context: .
    dockerfile: Dockerfile.mcp
  ports:
    - "8090:8090"
  environment:
    API_BASE_URL: http://api:8000
  depends_on:
    - api
```

### Standalone

```bash
pip install -r requirements-mcp.txt
API_BASE_URL=http://localhost:8000 python -m mcp_server.server
```

---

## Dependencies

MCP server dependencies are kept separate in `requirements-mcp.txt` to minimize the image size:

```
mcp==1.2.0
httpx==0.27.0
```

The MCP server uses a dedicated `Dockerfile.mcp` that only installs MCP dependencies, not the full FastAPI stack.
