"""add db procedures and triggers

Revision ID: 20260430_07
Revises: 20260430_06
Create Date: 2026-04-30
"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260430_07"
down_revision: Union[str, None] = "20260430_06"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tariff_history (
            id BIGSERIAL PRIMARY KEY,
            tariff_id INTEGER NOT NULL REFERENCES tariffs(id) ON DELETE CASCADE,
            comfort_class carcomfortclass NOT NULL,
            base_fare NUMERIC(10, 2) NOT NULL,
            price_per_km NUMERIC(10, 2) NOT NULL,
            price_per_minute NUMERIC(10, 2) NOT NULL,
            night_multiplier DOUBLE PRECISION NOT NULL,
            is_active BOOLEAN NOT NULL,
            changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_create_order(
            p_client_id INTEGER,
            p_pickup_address VARCHAR,
            p_dropoff_address VARCHAR,
            p_pickup_lat DOUBLE PRECISION,
            p_pickup_lng DOUBLE PRECISION,
            p_dropoff_lat DOUBLE PRECISION,
            p_dropoff_lng DOUBLE PRECISION,
            p_distance_km DOUBLE PRECISION,
            p_estimated_minutes INTEGER,
            p_requested_comfort_class carcomfortclass
        )
        RETURNS INTEGER AS $$
        DECLARE
            v_order_id INTEGER;
            v_driver_id INTEGER;
            v_car_id INTEGER;
            v_base_fare NUMERIC(10, 2);
            v_price_per_km NUMERIC(10, 2);
            v_price_per_minute NUMERIC(10, 2);
            v_night_multiplier DOUBLE PRECISION;
            v_estimated_cost NUMERIC(10, 2);
            v_hour INTEGER;
            v_ratio DOUBLE PRECISION;
        BEGIN
            IF EXISTS (
                SELECT 1
                FROM orders o
                WHERE o.client_id = p_client_id
                  AND lower(o.status::text) IN ('pending', 'assigned', 'driver_arrived', 'in_progress')
            ) THEN
                RAISE EXCEPTION 'Client % already has an active order', p_client_id;
            END IF;

            SELECT d.id, d.car_id
            INTO v_driver_id, v_car_id
            FROM drivers d
            LEFT JOIN cars c ON c.id = d.car_id
            WHERE lower(d.status::text) = 'free'
              AND upper(d.approved_car_class::text) = upper(p_requested_comfort_class::text)
              AND (d.car_id IS NULL OR c.is_active IS TRUE)
            ORDER BY d.rating DESC, d.id
            LIMIT 1
            FOR UPDATE SKIP LOCKED;

            IF v_driver_id IS NULL THEN
                RAISE EXCEPTION 'No free driver found for class %', p_requested_comfort_class;
            END IF;

            SELECT t.base_fare, t.price_per_km, t.price_per_minute, t.night_multiplier
            INTO v_base_fare, v_price_per_km, v_price_per_minute, v_night_multiplier
            FROM tariffs t
            WHERE upper(t.comfort_class::text) = upper(p_requested_comfort_class::text)
              AND t.is_active = TRUE
            ORDER BY t.id DESC
            LIMIT 1;

            IF v_base_fare IS NULL THEN
                RAISE EXCEPTION 'Active tariff for class % not found', p_requested_comfort_class;
            END IF;

            v_hour := EXTRACT(HOUR FROM now());
            v_estimated_cost := v_base_fare + (p_distance_km * v_price_per_km) + (p_estimated_minutes * v_price_per_minute);
            IF v_hour >= 23 OR v_hour < 6 THEN
                v_estimated_cost := v_estimated_cost * v_night_multiplier;
            END IF;
            v_estimated_cost := ROUND(v_estimated_cost, 2);

            SELECT CASE WHEN d.uses_own_car THEN 0.75 ELSE 0.50 END
            INTO v_ratio
            FROM drivers d
            WHERE d.id = v_driver_id;

            INSERT INTO orders (
                client_id,
                driver_id,
                car_id,
                requested_comfort_class,
                pickup_address,
                dropoff_address,
                pickup_lat,
                pickup_lng,
                dropoff_lat,
                dropoff_lng,
                distance_km,
                estimated_minutes,
                estimated_cost,
                driver_payout_ratio,
                driver_payout,
                status
            )
            VALUES (
                p_client_id,
                v_driver_id,
                v_car_id,
                p_requested_comfort_class,
                p_pickup_address,
                p_dropoff_address,
                p_pickup_lat,
                p_pickup_lng,
                p_dropoff_lat,
                p_dropoff_lng,
                p_distance_km,
                p_estimated_minutes,
                v_estimated_cost,
                v_ratio,
                ROUND((v_estimated_cost * v_ratio)::numeric, 2),
                'ASSIGNED'::orderstatus
            )
            RETURNING id INTO v_order_id;

            RETURN v_order_id;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_assign_driver_to_order(
            p_order_id INTEGER,
            p_driver_id INTEGER
        )
        RETURNS VOID AS $$
        DECLARE
            v_order_class carcomfortclass;
            v_driver_class carcomfortclass;
            v_driver_status driverstatus;
            v_driver_car_id INTEGER;
            v_ratio DOUBLE PRECISION;
        BEGIN
            SELECT o.requested_comfort_class
            INTO v_order_class
            FROM orders o
            WHERE o.id = p_order_id
            FOR UPDATE;

            IF v_order_class IS NULL THEN
                RAISE EXCEPTION 'Order % not found', p_order_id;
            END IF;

            SELECT d.approved_car_class, d.status, d.car_id
            INTO v_driver_class, v_driver_status, v_driver_car_id
            FROM drivers d
            WHERE d.id = p_driver_id
            FOR UPDATE;

            IF v_driver_class IS NULL THEN
                RAISE EXCEPTION 'Driver % not found', p_driver_id;
            END IF;

            IF lower(v_driver_status::text) <> 'free' THEN
                RAISE EXCEPTION 'Driver % is not free', p_driver_id;
            END IF;

            IF upper(v_driver_class::text) <> upper(v_order_class::text) THEN
                RAISE EXCEPTION 'Driver class % does not match order class %', v_driver_class, v_order_class;
            END IF;

            SELECT CASE WHEN d.uses_own_car THEN 0.75 ELSE 0.50 END
            INTO v_ratio
            FROM drivers d
            WHERE d.id = p_driver_id;

            UPDATE orders
            SET driver_id = p_driver_id,
                car_id = v_driver_car_id,
                status = 'ASSIGNED'::orderstatus,
                driver_payout_ratio = COALESCE(driver_payout_ratio, v_ratio),
                driver_payout = ROUND((estimated_cost * COALESCE(driver_payout_ratio, v_ratio))::numeric, 2),
                updated_at = now()
            WHERE id = p_order_id;

            UPDATE drivers
            SET status = 'ON_ORDER'::driverstatus
            WHERE id = p_driver_id;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION sp_complete_order(
            p_order_id INTEGER,
            p_final_cost NUMERIC(10, 2) DEFAULT NULL
        )
        RETURNS VOID AS $$
        DECLARE
            v_client_id INTEGER;
            v_driver_id INTEGER;
            v_final_cost NUMERIC(10, 2);
            v_ratio DOUBLE PRECISION;
            v_driver_payout NUMERIC(10, 2);
        BEGIN
            SELECT o.client_id,
                   o.driver_id,
                   COALESCE(p_final_cost, o.estimated_cost),
                   COALESCE(o.driver_payout_ratio, 0.50)
            INTO v_client_id, v_driver_id, v_final_cost, v_ratio
            FROM orders o
            WHERE o.id = p_order_id
            FOR UPDATE;

            IF v_client_id IS NULL THEN
                RAISE EXCEPTION 'Order % not found', p_order_id;
            END IF;

            v_driver_payout := ROUND((v_final_cost * v_ratio)::numeric, 2);

            UPDATE orders
            SET status = 'COMPLETED'::orderstatus,
                final_cost = v_final_cost,
                driver_payout = v_driver_payout,
                updated_at = now()
            WHERE id = p_order_id;

            UPDATE clients
            SET balance = COALESCE(balance, 0) - v_final_cost
            WHERE id = v_client_id;

            UPDATE drivers
            SET status = 'FREE'::driverstatus
            WHERE id = v_driver_id;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_set_order_sequence_fn()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.client_order_number IS NULL OR NEW.client_order_number <= 0 THEN
                SELECT COALESCE(MAX(o.client_order_number), 0) + 1
                INTO NEW.client_order_number
                FROM orders o
                WHERE o.client_id = NEW.client_id;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_driver_status_on_order_fn()
        RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.driver_id IS NULL THEN
                RETURN NEW;
            END IF;

            IF lower(NEW.status::text) = 'assigned' THEN
                UPDATE drivers SET status = 'ON_ORDER'::driverstatus WHERE id = NEW.driver_id;
            ELSIF lower(NEW.status::text) IN ('completed', 'cancelled') THEN
                UPDATE drivers SET status = 'FREE'::driverstatus WHERE id = NEW.driver_id;
            END IF;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION trg_tariff_history_fn()
        RETURNS TRIGGER AS $$
        BEGIN
            INSERT INTO tariff_history (
                tariff_id,
                comfort_class,
                base_fare,
                price_per_km,
                price_per_minute,
                night_multiplier,
                is_active,
                changed_at
            )
            VALUES (
                OLD.id,
                OLD.comfort_class,
                OLD.base_fare,
                OLD.price_per_km,
                OLD.price_per_minute,
                OLD.night_multiplier,
                OLD.is_active,
                now()
            );

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_set_order_sequence ON orders;")
    op.execute("DROP TRIGGER IF EXISTS trg_driver_status_on_order ON orders;")
    op.execute("DROP TRIGGER IF EXISTS trg_tariff_history ON tariffs;")

    op.execute(
        """
        CREATE TRIGGER trg_set_order_sequence
        BEFORE INSERT ON orders
        FOR EACH ROW
        EXECUTE FUNCTION trg_set_order_sequence_fn();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_driver_status_on_order
        AFTER UPDATE OF status ON orders
        FOR EACH ROW
        EXECUTE FUNCTION trg_driver_status_on_order_fn();
        """
    )

    op.execute(
        """
        CREATE TRIGGER trg_tariff_history
        BEFORE UPDATE OF base_fare, price_per_km, price_per_minute, night_multiplier, is_active ON tariffs
        FOR EACH ROW
        EXECUTE FUNCTION trg_tariff_history_fn();
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    op.execute("DROP TRIGGER IF EXISTS trg_tariff_history ON tariffs;")
    op.execute("DROP TRIGGER IF EXISTS trg_driver_status_on_order ON orders;")
    op.execute("DROP TRIGGER IF EXISTS trg_set_order_sequence ON orders;")

    op.execute("DROP FUNCTION IF EXISTS trg_tariff_history_fn();")
    op.execute("DROP FUNCTION IF EXISTS trg_driver_status_on_order_fn();")
    op.execute("DROP FUNCTION IF EXISTS trg_set_order_sequence_fn();")

    op.execute("DROP FUNCTION IF EXISTS sp_complete_order(INTEGER, NUMERIC);")
    op.execute("DROP FUNCTION IF EXISTS sp_assign_driver_to_order(INTEGER, INTEGER);")
    op.execute("DROP FUNCTION IF EXISTS sp_create_order(INTEGER, VARCHAR, VARCHAR, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, DOUBLE PRECISION, INTEGER, carcomfortclass);")

    op.execute("DROP TABLE IF EXISTS tariff_history;")
