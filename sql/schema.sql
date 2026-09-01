-- Canonical PostgreSQL schema. Safe to run once on a new database.
CREATE TYPE agent_status AS ENUM ('AVAILABLE', 'BUSY', 'OFFLINE');
CREATE TYPE order_status AS ENUM ('PLACED', 'ACCEPTED', 'PREPARING', 'READY_FOR_PICKUP', 'PICKED_UP', 'OUT_FOR_DELIVERY', 'DELIVERED', 'CANCELLED');
CREATE TYPE payment_method AS ENUM ('UPI', 'CARD', 'CASH', 'WALLET');
CREATE TYPE payment_status AS ENUM ('PENDING', 'SUCCESS', 'FAILED', 'REFUNDED');
CREATE TYPE discount_type AS ENUM ('PERCENTAGE', 'FIXED');

CREATE TABLE users (
    user_id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    phone VARCHAR(20) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE addresses (
    address_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    label VARCHAR(40) NOT NULL,
    address_line TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    state VARCHAR(100) NOT NULL,
    postal_code VARCHAR(12) NOT NULL,
    latitude NUMERIC(9,6) CHECK (latitude BETWEEN -90 AND 90),
    longitude NUMERIC(9,6) CHECK (longitude BETWEEN -180 AND 180),
    is_default BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE restaurants (
    restaurant_id BIGSERIAL PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    cuisine_type VARCHAR(100) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    email VARCHAR(255) UNIQUE,
    address TEXT NOT NULL,
    city VARCHAR(100) NOT NULL,
    rating NUMERIC(3,2) NOT NULL DEFAULT 0 CHECK (rating BETWEEN 0 AND 5),
    is_active BOOLEAN NOT NULL DEFAULT true,
    opening_time TIME NOT NULL,
    closing_time TIME NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE menu_categories (
    category_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT NOT NULL REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    category_name VARCHAR(80) NOT NULL,
    UNIQUE (restaurant_id, category_name)
);

CREATE TABLE menu_items (
    menu_item_id BIGSERIAL PRIMARY KEY,
    restaurant_id BIGINT NOT NULL REFERENCES restaurants(restaurant_id) ON DELETE CASCADE,
    category_id BIGINT NOT NULL REFERENCES menu_categories(category_id),
    item_name VARCHAR(160) NOT NULL,
    description TEXT,
    price NUMERIC(10,2) NOT NULL CHECK (price > 0),
    is_vegetarian BOOLEAN NOT NULL DEFAULT false,
    is_available BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (restaurant_id, item_name)
);

CREATE TABLE delivery_agents (
    agent_id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(120) NOT NULL,
    phone VARCHAR(20) NOT NULL UNIQUE,
    vehicle_number VARCHAR(30) NOT NULL UNIQUE,
    vehicle_type VARCHAR(30) NOT NULL,
    current_status agent_status NOT NULL DEFAULT 'AVAILABLE',
    average_rating NUMERIC(3,2) NOT NULL DEFAULT 0 CHECK (average_rating BETWEEN 0 AND 5),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    order_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    restaurant_id BIGINT NOT NULL REFERENCES restaurants(restaurant_id),
    delivery_address_id BIGINT NOT NULL REFERENCES addresses(address_id),
    delivery_agent_id BIGINT REFERENCES delivery_agents(agent_id),
    order_status order_status NOT NULL DEFAULT 'PLACED',
    subtotal NUMERIC(12,2) NOT NULL,
    delivery_fee NUMERIC(10,2) NOT NULL DEFAULT 0,
    tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    discount_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
    total_amount NUMERIC(12,2) NOT NULL,
    order_time TIMESTAMPTZ NOT NULL DEFAULT now(),
    accepted_time TIMESTAMPTZ,
    prepared_time TIMESTAMPTZ,
    picked_up_time TIMESTAMPTZ,
    delivered_time TIMESTAMPTZ,
    cancelled_time TIMESTAMPTZ,
    CONSTRAINT ck_order_nonnegative CHECK (subtotal >= 0 AND delivery_fee >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0),
    CONSTRAINT ck_order_discount_limit CHECK (discount_amount <= subtotal + tax_amount + delivery_fee)
);

CREATE TABLE order_items (
    order_item_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    menu_item_id BIGINT NOT NULL REFERENCES menu_items(menu_item_id),
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(10,2) NOT NULL CHECK (unit_price > 0),
    total_price NUMERIC(12,2) NOT NULL CHECK (total_price > 0),
    UNIQUE (order_id, menu_item_id)
);

CREATE TABLE order_status_history (
    status_history_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    previous_status order_status,
    new_status order_status NOT NULL,
    changed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE payments (
    payment_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL UNIQUE REFERENCES orders(order_id) ON DELETE CASCADE,
    payment_method payment_method NOT NULL,
    payment_status payment_status NOT NULL DEFAULT 'PENDING',
    transaction_reference VARCHAR(120) UNIQUE,
    amount NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE restaurant_reviews (
    review_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    restaurant_id BIGINT NOT NULL REFERENCES restaurants(restaurant_id),
    order_id BIGINT NOT NULL UNIQUE REFERENCES orders(order_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE delivery_reviews (
    review_id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(user_id),
    delivery_agent_id BIGINT NOT NULL REFERENCES delivery_agents(agent_id),
    order_id BIGINT NOT NULL UNIQUE REFERENCES orders(order_id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    review_text TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE coupons (
    coupon_id BIGSERIAL PRIMARY KEY,
    coupon_code VARCHAR(40) NOT NULL UNIQUE,
    discount_type discount_type NOT NULL,
    discount_value NUMERIC(10,2) NOT NULL CHECK (discount_value > 0),
    minimum_order_value NUMERIC(10,2) NOT NULL DEFAULT 0 CHECK (minimum_order_value >= 0),
    maximum_discount NUMERIC(10,2) CHECK (maximum_discount IS NULL OR maximum_discount > 0),
    valid_from DATE NOT NULL,
    valid_until DATE NOT NULL,
    usage_limit INTEGER NOT NULL CHECK (usage_limit > 0),
    current_usage INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    CHECK (valid_until >= valid_from),
    CHECK (current_usage BETWEEN 0 AND usage_limit),
    CHECK (discount_type <> 'PERCENTAGE' OR discount_value <= 100)
);

CREATE TABLE order_coupons (
    order_id BIGINT NOT NULL REFERENCES orders(order_id) ON DELETE CASCADE,
    coupon_id BIGINT NOT NULL REFERENCES coupons(coupon_id),
    discount_applied NUMERIC(10,2) NOT NULL CHECK (discount_applied >= 0),
    PRIMARY KEY (order_id, coupon_id)
);

