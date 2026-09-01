# Entity–Relationship Diagram

```mermaid
erDiagram
    USERS ||--o{ ADDRESSES : owns
    USERS ||--o{ ORDERS : places
    RESTAURANTS ||--o{ MENU_CATEGORIES : organizes
    RESTAURANTS ||--o{ MENU_ITEMS : offers
    MENU_CATEGORIES ||--o{ MENU_ITEMS : classifies
    RESTAURANTS ||--o{ ORDERS : receives
    ADDRESSES ||--o{ ORDERS : destination
    DELIVERY_AGENTS ||--o{ ORDERS : delivers
    ORDERS ||--|{ ORDER_ITEMS : contains
    MENU_ITEMS ||--o{ ORDER_ITEMS : snapshots
    ORDERS ||--o{ ORDER_STATUS_HISTORY : audits
    ORDERS ||--|| PAYMENTS : has
    USERS ||--o{ RESTAURANT_REVIEWS : writes
    RESTAURANTS ||--o{ RESTAURANT_REVIEWS : receives
    ORDERS ||--o| RESTAURANT_REVIEWS : validates
    USERS ||--o{ DELIVERY_REVIEWS : writes
    DELIVERY_AGENTS ||--o{ DELIVERY_REVIEWS : receives
    ORDERS ||--o| DELIVERY_REVIEWS : validates
    ORDERS ||--o{ ORDER_COUPONS : applies
    COUPONS ||--o{ ORDER_COUPONS : redeemed_as

    USERS {
      bigint user_id PK
      varchar email UK
      varchar phone UK
      varchar password_hash
    }
    ADDRESSES {
      bigint address_id PK
      bigint user_id FK
      boolean is_default
    }
    RESTAURANTS {
      bigint restaurant_id PK
      varchar cuisine_type
      numeric rating
      boolean is_active
    }
    MENU_CATEGORIES {
      bigint category_id PK
      bigint restaurant_id FK
      varchar category_name
    }
    MENU_ITEMS {
      bigint menu_item_id PK
      bigint restaurant_id FK
      bigint category_id FK
      numeric price
      boolean is_available
    }
    DELIVERY_AGENTS {
      bigint agent_id PK
      agent_status current_status
      numeric average_rating
    }
    ORDERS {
      bigint order_id PK
      bigint user_id FK
      bigint restaurant_id FK
      bigint delivery_address_id FK
      bigint delivery_agent_id FK
      order_status order_status
      numeric total_amount
    }
    ORDER_ITEMS {
      bigint order_item_id PK
      bigint order_id FK
      bigint menu_item_id FK
      int quantity
      numeric unit_price
      numeric total_price
    }
    ORDER_STATUS_HISTORY {
      bigint status_history_id PK
      bigint order_id FK
      order_status previous_status
      order_status new_status
      timestamptz changed_at
    }
    PAYMENTS {
      bigint payment_id PK
      bigint order_id FK,UK
      payment_method payment_method
      payment_status payment_status
      numeric amount
    }
    RESTAURANT_REVIEWS {
      bigint review_id PK
      bigint order_id FK,UK
      int rating
    }
    DELIVERY_REVIEWS {
      bigint review_id PK
      bigint order_id FK,UK
      int rating
    }
    COUPONS {
      bigint coupon_id PK
      varchar coupon_code UK
      discount_type discount_type
      numeric discount_value
    }
    ORDER_COUPONS {
      bigint order_id PK,FK
      bigint coupon_id PK,FK
      numeric discount_applied
    }
```

The one-review-per-order constraints make both review relationships optional one-to-one from an order. `ORDER_COUPONS` remains a junction table even though the current API applies at most one coupon; this preserves a clean relational model if stacking is later introduced.

