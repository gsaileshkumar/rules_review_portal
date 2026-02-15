import json
from typing import Any

from mcp.server import Server
from mcp.types import Tool, TextContent

from mcp_server.api_client import APIClient


def _format_matches(matches: list[dict]) -> str:
    if not matches:
        return "No matches found."
    lines = []
    for m in matches:
        entity_id = m.get("rule_id") or m.get("request_id")
        name = m.get("name", "Unknown")
        score = m.get("similarity_percent", round(m.get("similarity_score", 0) * 100))
        sources = ", ".join(m.get("sources", []))
        destinations = ", ".join(m.get("destinations", []))
        ports = ", ".join(m.get("ports", []))
        lines.append(
            f"  - ID={entity_id} | {name} | Similarity: {score}%\n"
            f"    Sources: {sources}\n"
            f"    Destinations: {destinations}\n"
            f"    Ports: {ports}"
        )
    return "\n".join(lines)


def _format_review_result(result: dict) -> str:
    summary = result.get("summary", {})
    lines = [
        "=== Semantic Review Results ===",
        f"Total physical rules:  {summary.get('total_physical_rules', 0)}",
        f"Total requests:        {summary.get('total_requests', 0)}",
        f"Matched pairs:         {summary.get('matched_count', 0)}",
        f"Unmatched rules:       {summary.get('unmatched_rules_count', 0)}",
        f"Unmatched requests:    {summary.get('unmatched_requests_count', 0)}",
        f"Similarity threshold:  {summary.get('threshold_used', 0.7)}",
        "",
        "--- Matched Pairs ---",
    ]
    for m in result.get("matched", []):
        lines.append(
            f"  Rule {m['rule_id']} '{m['rule_name']}' <-> "
            f"Request {m['request_id']} '{m['request_name']}' "
            f"({m.get('similarity_percent', round(m.get('similarity_score', 0)*100))}% similarity)"
        )

    lines.append("\n--- Unmatched Physical Rules (deficiencies) ---")
    for r in result.get("unmatched_physical_rules", []):
        best = f"best match: Request {r['best_match_request_id']} @ {round((r.get('similarity_score') or 0)*100)}%" if r.get("best_match_request_id") else "no candidates"
        lines.append(f"  Rule {r['rule_id']} '{r['rule_name']}' — {best}")

    lines.append("\n--- Unmatched Requests (deficiencies) ---")
    for r in result.get("unmatched_requests", []):
        best = f"best match: Rule {r['best_match_rule_id']} @ {round((r.get('similarity_score') or 0)*100)}%" if r.get("best_match_rule_id") else "no candidates"
        lines.append(f"  Request {r['request_id']} '{r['request_name']}' — {best}")

    return "\n".join(lines)


def register_tools(app: Server, client: APIClient) -> None:
    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="find_matching_rules",
                description="Find physical firewall rules semantically similar to a given user request ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "integer", "description": "The user request ID"},
                        "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.7)"},
                        "limit": {"type": "integer", "description": "Max results to return (default 10)"},
                    },
                    "required": ["request_id"],
                },
            ),
            Tool(
                name="find_matching_requests",
                description="Find user requests semantically similar to a given physical rule ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "integer", "description": "The physical rule ID"},
                        "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.7)"},
                        "limit": {"type": "integer", "description": "Max results to return (default 10)"},
                    },
                    "required": ["rule_id"],
                },
            ),
            Tool(
                name="search_rules",
                description="Free-text semantic search across rules and/or requests.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Natural language or technical query"},
                        "search_in": {"type": "string", "enum": ["rules", "requests", "both"], "description": "Which entities to search"},
                        "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.7)"},
                        "limit": {"type": "integer", "description": "Max results to return (default 10)"},
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name="get_request_details",
                description="Get full details of a specific user request by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "request_id": {"type": "integer", "description": "The user request ID"},
                    },
                    "required": ["request_id"],
                },
            ),
            Tool(
                name="get_rule_details",
                description="Get full details of a specific physical firewall rule by ID.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "rule_id": {"type": "integer", "description": "The physical rule ID"},
                    },
                    "required": ["rule_id"],
                },
            ),
            Tool(
                name="run_semantic_review",
                description="Run a full semantic comparison between all user requests and physical rules. Stores results in semantic_deficiencies table.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "threshold": {"type": "number", "description": "Minimum similarity score 0-1 (default 0.7)"},
                    },
                },
            ),
            Tool(
                name="generate_embeddings",
                description="Generate or regenerate vector embeddings for all rules and requests.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "force": {"type": "boolean", "description": "If true, regenerate even existing embeddings (default false)"},
                    },
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        try:
            if name == "find_matching_rules":
                result = client.search_by_request(
                    request_id=arguments["request_id"],
                    threshold=arguments.get("threshold", 0.7),
                    limit=arguments.get("limit", 10),
                )
                text = (
                    f"Semantic search for Request {result['query_id']} "
                    f"(threshold: {result['threshold_used']}):\n\n"
                    f"Query text: {result['query_text'][:200]}...\n\n"
                    f"Matching physical rules ({result['total_matches']} found):\n"
                    + _format_matches(result["matches"])
                )

            elif name == "find_matching_requests":
                result = client.search_by_rule(
                    rule_id=arguments["rule_id"],
                    threshold=arguments.get("threshold", 0.7),
                    limit=arguments.get("limit", 10),
                )
                text = (
                    f"Semantic search for Rule {result['query_id']} "
                    f"(threshold: {result['threshold_used']}):\n\n"
                    f"Query text: {result['query_text'][:200]}...\n\n"
                    f"Matching user requests ({result['total_matches']} found):\n"
                    + _format_matches(result["matches"])
                )

            elif name == "search_rules":
                result = client.search_by_text(
                    query=arguments["query"],
                    search_in=arguments.get("search_in", "both"),
                    threshold=arguments.get("threshold", 0.7),
                    limit=arguments.get("limit", 10),
                )
                text = (
                    f"Text search for '{result['query']}' "
                    f"(threshold: {result['threshold_used']}):\n\n"
                    f"Results ({result['total_matches']} found):\n"
                    + _format_matches(result["matches"])
                )

            elif name == "get_request_details":
                result = client.get_request(arguments["request_id"])
                text = json.dumps(result, indent=2)

            elif name == "get_rule_details":
                result = client.get_rule(arguments["rule_id"])
                text = json.dumps(result, indent=2)

            elif name == "run_semantic_review":
                result = client.run_semantic_review(
                    threshold=arguments.get("threshold")
                )
                text = _format_review_result(result)

            elif name == "generate_embeddings":
                result = client.generate_embeddings(force=arguments.get("force", False))
                text = (
                    f"Embedding generation complete:\n"
                    f"  Requests: {result['requests_generated']} generated, {result['requests_skipped']} skipped\n"
                    f"  Rules:    {result['rules_generated']} generated, {result['rules_skipped']} skipped"
                )

            else:
                text = f"Unknown tool: {name}"

        except Exception as e:
            text = f"Error calling tool '{name}': {e}"

        return [TextContent(type="text", text=text)]
