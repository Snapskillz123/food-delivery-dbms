from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.config import settings
from app.models.entities import (
    Address, AgentStatus, Coupon, DeliveryAgent, DiscountType, MenuItem, Order,
    OrderCoupon, OrderItem, OrderStatus, Payment, PaymentStatus, Restaurant,
)
from app.schemas.api import OrderCreate

MONEY = Decimal("0.01")
ACTIVE_STATUSES = {
    OrderStatus.ACCEPTED, OrderStatus.PREPARING, OrderStatus.READY_FOR_PICKUP,
    OrderStatus.PICKED_UP, OrderStatus.OUT_FOR_DELIVERY,
}
TRANSITIONS = {
    OrderStatus.PLACED: {OrderStatus.ACCEPTED, OrderStatus.CANCELLED},
    OrderStatus.ACCEPTED: {OrderStatus.PREPARING, OrderStatus.CANCELLED},
    OrderStatus.PREPARING: {OrderStatus.READY_FOR_PICKUP, OrderStatus.CANCELLED},
    OrderStatus.READY_FOR_PICKUP: {OrderStatus.PICKED_UP, OrderStatus.CANCELLED},
    OrderStatus.PICKED_UP: {OrderStatus.OUT_FOR_DELIVERY},
    OrderStatus.OUT_FOR_DELIVERY: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}


def money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


async def _coupon_discount(session: AsyncSession, code: str | None, subtotal: Decimal) -> tuple[Coupon | None, Decimal]:
    if not code:
        return None, Decimal("0.00")
    coupon = (await session.execute(
        select(Coupon).where(Coupon.coupon_code == code.upper()).with_for_update()
    )).scalar_one_or_none()
    today = datetime.now(UTC).date()
    if not coupon or not coupon.is_active or not (coupon.valid_from <= today <= coupon.valid_until):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Coupon is invalid or expired")
    if coupon.current_usage >= coupon.usage_limit or subtotal < coupon.minimum_order_value:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Coupon usage or minimum-order requirement not met")
    raw = subtotal * coupon.discount_value / Decimal("100") if coupon.discount_type == DiscountType.PERCENTAGE else coupon.discount_value
    if coupon.maximum_discount is not None:
        raw = min(raw, coupon.maximum_discount)
    return coupon, money(min(raw, subtotal))


async def place_order(session: AsyncSession, payload: OrderCreate) -> Order:
    """Create every order component in one ACID transaction; callers must not pre-calculate totals."""
    async with session.begin():
        restaurant = await session.get(Restaurant, payload.restaurant_id)
        address = await session.get(Address, payload.delivery_address_id)
        if not restaurant or not restaurant.is_active:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Restaurant is unavailable")
        if not address or address.user_id != payload.user_id:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Delivery address does not belong to customer")
        ids = [line.menu_item_id for line in payload.items]
        if len(ids) != len(set(ids)):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Duplicate menu item lines are not allowed")
        items = (await session.execute(select(MenuItem).where(MenuItem.menu_item_id.in_(ids)))).scalars().all()
        by_id = {item.menu_item_id: item for item in items}
        if len(by_id) != len(ids):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "One or more menu items do not exist")
        if any(item.restaurant_id != payload.restaurant_id or not item.is_available for item in items):
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "All items must be available and belong to the restaurant")
        subtotal = money(sum((by_id[line.menu_item_id].price * line.quantity for line in payload.items), Decimal("0")))
        coupon, discount = await _coupon_discount(session, payload.coupon_code, subtotal)
        tax = money(subtotal * Decimal(str(settings.tax_rate)))
        delivery_fee = money(Decimal(str(settings.default_delivery_fee)))
        total = money(subtotal + tax + delivery_fee - discount)
        order = Order(user_id=payload.user_id, restaurant_id=payload.restaurant_id, delivery_address_id=payload.delivery_address_id,
                      order_status=OrderStatus.PLACED, subtotal=subtotal, delivery_fee=delivery_fee,
                      tax_amount=tax, discount_amount=discount, total_amount=total)
        session.add(order)
        await session.flush()
        session.add_all([OrderItem(order_id=order.order_id, menu_item_id=line.menu_item_id, quantity=line.quantity,
                                   unit_price=by_id[line.menu_item_id].price,
                                   total_price=money(by_id[line.menu_item_id].price * line.quantity)) for line in payload.items])
        session.add(Payment(order_id=order.order_id, payment_method=payload.payment_method,
                            payment_status=PaymentStatus.PENDING, amount=total))
        if coupon:
            coupon.current_usage += 1
            session.add(OrderCoupon(order_id=order.order_id, coupon_id=coupon.coupon_id, discount_applied=discount))
    return await get_order(session, order.order_id)


async def get_order(session: AsyncSession, order_id: int, lock: bool = False) -> Order:
    stmt = select(Order).options(selectinload(Order.items), selectinload(Order.payment), selectinload(Order.coupons)).where(Order.order_id == order_id)
    if lock:
        stmt = stmt.with_for_update()
    order = (await session.execute(stmt)).scalar_one_or_none()
    if not order:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Order not found")
    return order


async def update_status(session: AsyncSession, order_id: int, new_status: OrderStatus, agent_id: int | None = None) -> Order:
    async with session.begin():
        order = await get_order(session, order_id, lock=True)
        if new_status not in TRANSITIONS[order.order_status]:
            raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot transition {order.order_status.value} to {new_status.value}")
        now = datetime.now(UTC)
        if new_status == OrderStatus.ACCEPTED:
            order.accepted_time = now
        elif new_status == OrderStatus.READY_FOR_PICKUP:
            order.prepared_time = now
        elif new_status == OrderStatus.PICKED_UP:
            if not agent_id and not order.delivery_agent_id:
                raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A delivery agent is required")
            chosen_id = agent_id or order.delivery_agent_id
            agent = (await session.execute(select(DeliveryAgent).where(DeliveryAgent.agent_id == chosen_id).with_for_update())).scalar_one_or_none()
            if not agent or agent.current_status != AgentStatus.AVAILABLE:
                raise HTTPException(status.HTTP_409_CONFLICT, "Delivery agent is not available")
            active = await session.scalar(select(Order.order_id).where(Order.delivery_agent_id == chosen_id, Order.order_status.in_(ACTIVE_STATUSES)))
            if active:
                raise HTTPException(status.HTTP_409_CONFLICT, "Delivery agent already has an active order")
            order.delivery_agent_id, agent.current_status, order.picked_up_time = chosen_id, AgentStatus.BUSY, now
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_time = now
            if order.delivery_agent_id:
                agent = await session.get(DeliveryAgent, order.delivery_agent_id, with_for_update=True)
                agent.current_status = AgentStatus.AVAILABLE
        order.order_status = new_status
    return await get_order(session, order_id)


async def cancel_order(session: AsyncSession, order_id: int) -> Order:
    async with session.begin():
        order = await get_order(session, order_id, lock=True)
        if OrderStatus.CANCELLED not in TRANSITIONS[order.order_status]:
            raise HTTPException(status.HTTP_409_CONFLICT, "Order can no longer be cancelled")
        order.order_status = OrderStatus.CANCELLED
        order.cancelled_time = datetime.now(UTC)
        if order.payment and order.payment.payment_status == PaymentStatus.SUCCESS:
            order.payment.payment_status = PaymentStatus.REFUNDED
        if order.delivery_agent_id:
            agent = await session.get(DeliveryAgent, order.delivery_agent_id, with_for_update=True)
            agent.current_status = AgentStatus.AVAILABLE
    return await get_order(session, order_id)
