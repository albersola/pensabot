"""add HNSW index for memory embedding

Revision ID: 9e1c2a4b7d8f
Revises: 6cf8a1f635d3
Create Date: 2026-03-10 12:30:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e1c2a4b7d8f"
down_revision: Union[str, Sequence[str], None] = "6cf8a1f635d3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_memory_embedding_hnsw_cosine
        ON memory
        USING hnsw (embedding vector_cosine_ops)
        WHERE embedding IS NOT NULL
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_memory_embedding_hnsw_cosine")
