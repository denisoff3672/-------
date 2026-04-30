"""add i18n fields for textual content

Revision ID: 20260430_06
Revises: 20260427_05
Create Date: 2026-04-30
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260430_06"
down_revision: Union[str, None] = "20260427_05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("reviews", sa.Column("comment_i18n", sa.JSON(), nullable=True))
    op.add_column("driver_class_applications", sa.Column("review_note_i18n", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("driver_class_applications", "review_note_i18n")
    op.drop_column("reviews", "comment_i18n")
