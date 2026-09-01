-- Cross-row rules that CHECK constraints cannot express.
CREATE UNIQUE INDEX uq_default_address_per_user ON addresses(user_id) WHERE is_default;
CREATE UNIQUE INDEX uq_active_order_per_agent ON orders(delivery_agent_id)
WHERE delivery_agent_id IS NOT NULL AND order_status IN ('ACCEPTED','PREPARING','READY_FOR_PICKUP','PICKED_UP','OUT_FOR_DELIVERY');

CREATE OR REPLACE FUNCTION validate_menu_item_category() RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM menu_categories c WHERE c.category_id = NEW.category_id AND c.restaurant_id = NEW.restaurant_id) THEN
        RAISE EXCEPTION 'menu category must belong to the same restaurant';
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_menu_item_category BEFORE INSERT OR UPDATE ON menu_items
FOR EACH ROW EXECUTE FUNCTION validate_menu_item_category();

CREATE OR REPLACE FUNCTION validate_review_order() RETURNS TRIGGER LANGUAGE plpgsql AS $$
DECLARE o orders%ROWTYPE;
BEGIN
    SELECT * INTO o FROM orders WHERE order_id = NEW.order_id;
    IF NOT FOUND OR o.order_status <> 'DELIVERED' OR o.user_id <> NEW.user_id THEN
        RAISE EXCEPTION 'reviews require the same customer''s delivered order';
    END IF;
    IF TG_TABLE_NAME = 'restaurant_reviews' THEN
        IF o.restaurant_id <> NEW.restaurant_id THEN
            RAISE EXCEPTION 'review restaurant does not match order';
        END IF;
    ELSE
        IF o.delivery_agent_id IS DISTINCT FROM NEW.delivery_agent_id THEN
            RAISE EXCEPTION 'review delivery agent does not match order';
        END IF;
    END IF;
    RETURN NEW;
END $$;
CREATE TRIGGER trg_validate_restaurant_review BEFORE INSERT OR UPDATE ON restaurant_reviews FOR EACH ROW EXECUTE FUNCTION validate_review_order();
CREATE TRIGGER trg_validate_delivery_review BEFORE INSERT OR UPDATE ON delivery_reviews FOR EACH ROW EXECUTE FUNCTION validate_review_order();
