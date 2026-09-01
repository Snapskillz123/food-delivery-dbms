import enum
from datetime import date, datetime, time
from decimal import Decimal
from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, Time, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AgentStatus(str, enum.Enum):
    AVAILABLE = "AVAILABLE"
    BUSY = "BUSY"
    OFFLINE = "OFFLINE"


class OrderStatus(str, enum.Enum):
    PLACED = "PLACED"
    ACCEPTED = "ACCEPTED"
    PREPARING = "PREPARING"
    READY_FOR_PICKUP = "READY_FOR_PICKUP"
    PICKED_UP = "PICKED_UP"
    OUT_FOR_DELIVERY = "OUT_FOR_DELIVERY"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"


class PaymentMethod(str, enum.Enum):
    UPI = "UPI"
    CARD = "CARD"
    CASH = "CASH"
    WALLET = "WALLET"


class PaymentStatus(str, enum.Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"


class DiscountType(str, enum.Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED = "FIXED"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    addresses: Mapped[list["Address"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    orders: Mapped[list["Order"]] = relationship(back_populates="user")


class Address(TimestampMixin, Base):
    __tablename__ = "addresses"
    address_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id", ondelete="CASCADE"), index=True)
    label: Mapped[str] = mapped_column(String(40))
    address_line: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(100))
    postal_code: Mapped[str] = mapped_column(String(12))
    latitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[Decimal | None] = mapped_column(Numeric(9, 6))
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    user: Mapped[User] = relationship(back_populates="addresses")


class Restaurant(TimestampMixin, Base):
    __tablename__ = "restaurants"
    __table_args__ = (CheckConstraint("rating BETWEEN 0 AND 5", name="ck_restaurant_rating"),)
    restaurant_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    cuisine_type: Mapped[str] = mapped_column(String(100))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True)
    address: Mapped[str] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(100), index=True)
    rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, server_default="0")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    opening_time: Mapped[time] = mapped_column(Time)
    closing_time: Mapped[time] = mapped_column(Time)
    categories: Mapped[list["MenuCategory"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")
    menu_items: Mapped[list["MenuItem"]] = relationship(back_populates="restaurant", cascade="all, delete-orphan")


class MenuCategory(Base):
    __tablename__ = "menu_categories"
    __table_args__ = (UniqueConstraint("restaurant_id", "category_name"),)
    category_id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"))
    category_name: Mapped[str] = mapped_column(String(80))
    restaurant: Mapped[Restaurant] = relationship(back_populates="categories")


class MenuItem(TimestampMixin, Base):
    __tablename__ = "menu_items"
    __table_args__ = (CheckConstraint("price > 0", name="ck_menu_price_positive"),)
    menu_item_id: Mapped[int] = mapped_column(primary_key=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.restaurant_id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int] = mapped_column(ForeignKey("menu_categories.category_id"))
    item_name: Mapped[str] = mapped_column(String(160))
    description: Mapped[str | None] = mapped_column(Text)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    is_vegetarian: Mapped[bool] = mapped_column(Boolean, default=False)
    is_available: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    restaurant: Mapped[Restaurant] = relationship(back_populates="menu_items")


class DeliveryAgent(TimestampMixin, Base):
    __tablename__ = "delivery_agents"
    __table_args__ = (CheckConstraint("average_rating BETWEEN 0 AND 5", name="ck_agent_rating"),)
    agent_id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str] = mapped_column(String(20), unique=True)
    vehicle_number: Mapped[str] = mapped_column(String(30), unique=True)
    vehicle_type: Mapped[str] = mapped_column(String(30))
    current_status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus, name="agent_status"), default=AgentStatus.AVAILABLE)
    average_rating: Mapped[Decimal] = mapped_column(Numeric(3, 2), default=0, server_default="0")


class Order(Base):
    __tablename__ = "orders"
    __table_args__ = (
        CheckConstraint("subtotal >= 0 AND delivery_fee >= 0 AND tax_amount >= 0 AND discount_amount >= 0 AND total_amount >= 0", name="ck_order_nonnegative"),
        CheckConstraint("discount_amount <= subtotal + tax_amount + delivery_fee", name="ck_order_discount_limit"),
    )
    order_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"), index=True)
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.restaurant_id"), index=True)
    delivery_address_id: Mapped[int] = mapped_column(ForeignKey("addresses.address_id"))
    delivery_agent_id: Mapped[int | None] = mapped_column(ForeignKey("delivery_agents.agent_id"), index=True)
    order_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status"), default=OrderStatus.PLACED, index=True)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_fee: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    accepted_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    prepared_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    picked_up_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    delivered_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cancelled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    user: Mapped[User] = relationship(back_populates="orders")
    items: Mapped[list["OrderItem"]] = relationship(back_populates="order", cascade="all, delete-orphan", lazy="selectin")
    payment: Mapped["Payment | None"] = relationship(back_populates="order", uselist=False, lazy="selectin")
    coupons: Mapped[list["OrderCoupon"]] = relationship(cascade="all, delete-orphan", lazy="selectin")


class OrderItem(Base):
    __tablename__ = "order_items"
    __table_args__ = (CheckConstraint("quantity > 0 AND unit_price > 0 AND total_price > 0", name="ck_order_item_positive"),)
    order_item_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), index=True)
    menu_item_id: Mapped[int] = mapped_column(ForeignKey("menu_items.menu_item_id"))
    quantity: Mapped[int] = mapped_column(Integer)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    total_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    order: Mapped[Order] = relationship(back_populates="items")


class OrderStatusHistory(Base):
    __tablename__ = "order_status_history"
    status_history_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), index=True)
    previous_status: Mapped[OrderStatus | None] = mapped_column(Enum(OrderStatus, name="order_status", create_type=False))
    new_status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus, name="order_status", create_type=False))
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"
    __table_args__ = (CheckConstraint("amount >= 0", name="ck_payment_amount"),)
    payment_id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), unique=True, index=True)
    payment_method: Mapped[PaymentMethod] = mapped_column(Enum(PaymentMethod, name="payment_method"))
    payment_status: Mapped[PaymentStatus] = mapped_column(Enum(PaymentStatus, name="payment_status"), default=PaymentStatus.PENDING, index=True)
    transaction_reference: Mapped[str | None] = mapped_column(String(120), unique=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    order: Mapped[Order] = relationship(back_populates="payment")


class RestaurantReview(TimestampMixin, Base):
    __tablename__ = "restaurant_reviews"
    __table_args__ = (UniqueConstraint("order_id"), CheckConstraint("rating BETWEEN 1 AND 5", name="ck_restaurant_review_rating"))
    review_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    restaurant_id: Mapped[int] = mapped_column(ForeignKey("restaurants.restaurant_id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    rating: Mapped[int] = mapped_column(Integer)
    review_text: Mapped[str | None] = mapped_column(Text)


class DeliveryReview(TimestampMixin, Base):
    __tablename__ = "delivery_reviews"
    __table_args__ = (UniqueConstraint("order_id"), CheckConstraint("rating BETWEEN 1 AND 5", name="ck_delivery_review_rating"))
    review_id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    delivery_agent_id: Mapped[int] = mapped_column(ForeignKey("delivery_agents.agent_id"), index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id"))
    rating: Mapped[int] = mapped_column(Integer)
    review_text: Mapped[str | None] = mapped_column(Text)


class Coupon(Base):
    __tablename__ = "coupons"
    __table_args__ = (
        CheckConstraint("discount_value > 0 AND minimum_order_value >= 0 AND (maximum_discount IS NULL OR maximum_discount > 0)", name="ck_coupon_values"),
        CheckConstraint("valid_until >= valid_from", name="ck_coupon_dates"),
        CheckConstraint("usage_limit > 0 AND current_usage BETWEEN 0 AND usage_limit", name="ck_coupon_usage"),
    )
    coupon_id: Mapped[int] = mapped_column(primary_key=True)
    coupon_code: Mapped[str] = mapped_column(String(40), unique=True)
    discount_type: Mapped[DiscountType] = mapped_column(Enum(DiscountType, name="discount_type"))
    discount_value: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    minimum_order_value: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    maximum_discount: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    valid_from: Mapped[date] = mapped_column(Date)
    valid_until: Mapped[date] = mapped_column(Date)
    usage_limit: Mapped[int] = mapped_column(Integer)
    current_usage: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrderCoupon(Base):
    __tablename__ = "order_coupons"
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.order_id", ondelete="CASCADE"), primary_key=True)
    coupon_id: Mapped[int] = mapped_column(ForeignKey("coupons.coupon_id"), primary_key=True)
    discount_applied: Mapped[Decimal] = mapped_column(Numeric(10, 2))
