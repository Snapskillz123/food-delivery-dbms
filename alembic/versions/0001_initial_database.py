"""Create normalized database and database-native behavior."""
from pathlib import Path
from alembic import op

revision = "0001_initial_database"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    root = Path(__file__).resolve().parents[2]
    # Use Alembic's active transaction but bypass SQLAlchemy's percent-style
    # parameter parsing: PL/pgSQL RAISE statements legitimately contain `%`.
    cursor = op.get_bind().connection.driver_connection.cursor()
    try:
        for filename in ("schema.sql", "constraints.sql", "indexes.sql", "triggers.sql", "functions.sql", "views.sql"):
            cursor.execute((root / "sql" / filename).read_text(encoding="utf-8"))
    finally:
        cursor.close()


def downgrade() -> None:
    op.get_bind().exec_driver_sql("""
        DROP TABLE IF EXISTS order_coupons, delivery_reviews, restaurant_reviews, payments,
          order_status_history, order_items, orders, coupons, delivery_agents, menu_items,
          menu_categories, restaurants, addresses, users CASCADE;
        DROP TYPE IF EXISTS discount_type, payment_status, payment_method, order_status, agent_status CASCADE;
    """)
