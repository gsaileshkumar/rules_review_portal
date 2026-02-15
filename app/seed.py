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
        # Requests with subnets/ranges that will mismatch physical rule formats
        Request(
            name="Monitoring subnet access",
            status="completed",
            request_json={
                "sources": ["10.0.10.0/24"],
                "destinations": ["10.0.20.0/24"],
                "ports": ["161", "162"],
            },
        ),
        Request(
            name="Backup IP range access",
            status="completed",
            request_json={
                "sources": ["10.0.30.1-10.0.30.50"],
                "destinations": ["10.0.40.100"],
                "ports": ["873"],
            },
        ),
        Request(
            name="Dev environment access",
            status="completed",
            request_json={
                "sources": ["172.16.0.0/16"],
                "destinations": ["192.168.1.0/24"],
                "ports": ["22", "3306"],
            },
        ),
        Request(
            name="Load balancer health check",
            status="completed",
            request_json={
                "sources": ["10.0.50.10"],
                "destinations": ["10.0.60.0/24"],
                "ports": ["80", "443"],
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

    # Rule 4: Monitoring - implemented as IP range (request uses /24 subnet)
    rule4 = PhysicalRule(
        rule_name="Monitoring traffic",
        firewall_device="FW-CORE-01",
        ports=["161", "162"],
        action="allow",
    )
    rule4.sources.append(PhysicalRuleSource(address="10.0.10.0-10.0.10.255"))
    rule4.destinations.append(PhysicalRuleDestination(address="10.0.20.0-10.0.20.255"))

    # Rule 5: Backup - implemented as /24 subnet (request uses IP range)
    rule5 = PhysicalRule(
        rule_name="Backup traffic",
        firewall_device="FW-CORE-02",
        ports=["873"],
        action="allow",
    )
    rule5.sources.append(PhysicalRuleSource(address="10.0.30.0/24"))
    rule5.destinations.append(PhysicalRuleDestination(address="10.0.40.100"))

    # Rule 6: Dev environment - exact same subnet format as request (will match)
    rule6 = PhysicalRule(
        rule_name="Dev environment",
        firewall_device="FW-CORE-02",
        ports=["22", "3306"],
        action="allow",
    )
    rule6.sources.append(PhysicalRuleSource(address="172.16.0.0/16"))
    rule6.destinations.append(PhysicalRuleDestination(address="192.168.1.0/24"))

    # Rule 7: LB health check - dest as IP range (request uses /24 subnet)
    rule7 = PhysicalRule(
        rule_name="LB health check",
        firewall_device="FW-CORE-01",
        ports=["80", "443"],
        action="allow",
    )
    rule7.sources.append(PhysicalRuleSource(address="10.0.50.10"))
    rule7.destinations.append(PhysicalRuleDestination(address="10.0.60.0-10.0.60.255"))

    db.add_all([rule1, rule2, rule3, rule4, rule5, rule6, rule7])
    db.commit()

    return {
        "message": "Seed data created successfully",
        "requests_created": 7,
        "physical_rules_created": 7,
    }
