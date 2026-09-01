CREATE OR REPLACE FUNCTION calculate_order_total(p_order_id BIGINT)
RETURNS TABLE(subtotal NUMERIC, tax NUMERIC, delivery_fee NUMERIC, discount NUMERIC, final_total NUMERIC)
LANGUAGE sql STABLE AS $$
    SELECT COALESCE(sum(oi.total_price), 0)::numeric,
           o.tax_amount, o.delivery_fee, o.discount_amount,
           (COALESCE(sum(oi.total_price), 0) + o.tax_amount + o.delivery_fee - o.discount_amount)::numeric
    FROM orders o LEFT JOIN order_items oi ON oi.order_id = o.order_id
    WHERE o.order_id = p_order_id
    GROUP BY o.order_id, o.tax_amount, o.delivery_fee, o.discount_amount;
$$;

CREATE OR REPLACE FUNCTION get_restaurant_monthly_revenue(p_restaurant_id BIGINT, p_year INTEGER, p_month INTEGER)
RETURNS TABLE(restaurant_id BIGINT, revenue NUMERIC, delivered_orders BIGINT, average_order_value NUMERIC)
LANGUAGE sql STABLE AS $$
    SELECT p_restaurant_id, COALESCE(sum(o.total_amount), 0)::numeric, count(*)::bigint,
           COALESCE(avg(o.total_amount), 0)::numeric
    FROM orders o
    WHERE o.restaurant_id = p_restaurant_id AND o.order_status = 'DELIVERED'
      AND extract(year FROM o.order_time) = p_year AND extract(month FROM o.order_time) = p_month;
$$;

CREATE OR REPLACE FUNCTION get_customer_lifetime_value(p_user_id BIGINT)
RETURNS NUMERIC LANGUAGE sql STABLE AS $$
    SELECT COALESCE(sum(total_amount), 0)::numeric FROM orders
    WHERE user_id = p_user_id AND order_status = 'DELIVERED';
$$;

CREATE OR REPLACE FUNCTION get_agent_performance(p_agent_id BIGINT)
RETURNS TABLE(agent_id BIGINT, deliveries_completed BIGINT, average_rating NUMERIC, average_delivery_duration INTERVAL)
LANGUAGE sql STABLE AS $$
    SELECT p_agent_id, count(o.order_id)::bigint, COALESCE(a.average_rating, 0),
           avg(o.delivered_time - o.picked_up_time)
    FROM delivery_agents a LEFT JOIN orders o ON o.delivery_agent_id = a.agent_id AND o.order_status = 'DELIVERED'
    WHERE a.agent_id = p_agent_id GROUP BY a.agent_id, a.average_rating;
$$;

CREATE OR REPLACE FUNCTION apply_coupon(p_coupon_code TEXT, p_order_value NUMERIC)
RETURNS NUMERIC LANGUAGE plpgsql STABLE AS $$
DECLARE c coupons%ROWTYPE; result NUMERIC;
BEGIN
    SELECT * INTO c FROM coupons WHERE coupon_code = upper(p_coupon_code);
    IF NOT FOUND OR NOT c.is_active OR current_date NOT BETWEEN c.valid_from AND c.valid_until
       OR c.current_usage >= c.usage_limit OR p_order_value < c.minimum_order_value THEN RETURN 0; END IF;
    result := CASE WHEN c.discount_type = 'PERCENTAGE' THEN p_order_value * c.discount_value / 100 ELSE c.discount_value END;
    result := LEAST(result, p_order_value);
    IF c.maximum_discount IS NOT NULL THEN result := LEAST(result, c.maximum_discount); END IF;
    RETURN round(result, 2);
END $$;

