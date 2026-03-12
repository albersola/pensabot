"""switch memory embeddings to 512 dims

Revision ID: 6cf8a1f635d3
Revises: 2f6f0cf4c0a1
Create Date: 2026-03-10 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6cf8a1f635d3"
down_revision: Union[str, Sequence[str], None] = "2f6f0cf4c0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Existing embeddings were generated with a different model/size and are no longer valid.
    op.execute("UPDATE memory SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute("ALTER TABLE memory ALTER COLUMN embedding TYPE vector(512)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("UPDATE memory SET embedding = NULL WHERE embedding IS NOT NULL")
    op.execute("ALTER TABLE memory ALTER COLUMN embedding TYPE vector(1536)")
