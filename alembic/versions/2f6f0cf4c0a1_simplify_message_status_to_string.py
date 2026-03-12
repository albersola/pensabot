"""simplify message status to string

Revision ID: 2f6f0cf4c0a1
Revises: c54af5f77e4f
Create Date: 2026-03-08 12:15:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "2f6f0cf4c0a1"
down_revision: Union[str, Sequence[str], None] = "c54af5f77e4f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "message",
        "status",
        existing_type=sa.Enum(
            "pending",
            "processing",
            "done",
            "error",
            "transcribing",
            "preprocessing",
            name="messagestatus",
        ),
        type_=sa.String(),
        existing_nullable=False,
        postgresql_using="status::text",
    )
    op.execute("UPDATE message SET status = 'pending' WHERE status = 'processing'")
    op.execute("UPDATE message SET status = 'preprocessing' WHERE status = 'transcribing'")
    op.execute("DROP TYPE IF EXISTS messagestatus")


def downgrade() -> None:
    op.execute(
        "CREATE TYPE messagestatus AS ENUM "
        "('pending', 'processing', 'done', 'error', 'transcribing', 'preprocessing')"
    )
    op.alter_column(
        "message",
        "status",
        existing_type=sa.String(),
        type_=sa.Enum(
            "pending",
            "processing",
            "done",
            "error",
            "transcribing",
            "preprocessing",
            name="messagestatus",
        ),
        existing_nullable=False,
        postgresql_using="status::messagestatus",
    )
