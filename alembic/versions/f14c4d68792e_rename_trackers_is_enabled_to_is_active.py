"""rename trackers is_enabled to is_active

Revision ID: f14c4d68792e
Revises: fe7696ae8e8c
Create Date: 2026-05-30 15:28:31.355676
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f14c4d68792e"
down_revision: Union[str, Sequence[str], None] = "fe7696ae8e8c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 已由前一支 migration fe7696ae8e8c 完成 is_enabled -> is_active
    # 這支保留 revision 鏈，但不再執行任何資料表變更
    pass


def downgrade() -> None:
    """Downgrade schema."""
    # 對應 upgrade 為 no-op，這裡也保持 no-op
    pass