"""add unique constraint to game_matches

Revision ID: acb80a98d725
Revises: c735f4eb845d
Create Date: 2026-04-03 10:47:33.978537

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'acb80a98d725'
down_revision: Union[str, Sequence[str], None] = 'c735f4eb845d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    with op.batch_alter_table("game_matches") as batch_op:
        batch_op.create_unique_constraint(
            "uq_tracker_game_match",
            ["tracker_id", "game_id"]
        )

def downgrade() -> None:
    """Downgrade schema."""
    with op.batch_alter_table("game_matches") as batch_op:
        batch_op.drop_constraint(
            "uq_tracker_game_match",
            type_="unique"
        )
