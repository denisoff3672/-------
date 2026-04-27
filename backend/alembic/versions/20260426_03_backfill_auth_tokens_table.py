"""backfill auth_tokens table for legacy databases

Revision ID: 20260426_03
Revises: 20260423_02
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260426_03"
down_revision: Union[str, None] = "20260423_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


token_type_enum = postgresql.ENUM("ACCESS", "REFRESH", name="tokentype", create_type=False)


def _table_exists(bind, table_name: str) -> bool:
    inspector = sa.inspect(bind)
    return table_name in inspector.get_table_names()


def _index_exists(bind, table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(bind)
    return any(index.get("name") == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        token_type_enum.create(bind, checkfirst=True)

    if not _table_exists(bind, "auth_tokens"):
        op.create_table(
            "auth_tokens",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
            sa.Column("jti", sa.String(length=64), nullable=False),
            sa.Column("token_type", token_type_enum if bind.dialect.name == "postgresql" else sa.String(length=20), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("is_revoked", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.UniqueConstraint("jti"),
        )

    if not _index_exists(bind, "auth_tokens", "ix_auth_tokens_jti"):
        op.create_index("ix_auth_tokens_jti", "auth_tokens", ["jti"], unique=True)

    if not _index_exists(bind, "auth_tokens", "ix_auth_tokens_user_id"):
        op.create_index("ix_auth_tokens_user_id", "auth_tokens", ["user_id"], unique=False)


def downgrade() -> None:
    bind = op.get_bind()

    if _table_exists(bind, "auth_tokens"):
        op.drop_index("ix_auth_tokens_user_id", table_name="auth_tokens")
        op.drop_index("ix_auth_tokens_jti", table_name="auth_tokens")
        op.drop_table("auth_tokens")

    if bind.dialect.name == "postgresql":
        token_type_enum.drop(bind, checkfirst=True)
