"""Add physical_rules_view

Revision ID: 003
Revises: 002
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE VIEW physical_rules_view AS
        SELECT
            pr.rule_id,
            pr.rule_name,
            pr.firewall_device,
            pr.ports,
            pr.action,
            pr.created_at,
            array_agg(DISTINCT prs.address ORDER BY prs.address) AS sources,
            array_agg(DISTINCT prd.address ORDER BY prd.address) AS destinations
        FROM physical_rules pr
        LEFT JOIN physical_rule_sources prs ON pr.rule_id = prs.rule_id
        LEFT JOIN physical_rule_destinations prd ON pr.rule_id = prd.rule_id
        GROUP BY pr.rule_id, pr.rule_name, pr.firewall_device, pr.ports, pr.action, pr.created_at
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS physical_rules_view")
