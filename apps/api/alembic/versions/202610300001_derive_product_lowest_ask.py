"""derive product lowest ask from qualifying listings

Revision ID: 202610300001
Revises: 202610290001
Create Date: 2026-10-30 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "202610300001"
down_revision: Union[str, None] = "202610290001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


REFRESH_FUNCTION = "stockx_refresh_product_lowest_ask"
LOCK_FUNCTION = "stockx_lock_lowest_ask_products"
LOCK_TRIGGER_FUNCTION = "stockx_listing_lowest_ask_lock_trigger"
TRIGGER_FUNCTION = "stockx_listing_lowest_ask_trigger"
LOCK_INSERT_DELETE_TRIGGER = "trg_listings_lowest_ask_lock_insert_delete"
LOCK_UPDATE_TRIGGER = "trg_listings_lowest_ask_lock_update"
INSERT_DELETE_TRIGGER = "trg_listings_lowest_ask_insert_delete"
UPDATE_TRIGGER = "trg_listings_lowest_ask_update"


def upgrade() -> None:
    op.create_index(
        "ix_listings_qualifying_product_price",
        "listings",
        ["product_id", "price_cents", "id"],
        unique=False,
        postgresql_where=sa.text("status = 'active' AND available_quantity > 0 AND currency = 'USD'"),
    )
    op.create_index(
        "ix_product_variants_product_size",
        "product_variants",
        ["product_id", "size"],
        unique=False,
    )
    op.create_index(
        "ix_listings_status_created_at_id",
        "listings",
        ["status", sa.text("created_at DESC"), "id"],
        unique=False,
    )

    op.execute(
        f"""
        CREATE FUNCTION {LOCK_FUNCTION}(p_product_ids uuid[])
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_product_id uuid;
        BEGIN
            FOR v_product_id IN
                SELECT DISTINCT product_id
                FROM unnest(p_product_ids) AS affected(product_id)
                WHERE product_id IS NOT NULL
                ORDER BY product_id
            LOOP
                PERFORM 1
                FROM products
                WHERE id = v_product_id
                FOR UPDATE;
            END LOOP;
        END;
        $$
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION {REFRESH_FUNCTION}(p_product_ids uuid[])
        RETURNS void
        LANGUAGE plpgsql
        AS $$
        DECLARE
            v_product_id uuid;
            v_lowest_ask_cents integer;
        BEGIN
            FOR v_product_id IN
                SELECT DISTINCT product_id
                FROM unnest(p_product_ids) AS affected(product_id)
                WHERE product_id IS NOT NULL
                ORDER BY product_id
            LOOP
                SELECT min(price_cents)
                INTO v_lowest_ask_cents
                FROM listings
                WHERE product_id = v_product_id
                  AND status = 'active'
                  AND available_quantity > 0
                  AND currency = 'USD';

                UPDATE products
                SET lowest_ask_cents = v_lowest_ask_cents
                WHERE id = v_product_id
                  AND lowest_ask_cents IS DISTINCT FROM v_lowest_ask_cents;
            END LOOP;
        END;
        $$
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION {LOCK_TRIGGER_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                PERFORM {LOCK_FUNCTION}(ARRAY[NEW.product_id]);
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                PERFORM {LOCK_FUNCTION}(ARRAY[OLD.product_id]);
                RETURN OLD;
            END IF;

            PERFORM {LOCK_FUNCTION}(ARRAY[OLD.product_id, NEW.product_id]);
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        f"""
        CREATE FUNCTION {TRIGGER_FUNCTION}()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                PERFORM {REFRESH_FUNCTION}(ARRAY[NEW.product_id]);
                RETURN NEW;
            ELSIF TG_OP = 'DELETE' THEN
                PERFORM {REFRESH_FUNCTION}(ARRAY[OLD.product_id]);
                RETURN OLD;
            END IF;

            PERFORM {REFRESH_FUNCTION}(ARRAY[OLD.product_id, NEW.product_id]);
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {LOCK_INSERT_DELETE_TRIGGER}
        BEFORE INSERT OR DELETE ON listings
        FOR EACH ROW EXECUTE FUNCTION {LOCK_TRIGGER_FUNCTION}()
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {LOCK_UPDATE_TRIGGER}
        BEFORE UPDATE OF product_id, price_cents, currency, status, available_quantity ON listings
        FOR EACH ROW
        WHEN (
            OLD.product_id IS DISTINCT FROM NEW.product_id
            OR OLD.price_cents IS DISTINCT FROM NEW.price_cents
            OR OLD.currency IS DISTINCT FROM NEW.currency
            OR OLD.status IS DISTINCT FROM NEW.status
            OR OLD.available_quantity IS DISTINCT FROM NEW.available_quantity
        )
        EXECUTE FUNCTION {LOCK_TRIGGER_FUNCTION}()
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {INSERT_DELETE_TRIGGER}
        AFTER INSERT OR DELETE ON listings
        FOR EACH ROW EXECUTE FUNCTION {TRIGGER_FUNCTION}()
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {UPDATE_TRIGGER}
        AFTER UPDATE OF product_id, price_cents, currency, status, available_quantity ON listings
        FOR EACH ROW
        WHEN (
            OLD.product_id IS DISTINCT FROM NEW.product_id
            OR OLD.price_cents IS DISTINCT FROM NEW.price_cents
            OR OLD.currency IS DISTINCT FROM NEW.currency
            OR OLD.status IS DISTINCT FROM NEW.status
            OR OLD.available_quantity IS DISTINCT FROM NEW.available_quantity
        )
        EXECUTE FUNCTION {TRIGGER_FUNCTION}()
        """
    )

    op.execute(
        """
        UPDATE products AS product
        SET lowest_ask_cents = qualifying.lowest_ask_cents
        FROM (
            SELECT product.id,
                   min(listing.price_cents) FILTER (
                       WHERE listing.status = 'active'
                         AND listing.available_quantity > 0
                         AND listing.currency = 'USD'
                   ) AS lowest_ask_cents
            FROM products AS product
            LEFT JOIN listings AS listing ON listing.product_id = product.id
            GROUP BY product.id
        ) AS qualifying
        WHERE product.id = qualifying.id
          AND product.lowest_ask_cents IS DISTINCT FROM qualifying.lowest_ask_cents
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {UPDATE_TRIGGER} ON listings")
    op.execute(f"DROP TRIGGER IF EXISTS {INSERT_DELETE_TRIGGER} ON listings")
    op.execute(f"DROP TRIGGER IF EXISTS {LOCK_UPDATE_TRIGGER} ON listings")
    op.execute(f"DROP TRIGGER IF EXISTS {LOCK_INSERT_DELETE_TRIGGER} ON listings")
    op.execute(f"DROP FUNCTION IF EXISTS {TRIGGER_FUNCTION}()")
    op.execute(f"DROP FUNCTION IF EXISTS {LOCK_TRIGGER_FUNCTION}()")
    op.execute(f"DROP FUNCTION IF EXISTS {REFRESH_FUNCTION}(uuid[])")
    op.execute(f"DROP FUNCTION IF EXISTS {LOCK_FUNCTION}(uuid[])")
    op.drop_index("ix_listings_status_created_at_id", table_name="listings")
    op.drop_index("ix_product_variants_product_size", table_name="product_variants")
    op.drop_index("ix_listings_qualifying_product_price", table_name="listings")
