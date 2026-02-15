from sqlalchemy.orm import Session

from app.models.request import Request
from app.models.physical_rule import PhysicalRule
from app.models.physical_rule_source import PhysicalRuleSource
from app.models.physical_rule_destination import PhysicalRuleDestination
from app.models.deficiency import Deficiency


def seed_data(db: Session) -> dict:
    # Clear existing data
    db.query(Deficiency).delete()
    db.query(PhysicalRuleDestination).delete()
    db.query(PhysicalRuleSource).delete()
    db.query(PhysicalRule).delete()
    db.query(Request).delete()
    db.commit()

    # Seed user requests
    requests_data = [
        Request(
            name="Web server access",
            status="completed",
            request_json={
                "sources": ["10.0.1.10"],
                "destinations": ["10.0.2.20"],
                "ports": ["443"],
            },
        ),
        Request(
            name="API backend access",
            status="completed",
            request_json={
                "sources": ["10.0.1.11", "10.0.1.12"],
                "destinations": ["10.0.3.30"],
                "ports": ["8080", "8443"],
            },
        ),
        Request(
            name="DB access",
            status="completed",
            request_json={
                "sources": ["10.0.1.50"],
                "destinations": ["10.0.4.40"],
                "ports": ["5432"],
            },
        ),
    ]
    db.add_all(requests_data)
    db.flush()

    # Seed physical rules
    rule1 = PhysicalRule(
        rule_name="Allow web traffic",
        firewall_device="FW-CORE-01",
        ports=["443"],
        action="allow",
    )
    rule1.sources.append(PhysicalRuleSource(address="10.0.1.10"))
    rule1.destinations.append(PhysicalRuleDestination(address="10.0.2.20"))

    rule2 = PhysicalRule(
        rule_name="Allow API traffic",
        firewall_device="FW-CORE-01",
        ports=["8080", "8443"],
        action="allow",
    )
    rule2.sources.append(PhysicalRuleSource(address="10.0.1.11"))
    rule2.sources.append(PhysicalRuleSource(address="10.0.1.12"))
    rule2.destinations.append(PhysicalRuleDestination(address="10.0.3.30"))

    rule3 = PhysicalRule(
        rule_name="Unknown SSH rule",
        firewall_device="FW-CORE-02",
        ports=["22"],
        action="allow",
    )
    rule3.sources.append(PhysicalRuleSource(address="10.0.5.99"))
    rule3.destinations.append(PhysicalRuleDestination(address="10.0.6.50"))

    db.add_all([rule1, rule2, rule3])
    db.commit()

    return {
        "message": "Seed data created successfully",
        "requests_created": 3,
        "physical_rules_created": 3,
    }
