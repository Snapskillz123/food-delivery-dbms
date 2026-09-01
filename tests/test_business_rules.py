from decimal import Decimal
from app.config import Settings
from app.models.entities import OrderStatus
from app.services.order_service import TRANSITIONS, money


def test_money_rounds_to_currency_precision():
    assert money(Decimal("10.005")) == Decimal("10.01")
    assert money(Decimal("10.004")) == Decimal("10.00")


def test_order_state_machine_has_terminal_states():
    assert TRANSITIONS[OrderStatus.DELIVERED] == set()
    assert TRANSITIONS[OrderStatus.CANCELLED] == set()
    assert OrderStatus.CANCELLED in TRANSITIONS[OrderStatus.PLACED]
    assert OrderStatus.DELIVERED not in TRANSITIONS[OrderStatus.PLACED]


def test_every_nonterminal_progression_is_explicit():
    path = [OrderStatus.PLACED, OrderStatus.ACCEPTED, OrderStatus.PREPARING,
            OrderStatus.READY_FOR_PICKUP, OrderStatus.PICKED_UP,
            OrderStatus.OUT_FOR_DELIVERY, OrderStatus.DELIVERED]
    assert all(next_status in TRANSITIONS[current] for current, next_status in zip(path, path[1:]))


def test_render_postgres_urls_are_normalized_for_each_driver():
    settings = Settings(
        database_url="postgresql://user:secret@host/database",
        sync_database_url="postgresql://user:secret@host/database",
    )
    assert settings.database_url.startswith("postgresql+asyncpg://")
    assert settings.sync_database_url.startswith("postgresql+psycopg2://")
