CREATE OR REPLACE VIEW restaurant_performance_view AS
SELECT r.restaurant_id, r.name AS restaurant,
       count(o.order_id) AS total_orders,
       count(*) FILTER (WHERE o.order_status = 'DELIVERED') AS delivered_orders,
       count(*) FILTER (WHERE o.order_status = 'CANCELLED') AS cancelled_orders,
       COALESCE(sum(o.total_amount) FILTER (WHERE o.order_status = 'DELIVERED'), 0) AS revenue,
       r.rating AS average_rating,
       COALESCE(avg(o.total_amount) FILTER (WHERE o.order_status = 'DELIVERED'), 0) AS average_order_value
FROM restaurants r LEFT JOIN orders o ON o.restaurant_id = r.restaurant_id
GROUP BY r.restaurant_id, r.name, r.rating;

CREATE OR REPLACE VIEW customer_summary_view AS
SELECT u.user_id, u.full_name AS customer, count(o.order_id) AS total_orders,
       COALESCE(sum(o.total_amount) FILTER (WHERE o.order_status = 'DELIVERED'), 0) AS total_spent,
       COALESCE(avg(o.total_amount) FILTER (WHERE o.order_status = 'DELIVERED'), 0) AS average_order_value,
       max(o.order_time) AS last_order_date
FROM users u LEFT JOIN orders o ON o.user_id = u.user_id
GROUP BY u.user_id, u.full_name;

CREATE OR REPLACE VIEW delivery_agent_performance_view AS
SELECT a.agent_id, a.full_name AS agent,
       count(o.order_id) FILTER (WHERE o.order_status = 'DELIVERED') AS completed_deliveries,
       a.average_rating,
       avg(o.delivered_time - o.picked_up_time) FILTER (WHERE o.order_status = 'DELIVERED') AS average_delivery_time
FROM delivery_agents a LEFT JOIN orders o ON o.delivery_agent_id = a.agent_id
GROUP BY a.agent_id, a.full_name, a.average_rating;

CREATE OR REPLACE VIEW daily_sales_view AS
SELECT order_time::date AS sales_date, count(*) AS order_count, sum(total_amount) AS revenue,
       avg(total_amount) AS average_order_value
FROM orders WHERE order_status = 'DELIVERED' GROUP BY order_time::date;
