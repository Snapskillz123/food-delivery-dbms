-- 1. Audit initial status and every later status transition.
CREATE OR REPLACE FUNCTION audit_order_status() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF TG_OP = 'INSERT' OR NEW.order_status IS DISTINCT FROM OLD.order_status THEN
        INSERT INTO order_status_history(order_id, previous_status, new_status, changed_at)
        VALUES (NEW.order_id, CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.order_status END, NEW.order_status, now());
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_order_status_history AFTER INSERT OR UPDATE OF order_status ON orders
FOR EACH ROW EXECUTE FUNCTION audit_order_status();

-- Reject invalid state-machine jumps even when SQL bypasses the API.
CREATE OR REPLACE FUNCTION enforce_order_status_transition() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.order_status = OLD.order_status THEN RETURN NEW; END IF;
    IF NOT (
        (OLD.order_status = 'PLACED' AND NEW.order_status IN ('ACCEPTED','CANCELLED')) OR
        (OLD.order_status = 'ACCEPTED' AND NEW.order_status IN ('PREPARING','CANCELLED')) OR
        (OLD.order_status = 'PREPARING' AND NEW.order_status IN ('READY_FOR_PICKUP','CANCELLED')) OR
        (OLD.order_status = 'READY_FOR_PICKUP' AND NEW.order_status IN ('PICKED_UP','CANCELLED')) OR
        (OLD.order_status = 'PICKED_UP' AND NEW.order_status = 'OUT_FOR_DELIVERY') OR
        (OLD.order_status = 'OUT_FOR_DELIVERY' AND NEW.order_status = 'DELIVERED')
    ) THEN RAISE EXCEPTION 'invalid order transition: % -> %', OLD.order_status, NEW.order_status; END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_enforce_order_transition BEFORE UPDATE OF order_status ON orders
FOR EACH ROW EXECUTE FUNCTION enforce_order_status_transition();

-- 2. Denormalized restaurant rating cache, maintained from its source rows.
CREATE OR REPLACE FUNCTION refresh_restaurant_rating() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE target_id BIGINT := COALESCE(NEW.restaurant_id, OLD.restaurant_id);
BEGIN
    UPDATE restaurants SET rating = COALESCE((SELECT round(avg(rating)::numeric, 2) FROM restaurant_reviews WHERE restaurant_id = target_id), 0)
    WHERE restaurant_id = target_id;
    RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER trg_restaurant_rating AFTER INSERT OR UPDATE OR DELETE ON restaurant_reviews
FOR EACH ROW EXECUTE FUNCTION refresh_restaurant_rating();

-- 3. Denormalized delivery-agent rating cache.
CREATE OR REPLACE FUNCTION refresh_agent_rating() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE target_id BIGINT := COALESCE(NEW.delivery_agent_id, OLD.delivery_agent_id);
BEGIN
    UPDATE delivery_agents SET average_rating = COALESCE((SELECT round(avg(rating)::numeric, 2) FROM delivery_reviews WHERE delivery_agent_id = target_id), 0)
    WHERE agent_id = target_id;
    RETURN COALESCE(NEW, OLD);
END $$;
CREATE TRIGGER trg_agent_rating AFTER INSERT OR UPDATE OR DELETE ON delivery_reviews
FOR EACH ROW EXECUTE FUNCTION refresh_agent_rating();

-- 4. Snapshot line totals are always quantity * price.
CREATE OR REPLACE FUNCTION set_order_item_total() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    NEW.total_price := round(NEW.quantity * NEW.unit_price, 2);
    RETURN NEW;
END $$;
CREATE TRIGGER trg_order_item_total BEFORE INSERT OR UPDATE OF quantity, unit_price ON order_items
FOR EACH ROW EXECUTE FUNCTION set_order_item_total();

-- 5. Financial identity check, within a cent for numeric rounding.
CREATE OR REPLACE FUNCTION validate_order_total() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.subtotal < 0 OR NEW.delivery_fee < 0 OR NEW.tax_amount < 0 OR NEW.discount_amount < 0 OR
       NEW.discount_amount > NEW.subtotal + NEW.delivery_fee + NEW.tax_amount OR
       abs(NEW.total_amount - (NEW.subtotal + NEW.delivery_fee + NEW.tax_amount - NEW.discount_amount)) > 0.01 THEN
        RAISE EXCEPTION 'invalid order financial totals';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_validate_order_total BEFORE INSERT OR UPDATE OF subtotal, delivery_fee, tax_amount, discount_amount, total_amount ON orders
FOR EACH ROW EXECUTE FUNCTION validate_order_total();

