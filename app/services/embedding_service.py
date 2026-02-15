import ipaddress
import re

import httpx

from app.config import settings


def normalize_address(address: str) -> str:
    """Expand an IP address/range/CIDR into all equivalent text representations.

    This ensures that semantically equivalent notations like '10.0.10.0/24' and
    '10.0.10.0-10.0.10.255' produce nearly identical text, yielding high cosine
    similarity when embedded.
    """
    address = address.strip()

    # Check for range format: x.x.x.x-y.y.y.y
    range_match = re.match(r"^(\d+\.\d+\.\d+\.\d+)-(\d+\.\d+\.\d+\.\d+)$", address)
    if range_match:
        start_ip = range_match.group(1)
        end_ip = range_match.group(2)
        parts = [f"range {start_ip} to {end_ip}"]
        # Try to express as a single CIDR notation
        try:
            networks = list(
                ipaddress.summarize_address_range(
                    ipaddress.IPv4Address(start_ip),
                    ipaddress.IPv4Address(end_ip),
                )
            )
            if len(networks) == 1:
                parts.append(f"subnet {networks[0]}")
        except (ValueError, TypeError):
            pass
        return " ".join(parts)

    # Check for CIDR format: x.x.x.x/prefix
    if "/" in address:
        try:
            network = ipaddress.IPv4Network(address, strict=False)
            first = str(network.network_address)
            last = str(network.broadcast_address)
            return f"subnet {address} range {first} to {last}"
        except ValueError:
            return address

    # Plain host IP
    return f"host {address}"


def build_request_text(name: str, sources: list[str], destinations: list[str], ports: list[str]) -> str:
    """Build a normalized text representation of a user request for embedding."""
    src_parts = sorted([normalize_address(s) for s in sources])
    dst_parts = sorted([normalize_address(d) for d in destinations])
    port_parts = sorted(ports)
    return (
        f"request {name.lower()} "
        f"sources {' '.join(src_parts)} "
        f"destinations {' '.join(dst_parts)} "
        f"ports {' '.join(port_parts)}"
    )


def build_rule_text(rule_name: str, action: str, sources: list[str], destinations: list[str], ports: list[str]) -> str:
    """Build a normalized text representation of a physical rule for embedding."""
    src_parts = sorted([normalize_address(s) for s in sources])
    dst_parts = sorted([normalize_address(d) for d in destinations])
    port_parts = sorted(ports)
    return (
        f"rule {rule_name.lower()} {action.lower()} "
        f"sources {' '.join(src_parts)} "
        f"destinations {' '.join(dst_parts)} "
        f"ports {' '.join(port_parts)}"
    )


def embed(text: str) -> list[float]:
    """Generate a single embedding vector via Ollama API."""
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embed",
            json={"model": settings.EMBEDDING_MODEL, "input": text},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"][0]


def embed_batch(texts: list[str]) -> list[list[float]]:
    """Generate embedding vectors for multiple texts via Ollama API."""
    with httpx.Client(timeout=300.0) as client:
        resp = client.post(
            f"{settings.OLLAMA_BASE_URL}/api/embed",
            json={"model": settings.EMBEDDING_MODEL, "input": texts},
        )
        resp.raise_for_status()
        return resp.json()["embeddings"]
