from datetime import datetime, time
from decimal import Decimal
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.models.entities import OrderStatus, PaymentMethod, PaymentStatus


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UserCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=8, max_length=128)


class UserRead(ORMModel):
    user_id: int
    full_name: str
    email: EmailStr
    phone: str
    created_at: datetime


class AddressCreate(BaseModel):
    label: str
    address_line: str
    city: str
    state: str
    postal_code: str
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    is_default: bool = False


class AddressRead(AddressCreate, ORMModel):
    address_id: int
    user_id: int
    created_at: datetime


class RestaurantCreate(BaseModel):
    name: str
    cuisine_type: str
    phone: str
    email: EmailStr | None = None
    address: str
    city: str
    opening_time: time
    closing_time: time


class RestaurantRead(RestaurantCreate, ORMModel):
    restaurant_id: int
    rating: Decimal
    is_active: bool


class MenuItemCreate(BaseModel):
    category_id: int
    item_name: str
    description: str | None = None
    price: Decimal = Field(gt=0)
    is_vegetarian: bool = False
    is_available: bool = True


class MenuItemUpdate(BaseModel):
    item_name: str | None = None
    description: str | None = None
    price: Decimal | None = Field(default=None, gt=0)
    is_vegetarian: bool | None = None
    is_available: bool | None = None
    category_id: int | None = None


class MenuItemRead(MenuItemCreate, ORMModel):
    menu_item_id: int
    restaurant_id: int


class OrderItemCreate(BaseModel):
    menu_item_id: int
    quantity: int = Field(gt=0, le=50)


class OrderCreate(BaseModel):
    user_id: int
    restaurant_id: int
    delivery_address_id: int
    items: list[OrderItemCreate] = Field(min_length=1)
    payment_method: PaymentMethod
    coupon_code: str | None = None


class OrderItemRead(ORMModel):
    order_item_id: int
    menu_item_id: int
    quantity: int
    unit_price: Decimal
    total_price: Decimal


class PaymentRead(ORMModel):
    payment_id: int
    order_id: int
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_reference: str | None
    amount: Decimal
    paid_at: datetime | None


class OrderRead(ORMModel):
    order_id: int
    user_id: int
    restaurant_id: int
    delivery_address_id: int
    delivery_agent_id: int | None
    order_status: OrderStatus
    subtotal: Decimal
    delivery_fee: Decimal
    tax_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    order_time: datetime
    items: list[OrderItemRead] = []
    payment: PaymentRead | None = None


class StatusUpdate(BaseModel):
    status: OrderStatus
    delivery_agent_id: int | None = None


class PaymentUpdate(BaseModel):
    payment_method: PaymentMethod
    payment_status: PaymentStatus
    transaction_reference: str | None = None


class ReviewCreate(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, max_length=2000)


class ReviewRead(ORMModel):
    review_id: int
    order_id: int
    rating: int
    review_text: str | None
    created_at: datetime

