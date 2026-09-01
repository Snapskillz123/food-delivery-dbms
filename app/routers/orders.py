from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import DeliveryReview, Order, OrderStatus, PaymentStatus, RestaurantReview
from app.schemas.api import OrderCreate, OrderRead, ReviewCreate, ReviewRead, StatusUpdate
from app.services.order_service import cancel_order, get_order, place_order, update_status

router = APIRouter(prefix="/orders", tags=["orders"])


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(payload: OrderCreate, db: AsyncSession = Depends(get_db)):
    return await place_order(db, payload)


@router.get("/{order_id}", response_model=OrderRead)
async def read_order(order_id: int, db: AsyncSession = Depends(get_db)):
    return await get_order(db, order_id)


@router.get("", response_model=list[OrderRead])
async def list_orders(
    order_status: OrderStatus | None = Query(None, alias="status"), restaurant_id: int | None = None,
    user_id: int | None = None, start_date: datetime | None = None, end_date: datetime | None = None,
    limit: int = Query(100, ge=1, le=500), db: AsyncSession = Depends(get_db),
):
    stmt = select(Order)
    for condition in [Order.order_status == order_status if order_status else None,
                      Order.restaurant_id == restaurant_id if restaurant_id else None,
                      Order.user_id == user_id if user_id else None,
                      Order.order_time >= start_date if start_date else None,
                      Order.order_time <= end_date if end_date else None]:
        if condition is not None:
            stmt = stmt.where(condition)
    return (await db.execute(stmt.order_by(Order.order_time.desc()).limit(limit))).scalars().all()


@router.patch("/{order_id}/status", response_model=OrderRead)
async def change_status(order_id: int, payload: StatusUpdate, db: AsyncSession = Depends(get_db)):
    return await update_status(db, order_id, payload.status, payload.delivery_agent_id)


@router.post("/{order_id}/cancel", response_model=OrderRead)
async def cancel(order_id: int, db: AsyncSession = Depends(get_db)):
    return await cancel_order(db, order_id)


async def _reviewable(db: AsyncSession, order_id: int) -> Order:
    order = await get_order(db, order_id)
    if order.order_status != OrderStatus.DELIVERED:
        raise HTTPException(409, "Only delivered orders can be reviewed")
    return order


@router.post("/{order_id}/restaurant-review", response_model=ReviewRead, status_code=201)
async def restaurant_review(order_id: int, payload: ReviewCreate, db: AsyncSession = Depends(get_db)):
    order = await _reviewable(db, order_id)
    review = RestaurantReview(user_id=order.user_id, restaurant_id=order.restaurant_id, order_id=order_id, **payload.model_dump())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review


@router.post("/{order_id}/delivery-review", response_model=ReviewRead, status_code=201)
async def delivery_review(order_id: int, payload: ReviewCreate, db: AsyncSession = Depends(get_db)):
    order = await _reviewable(db, order_id)
    if not order.delivery_agent_id:
        raise HTTPException(422, "Order has no delivery agent")
    review = DeliveryReview(user_id=order.user_id, delivery_agent_id=order.delivery_agent_id, order_id=order_id, **payload.model_dump())
    db.add(review)
    await db.commit()
    await db.refresh(review)
    return review

