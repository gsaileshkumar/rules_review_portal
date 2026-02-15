"""Add pgvector embeddings and semantic_deficiencies

Revision ID: 004
Revises: 003
Create Date: 2026-02-15

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable pgvector extension
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding_text and vector embedding columns to requests table
    op.add_column("requests", sa.Column("embedding_text", sa.Text(), nullable=True))
    op.execute("ALTER TABLE requests ADD COLUMN embedding vector(1024)")

    # Add embedding_text and vector embedding columns to physical_rules table
    op.add_column("physical_rules", sa.Column("embedding_text", sa.Text(), nullable=True))
    op.execute("ALTER TABLE physical_rules ADD COLUMN embedding vector(1024)")

    # Create HNSW indexes for fast cosine similarity search (1024 dims is within the 2000-dim limit)
    op.execute(
        "CREATE INDEX idx_requests_embedding ON requests USING hnsw (embedding vector_cosine_ops)"
    )
    op.execute(
        "CREATE INDEX idx_physical_rules_embedding ON physical_rules USING hnsw (embedding vector_cosine_ops)"
    )

    # Create semantic_deficiencies table
    op.execute("""
        CREATE TABLE semantic_deficiencies (
            id SERIAL PRIMARY KEY,
            type VARCHAR(50) NOT NULL,
            request_id INT REFERENCES requests(request_id) ON DELETE SET NULL,
            rule_id INT REFERENCES physical_rules(rule_id) ON DELETE SET NULL,
            best_match_request_id INT REFERENCES requests(request_id) ON DELETE SET NULL,
            best_match_rule_id INT REFERENCES physical_rules(rule_id) ON DELETE SET NULL,
            similarity_score FLOAT,
            threshold_used FLOAT NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS semantic_deficiencies")
    op.execute("DROP INDEX IF EXISTS idx_requests_embedding")
    op.execute("DROP INDEX IF EXISTS idx_physical_rules_embedding")
    op.execute("ALTER TABLE requests DROP COLUMN IF EXISTS embedding")
    op.drop_column("requests", "embedding_text")
    op.execute("ALTER TABLE physical_rules DROP COLUMN IF EXISTS embedding")
    op.drop_column("physical_rules", "embedding_text")
    op.execute("DROP EXTENSION IF EXISTS vector")
