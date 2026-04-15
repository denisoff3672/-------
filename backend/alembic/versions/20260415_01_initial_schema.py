"""initial schema

Revision ID: 20260415_01
Revises:
Create Date: 2026-04-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_01"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


user_role_enum = sa.Enum("CLIENT", "DRIVER", "DISPATCHER", "ADMIN", name="userrole")
driver_status_enum = sa.Enum("FREE", "ON_ORDER", "BREAK", "INACTIVE", name="driverstatus")
order_status_enum = sa.Enum("PENDING", "IN_PROGRESS", "COMPLETED", "CANCELLED", name="orderstatus")
comfort_class_enum = sa.Enum("ECONOMY", "STANDARD", "BUSINESS", name="carcomfortclass")


def upgrade() -> None:
    bind = op.get_bind()
    user_role_enum.create(bind, checkfirst=True)
    driver_status_enum.create(bind, checkfirst=True)
    order_status_enum.create(bind, checkfirst=True)
    comfort_class_enum.create(bind, checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_username", "users", ["username"], unique=True)

    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("balance", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.UniqueConstraint("user_id"),
    )

    op.create_table(
        "cars",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("plate_number", sa.String(length=15), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("color", sa.String(length=30), nullable=False),
        sa.Column("comfort_class", comfort_class_enum, nullable=False),
        sa.Column("technical_status", sa.String(length=100), nullable=False, server_default="good"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_cars_plate_number", "cars", ["plate_number"], unique=True)

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("license_number", sa.String(length=30), nullable=False),
        sa.Column("rating", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("status", driver_status_enum, nullable=False, server_default="FREE"),
        sa.Column("car_id", sa.Integer(), sa.ForeignKey("cars.id"), nullable=True),
        sa.UniqueConstraint("user_id"),
        sa.UniqueConstraint("license_number"),
    )

    op.create_table(
        "tariffs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comfort_class", comfort_class_enum, nullable=False),
        sa.Column("base_fare", sa.Numeric(10, 2), nullable=False, server_default="40"),
        sa.Column("price_per_km", sa.Numeric(10, 2), nullable=False, server_default="15"),
        sa.Column("price_per_minute", sa.Numeric(10, 2), nullable=False, server_default="2"),
        sa.Column("night_multiplier", sa.Float(), nullable=False, server_default="1.0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("comfort_class", name="uq_tariff_comfort_class"),
    )

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("car_id", sa.Integer(), sa.ForeignKey("cars.id"), nullable=True),
        sa.Column("pickup_address", sa.String(length=255), nullable=False),
        sa.Column("dropoff_address", sa.String(length=255), nullable=False),
        sa.Column("pickup_lat", sa.Float(), nullable=False),
        sa.Column("pickup_lng", sa.Float(), nullable=False),
        sa.Column("dropoff_lat", sa.Float(), nullable=False),
        sa.Column("dropoff_lng", sa.Float(), nullable=False),
        sa.Column("distance_km", sa.Float(), nullable=False),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("estimated_cost", sa.Numeric(10, 2), nullable=False),
        sa.Column("final_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("status", order_status_enum, nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reviews",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("client_id", sa.Integer(), sa.ForeignKey("clients.id"), nullable=False),
        sa.Column("driver_id", sa.Integer(), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("order_id"),
    )


def downgrade() -> None:
    op.drop_table("reviews")
    op.drop_table("orders")
    op.drop_table("tariffs")
    op.drop_table("drivers")
    op.drop_index("ix_cars_plate_number", table_name="cars")
    op.drop_table("cars")
    op.drop_table("clients")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    comfort_class_enum.drop(bind, checkfirst=True)
    order_status_enum.drop(bind, checkfirst=True)
    driver_status_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
