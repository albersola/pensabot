"""add BM25 index and drop keywords column

Revision ID: f3a1b8c2d4e5
Revises: 9e1c2a4b7d8f
Create Date: 2026-03-11 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
from sqlalchemy import Column
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers, used by Alembic.
revision: str = "f3a1b8c2d4e5"
down_revision: Union[str, Sequence[str], None] = "9e1c2a4b7d8f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE INDEX idx_memory_bm25 ON memory
        USING bm25 (id, content)
        WITH (key_field = 'id', text_fields = '{"content": {"tokenizer": {"type": "icu"}}}')
        """
    )
    op.drop_column("memory", "keywords")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_memory_bm25")
    op.add_column(
        "memory",
        Column("keywords", JSONB(), server_default="[]", nullable=False),
    )
