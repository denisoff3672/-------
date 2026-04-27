"""driver class applications and per-client order sequence

Revision ID: 20260427_05
Revises: 20260426_04
Create Date: 2026-04-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260427_05"
down_revision: Union[str, None] = "20260426_04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    bind = op.get_bind()

    op.add_column("orders", sa.Column("client_order_number", sa.Integer(), nullable=True))

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            WITH ranked AS (
                SELECT id, ROW_NUMBER() OVER (PARTITION BY client_id ORDER BY created_at, id) AS rn
                FROM orders
            )
            UPDATE orders o
            SET client_order_number = ranked.rn
            FROM ranked
            WHERE ranked.id = o.id
            """
        )
    else:
        rows = bind.execute(sa.text("SELECT id, client_id FROM orders ORDER BY client_id, created_at, id")).fetchall()
        counters: dict[int, int] = {}
        for row in rows:
            client_id = int(row.client_id)
            counters[client_id] = counters.get(client_id, 0) + 1
            bind.execute(
                sa.text("UPDATE orders SET client_order_number = :seq WHERE id = :id"),
                {"seq": counters[client_id], "id": int(row.id)},
            )

    op.alter_column("orders", "client_order_number", nullable=False, server_default="1")
    op.create_unique_constraint("uq_order_client_sequence", "orders", ["client_id", "client_order_number"])

    if bind.dialect.name == "postgresql":
        op.execute(
            """
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_type t
                    WHERE t.typname = 'driverclassapplicationstatus'
                ) THEN
                    CREATE TYPE driverclassapplicationstatus AS ENUM ('PENDING', 'APPROVED', 'REJECTED');
                END IF;
            END$$;
            """
        )
        op.execute(
            """
            CREATE TABLE driver_class_applications (
                id SERIAL PRIMARY KEY,
                driver_id INTEGER NOT NULL REFERENCES drivers(id),
                requested_car_class carcomfortclass NOT NULL,
                own_car_make VARCHAR(60) NOT NULL,
                own_car_model VARCHAR(80) NOT NULL,
                own_car_year INTEGER NOT NULL,
                own_car_plate VARCHAR(20) NOT NULL,
                own_car_engine VARCHAR(80) NOT NULL,
                own_car_transmission VARCHAR(40) NOT NULL,
                status driverclassapplicationstatus NOT NULL DEFAULT 'PENDING',
                reviewed_by INTEGER NULL REFERENCES users(id),
                review_note TEXT NULL,
                reviewed_at TIMESTAMPTZ NULL,
                created_at TIMESTAMPTZ DEFAULT now()
            )
            """
        )
    else:
        op.create_table(
            "driver_class_applications",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
            sa.Column("requested_car_class", sa.String(length=32), nullable=False),
            sa.Column("own_car_make", sa.String(length=60), nullable=False),
            sa.Column("own_car_model", sa.String(length=80), nullable=False),
            sa.Column("own_car_year", sa.Integer(), nullable=False),
            sa.Column("own_car_plate", sa.String(length=20), nullable=False),
            sa.Column("own_car_engine", sa.String(length=80), nullable=False),
            sa.Column("own_car_transmission", sa.String(length=40), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
            sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("review_note", sa.Text(), nullable=True),
            sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        )
    op.create_index(
        "ix_driver_class_applications_driver_id",
        "driver_class_applications",
        ["driver_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_driver_class_applications_driver_id", table_name="driver_class_applications")
    op.drop_table("driver_class_applications")

    op.drop_constraint("uq_order_client_sequence", "orders", type_="unique")
    op.drop_column("orders", "client_order_number")
