import os

import httpx

API_BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8000")


class APIClient:
    def __init__(self):
        self.base_url = API_BASE_URL
        self.client = httpx.Client(base_url=self.base_url, timeout=120.0)

    def search_by_request(self, request_id: int, threshold: float = 0.7, limit: int = 10) -> dict:
        resp = self.client.post(
            f"/api/semantic-search/by-request/{request_id}",
            params={"threshold": threshold, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    def search_by_rule(self, rule_id: int, threshold: float = 0.7, limit: int = 10) -> dict:
        resp = self.client.post(
            f"/api/semantic-search/by-rule/{rule_id}",
            params={"threshold": threshold, "limit": limit},
        )
        resp.raise_for_status()
        return resp.json()

    def search_by_text(
        self,
        query: str,
        search_in: str = "both",
        threshold: float = 0.7,
        limit: int = 10,
    ) -> dict:
        resp = self.client.post(
            "/api/semantic-search/by-text",
            json={
                "query": query,
                "search_in": search_in,
                "threshold": threshold,
                "limit": limit,
            },
        )
        resp.raise_for_status()
        return resp.json()

    def get_request(self, request_id: int) -> dict:
        resp = self.client.get(f"/api/requests/{request_id}")
        resp.raise_for_status()
        return resp.json()

    def get_rule(self, rule_id: int) -> dict:
        resp = self.client.get(f"/api/physical-rules/{rule_id}")
        resp.raise_for_status()
        return resp.json()

    def run_semantic_review(self, threshold: float | None = None) -> dict:
        params = {}
        if threshold is not None:
            params["threshold"] = threshold
        resp = self.client.post("/api/review/run-semantic", params=params)
        resp.raise_for_status()
        return resp.json()

    def generate_embeddings(self, force: bool = False) -> dict:
        resp = self.client.post("/api/embeddings/generate", params={"force": force})
        resp.raise_for_status()
        return resp.json()

    def get_embedding_status(self) -> dict:
        resp = self.client.get("/api/embeddings/status")
        resp.raise_for_status()
        return resp.json()
