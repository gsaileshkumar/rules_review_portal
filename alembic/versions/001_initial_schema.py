"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "requests",
        sa.Column("request_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("request_json", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("request_id"),
    )

    op.create_table(
        "physical_rules",
        sa.Column("rule_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_name", sa.String(255), nullable=False),
        sa.Column("firewall_device", sa.String(255), nullable=False),
        sa.Column("ports", ARRAY(sa.String()), nullable=False),
        sa.Column("action", sa.String(20), nullable=False, server_default="allow"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("rule_id"),
    )

    op.create_table(
        "physical_rule_sources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["rule_id"], ["physical_rules.rule_id"]),
    )

    op.create_table(
        "physical_rule_destinations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("rule_id", sa.Integer(), nullable=False),
        sa.Column("address", sa.String(255), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["rule_id"], ["physical_rules.rule_id"]),
    )


def downgrade() -> None:
    op.drop_table("physical_rule_destinations")
    op.drop_table("physical_rule_sources")
    op.drop_table("physical_rules")
    op.drop_table("requests")
