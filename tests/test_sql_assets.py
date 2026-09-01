from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_required_sql_assets_are_nonempty():
    expected = {"schema.sql", "constraints.sql", "indexes.sql", "triggers.sql", "functions.sql", "views.sql", "analytics.sql", "seed.sql"}
    actual = {path.name for path in (ROOT / "sql").glob("*.sql") if path.stat().st_size > 0}
    assert expected <= actual


def test_analytics_contains_thirty_labeled_queries_and_windows():
    sql = (ROOT / "sql" / "analytics.sql").read_text(encoding="utf-8").lower()
    assert sum(1 for line in sql.splitlines() if line.startswith("-- ") and line[3:5].isdigit()) >= 30
    for construct in ("rank() over", "dense_rank() over", "row_number() over", "lag(", "with recursive"):
        assert construct in sql


def test_five_core_trigger_families_exist():
    sql = (ROOT / "sql" / "triggers.sql").read_text(encoding="utf-8")
    for trigger in ("trg_order_status_history", "trg_restaurant_rating", "trg_agent_rating", "trg_order_item_total", "trg_validate_order_total"):
        assert trigger in sql

