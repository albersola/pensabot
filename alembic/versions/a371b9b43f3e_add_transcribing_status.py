"""add_transcribing_status

Revision ID: a371b9b43f3e
Revises: b2fb8093154a
Create Date: 2026-03-05 19:41:02.591947

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision: str = 'a371b9b43f3e'
down_revision: Union[str, Sequence[str], None] = 'b2fb8093154a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE messagestatus ADD VALUE 'transcribing'")


def downgrade() -> None:
    pass  # Postgres does not support removing enum values
