from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import Address, Order, User
from app.schemas.api import AddressCreate, AddressRead, OrderRead, UserCreate, UserRead
from app.utils.security import hash_password

router = APIRouter(prefix="/users", tags=["customers"])


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, db: AsyncSession = Depends(get_db)):
    user = User(full_name=payload.full_name, email=payload.email.lower(), phone=payload.phone,
                password_hash=hash_password(payload.password))
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserRead)
async def read_user(user_id: int, db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    return user


@router.get("/{user_id}/orders", response_model=list[OrderRead])
async def user_orders(user_id: int, db: AsyncSession = Depends(get_db)):
    return (await db.execute(select(Order).where(Order.user_id == user_id).order_by(Order.order_time.desc()))).scalars().all()


@router.post("/{user_id}/addresses", response_model=AddressRead, status_code=201)
async def create_address(user_id: int, payload: AddressCreate, db: AsyncSession = Depends(get_db)):
    if not await db.get(User, user_id):
        raise HTTPException(404, "User not found")
    if payload.is_default:
        await db.execute(update(Address).where(Address.user_id == user_id).values(is_default=False))
    address = Address(user_id=user_id, **payload.model_dump())
    db.add(address)
    await db.commit()
    await db.refresh(address)
    return address

