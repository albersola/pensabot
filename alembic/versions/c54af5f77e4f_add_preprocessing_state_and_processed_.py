"""add preprocessing state and processed content

Revision ID: c54af5f77e4f
Revises: a371b9b43f3e
Create Date: 2026-03-08 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = "c54af5f77e4f"
down_revision: Union[str, Sequence[str], None] = "a371b9b43f3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    context = op.get_context()
    with context.autocommit_block():
        op.execute("ALTER TYPE messagestatus ADD VALUE IF NOT EXISTS 'preprocessing'")
    op.add_column("message", sa.Column("processed_content", sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.execute(
        """
        UPDATE message
        SET status = 'preprocessing'::messagestatus
        WHERE status::text = 'transcribing'
        """
    )
    op.execute(
        """
        UPDATE message
        SET processed_content = content
        WHERE message_type IN ('image', 'voice')
          AND content IS NOT NULL
          AND content <> ''
          AND processed_content IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("message", "processed_content")
