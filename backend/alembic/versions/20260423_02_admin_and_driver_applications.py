"""admin role and driver applications

Revision ID: 20260423_02
Revises: 20260415_01
Create Date: 2026-04-23
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260423_02"
down_revision: Union[str, None] = "20260415_01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


driver_application_status_enum = postgresql.ENUM(
    "PENDING", "APPROVED", "REJECTED", name="driverapplicationstatus", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = 'userrole' AND e.enumlabel = 'DISPATCHER'
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = 'userrole' AND e.enumlabel = 'ADMIN'
                ) THEN
                    ALTER TYPE userrole RENAME VALUE 'DISPATCHER' TO 'ADMIN';
                END IF;
            END$$;
            """
        )

    op.add_column("users", sa.Column("first_name", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("users", sa.Column("last_name", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=False, server_default=""))

    driver_application_status_enum.create(bind, checkfirst=True)

    op.create_table(
        "driver_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("first_name", sa.String(length=80), nullable=False),
        sa.Column("last_name", sa.String(length=80), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("license_series", sa.String(length=20), nullable=False),
        sa.Column("license_number", sa.String(length=30), nullable=False),
        sa.Column("status", driver_application_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("license_number"),
    )
    op.create_index("ix_driver_applications_email", "driver_applications", ["email"], unique=True)


def downgrade() -> None:
    bind = op.get_bind()

    op.drop_index("ix_driver_applications_email", table_name="driver_applications")
    op.drop_table("driver_applications")

    op.drop_column("users", "phone")
    op.drop_column("users", "last_name")
    op.drop_column("users", "first_name")

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = 'userrole' AND e.enumlabel = 'ADMIN'
                )
                AND NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    JOIN pg_enum e ON e.enumtypid = t.oid
                    WHERE t.typname = 'userrole' AND e.enumlabel = 'DISPATCHER'
                ) THEN
                    ALTER TYPE userrole RENAME VALUE 'ADMIN' TO 'DISPATCHER';
                END IF;
            END$$;
            """
        )

    driver_application_status_enum.drop(bind, checkfirst=True)
