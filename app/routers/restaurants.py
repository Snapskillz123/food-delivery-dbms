from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.entities import MenuCategory, MenuItem, Restaurant
from app.schemas.api import MenuItemCreate, MenuItemRead, MenuItemUpdate, RestaurantCreate, RestaurantRead

router = APIRouter(tags=["restaurants"])


@router.post("/restaurants", response_model=RestaurantRead, status_code=status.HTTP_201_CREATED)
async def create_restaurant(payload: RestaurantCreate, db: AsyncSession = Depends(get_db)):
    restaurant = Restaurant(**payload.model_dump())
    db.add(restaurant)
    await db.commit()
    await db.refresh(restaurant)
    return restaurant


@router.get("/restaurants", response_model=list[RestaurantRead])
async def list_restaurants(city: str | None = None, active_only: bool = True, db: AsyncSession = Depends(get_db)):
    stmt = select(Restaurant)
    if city:
        stmt = stmt.where(Restaurant.city.ilike(city))
    if active_only:
        stmt = stmt.where(Restaurant.is_active.is_(True))
    return (await db.execute(stmt.order_by(Restaurant.rating.desc()))).scalars().all()


@router.get("/restaurants/{restaurant_id}", response_model=RestaurantRead)
async def read_restaurant(restaurant_id: int, db: AsyncSession = Depends(get_db)):
    restaurant = await db.get(Restaurant, restaurant_id)
    if not restaurant:
        raise HTTPException(404, "Restaurant not found")
    return restaurant


@router.get("/restaurants/{restaurant_id}/menu", response_model=list[MenuItemRead])
async def restaurant_menu(restaurant_id: int, available_only: bool = Query(True), db: AsyncSession = Depends(get_db)):
    stmt = select(MenuItem).where(MenuItem.restaurant_id == restaurant_id)
    if available_only:
        stmt = stmt.where(MenuItem.is_available.is_(True))
    return (await db.execute(stmt.order_by(MenuItem.category_id, MenuItem.item_name))).scalars().all()


@router.post("/restaurants/{restaurant_id}/menu-items", response_model=MenuItemRead, status_code=201)
async def create_menu_item(restaurant_id: int, payload: MenuItemCreate, db: AsyncSession = Depends(get_db)):
    category = await db.get(MenuCategory, payload.category_id)
    if not category or category.restaurant_id != restaurant_id:
        raise HTTPException(422, "Category must belong to the restaurant")
    item = MenuItem(restaurant_id=restaurant_id, **payload.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.patch("/menu-items/{menu_item_id}", response_model=MenuItemRead)
async def update_menu_item(menu_item_id: int, payload: MenuItemUpdate, db: AsyncSession = Depends(get_db)):
    item = await db.get(MenuItem, menu_item_id)
    if not item:
        raise HTTPException(404, "Menu item not found")
    changes = payload.model_dump(exclude_unset=True)
    if "category_id" in changes:
        category = await db.get(MenuCategory, changes["category_id"])
        if not category or category.restaurant_id != item.restaurant_id:
            raise HTTPException(422, "Category must belong to the restaurant")
    for key, value in changes.items():
        setattr(item, key, value)
    await db.commit()
    await db.refresh(item)
    return item

