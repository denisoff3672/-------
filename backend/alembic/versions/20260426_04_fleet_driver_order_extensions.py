"""fleet driver order extensions

Revision ID: 20260426_04
Revises: 20260426_03
Create Date: 2026-04-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_04"
down_revision: Union[str, None] = "20260426_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _add_enum_value_if_missing(enum_type: str, enum_value: str) -> None:
    op.execute(
        f"""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type t
                JOIN pg_enum e ON e.enumtypid = t.oid
                WHERE t.typname = '{enum_type}' AND e.enumlabel = '{enum_value}'
            ) THEN
                ALTER TYPE {enum_type} ADD VALUE '{enum_value}';
            END IF;
        END$$;
        """
    )


def upgrade() -> None:
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        _add_enum_value_if_missing("carcomfortclass", "COMFORT")
        _add_enum_value_if_missing("orderstatus", "ASSIGNED")
        _add_enum_value_if_missing("orderstatus", "DRIVER_ARRIVED")

    op.add_column("cars", sa.Column("make", sa.String(length=60), nullable=False, server_default=""))
    op.add_column("cars", sa.Column("production_year", sa.Integer(), nullable=False, server_default="2020"))
    op.add_column("cars", sa.Column("engine", sa.String(length=80), nullable=False, server_default=""))
    op.add_column("cars", sa.Column("transmission", sa.String(length=40), nullable=False, server_default="automatic"))

    op.add_column(
        "drivers",
        sa.Column(
            "approved_car_class",
            sa.Enum("ECONOMY", "STANDARD", "COMFORT", "BUSINESS", name="carcomfortclass"),
            nullable=False,
            server_default="ECONOMY",
        ),
    )
    op.add_column(
        "drivers",
        sa.Column(
            "requested_car_class",
            sa.Enum("ECONOMY", "STANDARD", "COMFORT", "BUSINESS", name="carcomfortclass"),
            nullable=True,
        ),
    )
    op.add_column("drivers", sa.Column("uses_own_car", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("drivers", sa.Column("own_car_make", sa.String(length=60), nullable=True))
    op.add_column("drivers", sa.Column("own_car_model", sa.String(length=80), nullable=True))
    op.add_column("drivers", sa.Column("own_car_year", sa.Integer(), nullable=True))
    op.add_column("drivers", sa.Column("own_car_plate", sa.String(length=20), nullable=True))
    op.add_column("drivers", sa.Column("own_car_engine", sa.String(length=80), nullable=True))
    op.add_column("drivers", sa.Column("own_car_transmission", sa.String(length=40), nullable=True))
    op.add_column("drivers", sa.Column("current_lat", sa.Float(), nullable=True))
    op.add_column("drivers", sa.Column("current_lng", sa.Float(), nullable=True))

    op.add_column(
        "orders",
        sa.Column(
            "requested_comfort_class",
            sa.Enum("ECONOMY", "STANDARD", "COMFORT", "BUSINESS", name="carcomfortclass"),
            nullable=False,
            server_default="ECONOMY",
        ),
    )
    op.add_column("orders", sa.Column("driver_payout", sa.Numeric(10, 2), nullable=True))
    op.add_column("orders", sa.Column("driver_payout_ratio", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "driver_payout_ratio")
    op.drop_column("orders", "driver_payout")
    op.drop_column("orders", "requested_comfort_class")

    op.drop_column("drivers", "current_lng")
    op.drop_column("drivers", "current_lat")
    op.drop_column("drivers", "own_car_transmission")
    op.drop_column("drivers", "own_car_engine")
    op.drop_column("drivers", "own_car_plate")
    op.drop_column("drivers", "own_car_year")
    op.drop_column("drivers", "own_car_model")
    op.drop_column("drivers", "own_car_make")
    op.drop_column("drivers", "uses_own_car")
    op.drop_column("drivers", "requested_car_class")
    op.drop_column("drivers", "approved_car_class")

    op.drop_column("cars", "transmission")
    op.drop_column("cars", "engine")
    op.drop_column("cars", "production_year")
    op.drop_column("cars", "make")
