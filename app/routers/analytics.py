from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


async def rows(db: AsyncSession, sql: str, params: dict | None = None):
    result = await db.execute(text(sql), params or {})
    return [dict(row) for row in result.mappings()]


@router.get("/restaurants")
async def restaurant_performance(db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT * FROM restaurant_performance_view ORDER BY revenue DESC")


@router.get("/restaurants/{restaurant_id}")
async def restaurant_monthly(restaurant_id: int, year: int, month: int, db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT * FROM get_restaurant_monthly_revenue(:id, :year, :month)", {"id": restaurant_id, "year": year, "month": month})


@router.get("/customers/{user_id}")
async def customer_summary(user_id: int, db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT *, get_customer_lifetime_value(:id) AS lifetime_value FROM customer_summary_view WHERE user_id=:id", {"id": user_id})


@router.get("/delivery-agents/{agent_id}")
async def agent_summary(agent_id: int, db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT * FROM get_agent_performance(:id)", {"id": agent_id})


@router.get("/sales/daily")
async def daily_sales(db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT * FROM daily_sales_view ORDER BY sales_date")


@router.get("/sales/monthly")
async def monthly_sales(db: AsyncSession = Depends(get_db)):
    return await rows(db, "SELECT date_trunc('month', order_time)::date AS month, count(*) AS order_count, sum(total_amount) AS revenue, avg(total_amount) AS average_order_value FROM orders WHERE order_status='DELIVERED' GROUP BY 1 ORDER BY 1")

