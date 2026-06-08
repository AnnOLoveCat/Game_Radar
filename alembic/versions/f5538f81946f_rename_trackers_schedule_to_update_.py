"""rename trackers schedule to update_frequency

Revision ID: f5538f81946f
Revises: f14c4d68792e
Create Date: 2026-05-30 17:26:55.564753
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f5538f81946f"
down_revision: Union[str, Sequence[str], None] = "f14c4d68792e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("trackers") as batch_op:
        batch_op.add_column(sa.Column("update_frequency", sa.String(length=20), nullable=True))

    op.execute("UPDATE trackers SET update_frequency = schedule")

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.alter_column("update_frequency", nullable=False)
        batch_op.drop_column("schedule")


def downgrade() -> None:
    with op.batch_alter_table("trackers") as batch_op:
        batch_op.add_column(sa.Column("schedule", sa.String(length=20), nullable=True))

    op.execute("UPDATE trackers SET schedule = update_frequency")

    with op.batch_alter_table("trackers") as batch_op:
        batch_op.alter_column("schedule", nullable=False)
        batch_op.drop_column("update_frequency")