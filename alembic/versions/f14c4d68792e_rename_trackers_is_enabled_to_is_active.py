"""rename trackers is_enabled to is_active

Revision ID: f14c4d68792e
Revises: fe7696ae8e8c
Create Date: 2026-05-30 17:02:02.509351

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f14c4d68792e'
down_revision: Union[str, Sequence[str], None] = 'fe7696ae8e8c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("trackers") as batch_op:
        batch_op.add_column(sa.Column("is_active", sa.Boolean(), nullable=True))

    op.execute("UPDATE trackers SET is_active = is_enabled")

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.alter_column("is_active", nullable=False)
        batch_op.drop_column("is_enabled")


def downgrade() -> None:
    with op.batch_alter_table("trackers") as batch_op:
        batch_op.add_column(sa.Column("is_enabled", sa.Boolean(), nullable=True))

    op.execute("UPDATE trackers SET is_enabled = is_active")

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.alter_column("is_enabled", nullable=False)
        batch_op.drop_column("is_active")
