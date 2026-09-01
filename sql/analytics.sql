-- 01. Top 10 restaurants by delivered revenue.
SELECT r.name, sum(o.total_amount) AS revenue FROM restaurants r JOIN orders o USING (restaurant_id)
WHERE o.order_status='DELIVERED' GROUP BY r.restaurant_id ORDER BY revenue DESC LIMIT 10;

-- 02. Top restaurants by order count.
SELECT r.name, count(*) AS orders FROM restaurants r JOIN orders o USING (restaurant_id)
GROUP BY r.restaurant_id ORDER BY orders DESC;

-- 03. Average delivered order value by restaurant.
SELECT r.name, round(avg(o.total_amount),2) AS average_order_value FROM restaurants r JOIN orders o USING (restaurant_id)
WHERE o.order_status='DELIVERED' GROUP BY r.restaurant_id ORDER BY average_order_value DESC;

-- 04. Monthly revenue trend.
SELECT date_trunc('month',order_time)::date AS month, sum(total_amount) AS revenue FROM orders
WHERE order_status='DELIVERED' GROUP BY 1 ORDER BY 1;

-- 05. Daily revenue trend.
SELECT * FROM daily_sales_view ORDER BY sales_date;

-- 06. Most popular menu items by quantity and line revenue.
SELECT mi.item_name, r.name, sum(oi.quantity) AS units, sum(oi.total_price) AS revenue
FROM order_items oi JOIN menu_items mi USING(menu_item_id) JOIN restaurants r USING(restaurant_id)
JOIN orders o USING(order_id) WHERE o.order_status='DELIVERED'
GROUP BY mi.menu_item_id,r.restaurant_id ORDER BY units DESC LIMIT 20;

-- 07. Most popular cuisine.
SELECT r.cuisine_type, count(*) AS orders, sum(o.total_amount) FILTER(WHERE o.order_status='DELIVERED') AS revenue
FROM orders o JOIN restaurants r USING(restaurant_id) GROUP BY r.cuisine_type ORDER BY orders DESC;

-- 08. Peak ordering hour.
SELECT extract(hour FROM order_time)::int AS hour, count(*) AS orders FROM orders GROUP BY 1 ORDER BY orders DESC;

-- 09. Peak ordering weekday.
SELECT to_char(order_time,'FMDay') AS weekday, extract(isodow FROM order_time) AS weekday_number, count(*) AS orders
FROM orders GROUP BY 1,2 ORDER BY orders DESC;

-- 10. Customer repeat-order rate (customers with 2+ orders / customers with orders).
WITH counts AS (SELECT user_id,count(*) n FROM orders GROUP BY user_id)
SELECT round(100.0*count(*) FILTER(WHERE n>=2)/NULLIF(count(*),0),2) AS repeat_customer_percentage FROM counts;

-- 11. Top customers by lifetime spend.
SELECT u.user_id,u.full_name,sum(o.total_amount) AS lifetime_spend FROM users u JOIN orders o USING(user_id)
WHERE o.order_status='DELIVERED' GROUP BY u.user_id ORDER BY lifetime_spend DESC LIMIT 20;

-- 12. Average orders per ordering customer.
SELECT round(avg(order_count),2) FROM (SELECT user_id,count(*) order_count FROM orders GROUP BY user_id) x;

-- 13. Customer spending rank.
WITH spend AS (SELECT user_id,sum(total_amount) total FROM orders WHERE order_status='DELIVERED' GROUP BY user_id)
SELECT u.full_name,s.total,rank() OVER(ORDER BY s.total DESC) AS spending_rank FROM spend s JOIN users u USING(user_id);

-- 14. Restaurant revenue dense rank (ties share rank without gaps).
SELECT restaurant,revenue,dense_rank() OVER(ORDER BY revenue DESC) AS revenue_rank FROM restaurant_performance_view;

-- 15. Running monthly revenue.
WITH m AS (SELECT date_trunc('month',order_time)::date AS revenue_month,sum(total_amount) revenue FROM orders
WHERE order_status='DELIVERED' GROUP BY 1)
SELECT revenue_month,revenue,sum(revenue) OVER(ORDER BY revenue_month) AS running_revenue FROM m ORDER BY revenue_month;

-- 16. Month-over-month revenue growth using LAG.
WITH m AS (SELECT date_trunc('month',order_time)::date AS revenue_month,sum(total_amount) revenue FROM orders
WHERE order_status='DELIVERED' GROUP BY 1), p AS (SELECT *,lag(revenue) OVER(ORDER BY revenue_month) previous_revenue FROM m)
SELECT *,round(100*(revenue-previous_revenue)/NULLIF(previous_revenue,0),2) AS growth_pct FROM p ORDER BY revenue_month;

-- 17. Average restaurant preparation time.
SELECT r.name,avg(o.prepared_time-o.accepted_time) AS average_preparation_time FROM restaurants r JOIN orders o USING(restaurant_id)
WHERE o.prepared_time IS NOT NULL AND o.accepted_time IS NOT NULL GROUP BY r.restaurant_id;

-- 18. Average delivery duration.
SELECT avg(delivered_time-picked_up_time) AS average_delivery_duration FROM orders
WHERE order_status='DELIVERED' AND picked_up_time IS NOT NULL;

-- 19. Delivery agent ranking (volume, then speed and rating).
SELECT *,dense_rank() OVER(ORDER BY completed_deliveries DESC,average_rating DESC,average_delivery_time) AS performance_rank
FROM delivery_agent_performance_view;

-- 20. Cancellation rate by restaurant.
SELECT r.name,count(*) AS total_orders,round(100.0*count(*) FILTER(WHERE o.order_status='CANCELLED')/count(*),2) cancellation_pct
FROM restaurants r JOIN orders o USING(restaurant_id) GROUP BY r.restaurant_id ORDER BY cancellation_pct DESC;

-- 21. Payment method distribution.
SELECT payment_method,count(*) transactions,round(100.0*count(*)/sum(count(*)) OVER(),2) percentage,
       sum(amount) FILTER(WHERE payment_status='SUCCESS') successful_value FROM payments GROUP BY payment_method;

-- 22. Coupon usage analysis.
SELECT c.coupon_code,count(oc.order_id) uses,sum(oc.discount_applied) discount_given,
       sum(o.total_amount) FILTER(WHERE o.order_status='DELIVERED') delivered_revenue
FROM coupons c LEFT JOIN order_coupons oc USING(coupon_id) LEFT JOIN orders o USING(order_id) GROUP BY c.coupon_id ORDER BY uses DESC;

-- 23. Restaurant rating vs revenue.
SELECT restaurant,average_rating,revenue,total_orders FROM restaurant_performance_view ORDER BY average_rating DESC,revenue DESC;

-- 24. Customers who have not ordered in the last 30 days (including never ordered).
SELECT u.user_id,u.full_name,max(o.order_time) last_order FROM users u LEFT JOIN orders o USING(user_id)
GROUP BY u.user_id HAVING max(o.order_time)<current_date-interval '30 days' OR max(o.order_time) IS NULL;

-- 25. Top 3 menu items per restaurant using ROW_NUMBER.
WITH sales AS (SELECT mi.restaurant_id,mi.menu_item_id,mi.item_name,sum(oi.quantity) units
FROM menu_items mi JOIN order_items oi USING(menu_item_id) JOIN orders o USING(order_id)
WHERE o.order_status='DELIVERED' GROUP BY mi.restaurant_id,mi.menu_item_id), ranked AS
(SELECT *,row_number() OVER(PARTITION BY restaurant_id ORDER BY units DESC) rn FROM sales)
SELECT r.name,item_name,units,rn FROM ranked JOIN restaurants r USING(restaurant_id) WHERE rn<=3 ORDER BY r.name,rn;

-- 26. Each restaurant's contribution to delivered order count and revenue.
WITH s AS (SELECT restaurant_id,count(*) orders,sum(total_amount) revenue FROM orders WHERE order_status='DELIVERED' GROUP BY restaurant_id)
SELECT r.name,s.*,round(100.0*orders/sum(orders) OVER(),2) order_share_pct,
round(100.0*revenue/sum(revenue) OVER(),2) revenue_share_pct FROM s JOIN restaurants r USING(restaurant_id);

-- 27. First-order-month cohort activity by months since acquisition.
WITH activity AS (SELECT user_id,date_trunc('month',order_time)::date activity_month,
min(date_trunc('month',order_time)::date) OVER(PARTITION BY user_id) cohort_month FROM orders), cohorts AS
(SELECT cohort_month,activity_month,((extract(year FROM age(activity_month,cohort_month))*12)+extract(month FROM age(activity_month,cohort_month)))::int month_number,user_id FROM activity)
SELECT cohort_month,month_number,count(DISTINCT user_id) active_customers FROM cohorts GROUP BY 1,2 ORDER BY 1,2;

-- 28. Average time between each customer's orders.
WITH gaps AS (SELECT user_id,order_time-lag(order_time) OVER(PARTITION BY user_id ORDER BY order_time) gap FROM orders)
SELECT u.full_name,avg(g.gap) average_time_between_orders FROM gaps g JOIN users u USING(user_id) WHERE gap IS NOT NULL GROUP BY u.user_id;

-- 29. Restaurant repeat-customer rate.
WITH customer_counts AS (SELECT restaurant_id,user_id,count(*) n FROM orders GROUP BY restaurant_id,user_id)
SELECT r.name,round(100.0*count(*) FILTER(WHERE n>1)/NULLIF(count(*),0),2) repeat_customer_pct
FROM customer_counts c JOIN restaurants r USING(restaurant_id) GROUP BY r.restaurant_id;

-- 30. Delivery delays by order hour (over 45 minutes from placement).
SELECT extract(hour FROM order_time)::int order_hour,count(*) delivered,
count(*) FILTER(WHERE delivered_time-order_time>interval '45 minutes') delayed,
round(100.0*count(*) FILTER(WHERE delivered_time-order_time>interval '45 minutes')/count(*),2) delay_pct
FROM orders WHERE order_status='DELIVERED' GROUP BY 1 ORDER BY 1;

-- 31. Recursive CTE documents the allowed path and minimum steps from PLACED.
WITH RECURSIVE transitions(previous_status,new_status) AS (VALUES
('PLACED','ACCEPTED'),('ACCEPTED','PREPARING'),('PREPARING','READY_FOR_PICKUP'),
('READY_FOR_PICKUP','PICKED_UP'),('PICKED_UP','OUT_FOR_DELIVERY'),('OUT_FOR_DELIVERY','DELIVERED')),
path(status,step) AS (SELECT 'PLACED'::text,0 UNION ALL SELECT t.new_status,p.step+1 FROM path p JOIN transitions t ON t.previous_status=p.status)
SELECT * FROM path ORDER BY step;
