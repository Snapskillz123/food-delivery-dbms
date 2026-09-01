# Sample Queries

## Inspect an order timeline

```sql
SELECT o.order_id, o.order_status, h.previous_status, h.new_status, h.changed_at
FROM orders o JOIN order_status_history h USING (order_id)
WHERE o.order_id = 42 ORDER BY h.changed_at;
```

## Reconcile stored financial totals

```sql
SELECT o.order_id, o.total_amount stored_total, c.final_total calculated_total
FROM orders o CROSS JOIN LATERAL calculate_order_total(o.order_id) c
WHERE abs(o.total_amount - c.final_total) > 0.01;
```

## Rank customers by lifetime value

```sql
SELECT customer, total_spent,
       rank() OVER (ORDER BY total_spent DESC) AS spending_rank
FROM customer_summary_view;
```

See [`sql/analytics.sql`](../sql/analytics.sql) for 31 production-readable analyses covering retention, cohorts, trends, item popularity, payment mix, delays, and operational rankings.
