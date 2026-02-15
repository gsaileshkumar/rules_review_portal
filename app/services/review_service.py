from sqlalchemy.orm import Session, joinedload

from app.models.deficiency import Deficiency
from app.models.physical_rule import PhysicalRule
from app.models.request import Request
from app.schemas.review import (
    MatchedPair,
    ReviewResult,
    ReviewSummary,
    UnmatchedRequest,
    UnmatchedRule,
)


def _build_fingerprint(sources: list[str], destinations: list[str], ports: list[str]) -> tuple:
    return (
        frozenset(sources),
        frozenset(destinations),
        frozenset(ports),
    )


def run_review(db: Session) -> ReviewResult:
    # Clear previous deficiencies
    db.query(Deficiency).delete()
    db.flush()

    physical_rules = (
        db.query(PhysicalRule)
        .options(joinedload(PhysicalRule.sources), joinedload(PhysicalRule.destinations))
        .all()
    )
    user_requests = db.query(Request).all()

    # Build fingerprints for physical rules
    rule_fingerprints: dict[int, tuple] = {}
    rule_details: dict[int, dict] = {}
    for rule in physical_rules:
        sources = [s.address for s in rule.sources]
        destinations = [d.address for d in rule.destinations]
        rule_fingerprints[rule.rule_id] = _build_fingerprint(sources, destinations, rule.ports)
        rule_details[rule.rule_id] = {
            "rule_name": rule.rule_name,
            "sources": sources,
            "destinations": destinations,
            "ports": rule.ports,
        }

    # Build fingerprints for user requests
    request_fingerprints: dict[int, tuple] = {}
    request_details: dict[int, dict] = {}
    for req in user_requests:
        data = req.request_json
        request_fingerprints[req.request_id] = _build_fingerprint(
            data["sources"], data["destinations"], data["ports"]
        )
        request_details[req.request_id] = {
            "name": req.name,
            "sources": data["sources"],
            "destinations": data["destinations"],
            "ports": data["ports"],
        }

    # Build a lookup from fingerprint to request_id for O(R+P) matching
    fp_to_request: dict[tuple, int] = {}
    for req_id, fp in request_fingerprints.items():
        fp_to_request[fp] = req_id

    matched: list[MatchedPair] = []
    unmatched_rules: list[UnmatchedRule] = []
    matched_request_ids: set[int] = set()

    for rule_id, rule_fp in rule_fingerprints.items():
        req_id = fp_to_request.get(rule_fp)
        if req_id is not None:
            details = rule_details[rule_id]
            matched.append(MatchedPair(
                rule_id=rule_id,
                request_id=req_id,
                sources=details["sources"],
                destinations=details["destinations"],
                ports=details["ports"],
            ))
            matched_request_ids.add(req_id)
        else:
            details = rule_details[rule_id]
            deficiency = Deficiency(
                type="no_matching_request",
                rule_id=rule_id,
                details={
                    "sources": details["sources"],
                    "destinations": details["destinations"],
                    "ports": details["ports"],
                },
            )
            db.add(deficiency)
            db.flush()
            unmatched_rules.append(UnmatchedRule(
                deficiency_id=deficiency.deficiency_id,
                rule_id=rule_id,
                rule_name=details["rule_name"],
                sources=details["sources"],
                destinations=details["destinations"],
                ports=details["ports"],
            ))

    unmatched_requests: list[UnmatchedRequest] = []
    for req_id in request_fingerprints:
        if req_id not in matched_request_ids:
            details = request_details[req_id]
            deficiency = Deficiency(
                type="no_matching_rule",
                request_id=req_id,
                details={
                    "sources": details["sources"],
                    "destinations": details["destinations"],
                    "ports": details["ports"],
                },
            )
            db.add(deficiency)
            db.flush()
            unmatched_requests.append(UnmatchedRequest(
                deficiency_id=deficiency.deficiency_id,
                request_id=req_id,
                name=details["name"],
                sources=details["sources"],
                destinations=details["destinations"],
                ports=details["ports"],
            ))

    db.commit()

    return ReviewResult(
        matched=matched,
        unmatched_physical_rules=unmatched_rules,
        unmatched_requests=unmatched_requests,
        summary=ReviewSummary(
            total_physical_rules=len(physical_rules),
            total_requests=len(user_requests),
            matched_count=len(matched),
            unmatched_rules_count=len(unmatched_rules),
            unmatched_requests_count=len(unmatched_requests),
        ),
    )
