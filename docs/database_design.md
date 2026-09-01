# Database Design and Integrity

## Transaction boundaries

`place_order` locks a coupon row, validates customer/address/restaurant/items, calculates money with `Decimal`, inserts the order, line snapshots, pending payment, redemption, and initial audit event in one transaction. An exception rolls back every write.

Cancellation locks the order, validates the state machine, refunds a successful payment, releases an assigned agent, and records status through the audit trigger in one commit. Delivery completion likewise timestamps delivery and releases the agent atomically.

This demonstrates ACID:

- **Atomicity:** each workflow commits all related rows or none.
- **Consistency:** keys, checks, partial unique indexes, triggers, and the state machine preserve invariants.
- **Isolation:** `SELECT … FOR UPDATE` serializes competing coupon, order, and agent changes.
- **Durability:** PostgreSQL WAL persists committed changes.

## Trigger catalogue

| Trigger | Event | Invariant |
|---|---|---|
| `trg_order_status_history` | order insert/status update | immutable lifecycle audit |
| `trg_enforce_order_transition` | before status update | no skipped/terminal transitions |
| `trg_restaurant_rating` | review I/U/D | rating cache equals review average |
| `trg_agent_rating` | review I/U/D | agent cache equals review average |
| `trg_order_item_total` | line I/U | total equals quantity × snapshot price |
| `trg_validate_order_total` | order I/U | financial components reconcile |
| review/category validation triggers | I/U | cross-table ownership rules |

## Index design and EXPLAIN ANALYZE

PostgreSQL may choose a **sequential scan** when a query needs much of a small table; reading pages in order is cheaper than following many index pointers. An **index scan** is valuable for selective predicates. The composite `(restaurant_id, order_time DESC)` index supports equality on restaurant followed by a time range/order. Partial indexes keep hot subsets small.

Capture a baseline in a disposable database before `sql/indexes.sql`, then repeat after creating indexes:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT * FROM orders
WHERE restaurant_id = 7
  AND order_time >= current_date - interval '30 days'
ORDER BY order_time DESC;

EXPLAIN (ANALYZE, BUFFERS)
SELECT oi.menu_item_id, sum(oi.quantity)
FROM order_items oi JOIN orders o USING (order_id)
WHERE o.order_status = 'DELIVERED' AND o.restaurant_id = 7
GROUP BY oi.menu_item_id;
```

Expected change for sufficiently large/selective data: `Seq Scan` plus sort becomes an `Index Scan`/bitmap scan using `idx_orders_restaurant_time`, and joins use the order/item indexes. Exact plans depend on statistics, cache, row count, and selectivity; run `ANALYZE` before comparison and retain the actual outputs for screenshots.

Indexes are not free. Every insert/update must maintain them, they consume disk/cache, and overlapping indexes can confuse maintenance without improving reads. This project indexes foreign-key joins and frequent filter/sort paths rather than every column.

