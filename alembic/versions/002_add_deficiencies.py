"""Add deficiencies table

Revision ID: 002
Revises: 001
Create Date: 2026-02-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "deficiencies",
        sa.Column("deficiency_id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("request_id", sa.Integer(), nullable=True),
        sa.Column("rule_id", sa.Integer(), nullable=True),
        sa.Column("details", JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("deficiency_id"),
        sa.ForeignKeyConstraint(["request_id"], ["requests.request_id"]),
        sa.ForeignKeyConstraint(["rule_id"], ["physical_rules.rule_id"]),
    )


def downgrade() -> None:
    op.drop_table("deficiencies")
