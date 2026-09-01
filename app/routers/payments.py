from datetime import UTC, datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Payment, PaymentStatus
from app.schemas.api import PaymentRead, PaymentUpdate

router = APIRouter(prefix="/orders/{order_id}/payment", tags=["payments"])


@router.get("", response_model=PaymentRead)
async def get_payment(order_id: int, db: AsyncSession = Depends(get_db)):
    payment = (await db.execute(select(Payment).where(Payment.order_id == order_id))).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment


@router.post("", response_model=PaymentRead)
async def record_payment(order_id: int, payload: PaymentUpdate, db: AsyncSession = Depends(get_db)):
    payment = (await db.execute(select(Payment).where(Payment.order_id == order_id).with_for_update())).scalar_one_or_none()
    if not payment:
        raise HTTPException(404, "Payment not found")
    if payment.payment_status in {PaymentStatus.SUCCESS, PaymentStatus.REFUNDED}:
        raise HTTPException(409, "Finalized payments cannot be overwritten")
    payment.payment_method = payload.payment_method
    payment.payment_status = payload.payment_status
    payment.transaction_reference = payload.transaction_reference
    if payload.payment_status == PaymentStatus.SUCCESS:
        payment.paid_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(payment)
    return payment

