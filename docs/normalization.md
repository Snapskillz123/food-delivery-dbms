# Normalization

## First Normal Form (1NF)

Every table has a primary key, every column contains one scalar value, and repeating groups are separated. An order does not contain a comma-separated menu list: its lines live in `order_items`. Customer addresses, menu categories, reviews, status events, and coupon redemptions similarly have their own relations.

## Second Normal Form (2NF)

The only composite-key table is `order_coupons(order_id, coupon_id)`. Its non-key value, `discount_applied`, describes that exact redemption and depends on the complete key. All other relations use a single-column surrogate key, so partial dependency cannot occur.

## Third Normal Form (3NF)

Non-key facts depend on the key, the whole key, and nothing but the key:

- Restaurant contact and cuisine data exist only in `restaurants`, not in orders.
- Customer identity is separated from reusable delivery addresses.
- Category names are separated from menu items and scoped to a restaurant.
- Payment lifecycle facts are separated from fulfillment lifecycle facts.
- Coupon definitions are separated from per-order redemptions.
- Review facts reference the delivered order instead of copying order details.

Cross-table triggers additionally ensure a menu item's category belongs to its restaurant and a review's customer/restaurant/agent matches its order.

## Intentional redundancy

Three values are intentionally retained:

1. `order_items.unit_price` snapshots the price at checkout. It intentionally differs from the current `menu_items.price`, preserving financial history.
2. `order_items.total_price` is derived, but stored for auditable invoices and query speed. A trigger guarantees `quantity * unit_price`.
3. `restaurants.rating` and `delivery_agents.average_rating` cache aggregates used in high-read listing screens. Insert/update/delete triggers recalculate them from source reviews.

Order-level subtotal, tax, fee, discount, and total are also immutable financial snapshots. Their arithmetic identity is protected by a database trigger and CHECK constraints.

