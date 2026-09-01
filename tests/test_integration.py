import os
from uuid import uuid4
import httpx
import psycopg2
import pytest
import pytest_asyncio

TEST_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = [pytest.mark.integration, pytest.mark.skipif(not TEST_URL, reason="TEST_DATABASE_URL is not configured")]


def sync_url() -> str:
    return TEST_URL.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg2://", "postgresql://")


if TEST_URL:
    os.environ["DATABASE_URL"] = TEST_URL if "+asyncpg" in TEST_URL else TEST_URL.replace("postgresql://", "postgresql+asyncpg://")
    os.environ["SYNC_DATABASE_URL"] = TEST_URL.replace("postgresql+asyncpg://", "postgresql+psycopg2://")


@pytest_asyncio.fixture
async def context():
    from app.main import app
    tables = "order_coupons,delivery_reviews,restaurant_reviews,payments,order_status_history,order_items,orders,coupons,delivery_agents,menu_items,menu_categories,restaurants,addresses,users"
    with psycopg2.connect(sync_url()) as conn, conn.cursor() as cur:
        cur.execute(f"TRUNCATE {tables} RESTART IDENTITY CASCADE")
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=True)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        suffix = uuid4().hex[:8]
        response = await client.post("/users", json={"full_name":"Test Customer","email":f"user-{suffix}@example.com","phone":f"9000{suffix}","password":"SafePassword123"})
        assert response.status_code == 201; user = response.json()
        response = await client.post(f"/users/{user['user_id']}/addresses", json={"label":"Home","address_line":"1 Test Road","city":"Bengaluru","state":"Karnataka","postal_code":"560001","is_default":True})
        assert response.status_code == 201; address = response.json()
        response = await client.post("/restaurants", json={"name":"Test Kitchen","cuisine_type":"Indian","phone":f"8000{suffix}","email":f"restaurant-{suffix}@example.com","address":"2 Food Street","city":"Bengaluru","opening_time":"09:00:00","closing_time":"23:00:00"})
        assert response.status_code == 201; restaurant = response.json()
        with psycopg2.connect(sync_url()) as conn, conn.cursor() as cur:
            cur.execute("INSERT INTO menu_categories(restaurant_id,category_name) VALUES(%s,'Main Course') RETURNING category_id",(restaurant["restaurant_id"],)); category_id=cur.fetchone()[0]
            cur.execute("INSERT INTO delivery_agents(full_name,phone,vehicle_number,vehicle_type) VALUES('Test Agent',%s,%s,'BIKE') RETURNING agent_id",(f"7000{suffix}",f"KA01{suffix}")); agent_id=cur.fetchone()[0]
            cur.execute("INSERT INTO coupons(coupon_code,discount_type,discount_value,minimum_order_value,maximum_discount,valid_from,valid_until,usage_limit,is_active) VALUES('SAVE20','PERCENTAGE',20,100,50,current_date-1,current_date+1,10,true)")
        response = await client.post(f"/restaurants/{restaurant['restaurant_id']}/menu-items", json={"category_id":category_id,"item_name":"Paneer Bowl","price":"200.00","is_vegetarian":True,"is_available":True})
        assert response.status_code == 201; item=response.json()
        yield {"client":client,"user":user,"address":address,"restaurant":restaurant,"item":item,"agent_id":agent_id}


def order_payload(c, **extra):
    payload={"user_id":c["user"]["user_id"],"restaurant_id":c["restaurant"]["restaurant_id"],"delivery_address_id":c["address"]["address_id"],"items":[{"menu_item_id":c["item"]["menu_item_id"],"quantity":2}],"payment_method":"UPI"}
    payload.update(extra); return payload


@pytest.mark.asyncio
async def test_user_restaurant_menu_order_and_payment_creation(context):
    response=await context["client"].post("/orders",json=order_payload(context))
    assert response.status_code==201
    order=response.json()
    assert order["subtotal"]=="400.00" and order["total_amount"]=="460.00"
    payment=await context["client"].get(f"/orders/{order['order_id']}/payment")
    assert payment.status_code==200 and payment.json()["payment_status"]=="PENDING"


@pytest.mark.asyncio
async def test_invalid_or_unavailable_item_rolls_back_order(context):
    bad=order_payload(context); bad["items"].append({"menu_item_id":999999,"quantity":1})
    response=await context["client"].post("/orders",json=bad)
    assert response.status_code==422
    with psycopg2.connect(sync_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM orders"); assert cur.fetchone()[0]==0
    await context["client"].patch(f"/menu-items/{context['item']['menu_item_id']}",json={"is_available":False})
    assert (await context["client"].post("/orders",json=order_payload(context))).status_code==422


@pytest.mark.asyncio
async def test_coupon_validation_and_server_side_totals(context):
    order=(await context["client"].post("/orders",json=order_payload(context,coupon_code="SAVE20"))).json()
    assert order["discount_amount"]=="50.00" and order["total_amount"]=="410.00"
    invalid=await context["client"].post("/orders",json=order_payload(context,coupon_code="EXPIRED"))
    assert invalid.status_code==422


@pytest.mark.asyncio
async def test_payment_cancellation_and_trigger_history(context):
    order=(await context["client"].post("/orders",json=order_payload(context))).json(); oid=order["order_id"]
    paid=await context["client"].post(f"/orders/{oid}/payment",json={"payment_method":"CARD","payment_status":"SUCCESS","transaction_reference":f"T-{oid}"})
    assert paid.status_code==200
    cancelled=await context["client"].post(f"/orders/{oid}/cancel")
    assert cancelled.status_code==200 and cancelled.json()["payment"]["payment_status"]=="REFUNDED"
    assert (await context["client"].patch(f"/orders/{oid}/status",json={"status":"ACCEPTED"})).status_code==409
    with psycopg2.connect(sync_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT new_status::text FROM order_status_history WHERE order_id=%s ORDER BY changed_at",(oid,))
        assert [row[0] for row in cur.fetchall()]==["PLACED","CANCELLED"]


@pytest.mark.asyncio
async def test_agent_assignment_completion_reviews_and_rating_triggers(context):
    client=context["client"]; oid=(await client.post("/orders",json=order_payload(context))).json()["order_id"]
    assert (await client.post(f"/orders/{oid}/restaurant-review",json={"rating":5})).status_code==409
    for state in ("ACCEPTED","PREPARING","READY_FOR_PICKUP"):
        assert (await client.patch(f"/orders/{oid}/status",json={"status":state})).status_code==200
    assert (await client.patch(f"/orders/{oid}/status",json={"status":"PICKED_UP","delivery_agent_id":context["agent_id"]})).status_code==200
    for state in ("OUT_FOR_DELIVERY","DELIVERED"):
        assert (await client.patch(f"/orders/{oid}/status",json={"status":state})).status_code==200
    assert (await client.post(f"/orders/{oid}/restaurant-review",json={"rating":5,"review_text":"Excellent"})).status_code==201
    assert (await client.post(f"/orders/{oid}/delivery-review",json={"rating":4,"review_text":"Quick"})).status_code==201
    assert (await client.post(f"/orders/{oid}/restaurant-review",json={"rating":3})).status_code==409
    with psycopg2.connect(sync_url()) as conn, conn.cursor() as cur:
        cur.execute("SELECT r.rating,a.average_rating,a.current_status::text FROM restaurants r CROSS JOIN delivery_agents a WHERE r.restaurant_id=%s AND a.agent_id=%s",(context["restaurant"]["restaurant_id"],context["agent_id"]))
        assert cur.fetchone()==(5,4,"AVAILABLE")


@pytest.mark.asyncio
async def test_agent_cannot_handle_two_active_orders(context):
    client=context["client"]
    async def ready_order():
        oid=(await client.post("/orders",json=order_payload(context))).json()["order_id"]
        for state in ("ACCEPTED","PREPARING","READY_FOR_PICKUP"):
            await client.patch(f"/orders/{oid}/status",json={"status":state})
        return oid
    first,second=await ready_order(),await ready_order()
    assert (await client.patch(f"/orders/{first}/status",json={"status":"PICKED_UP","delivery_agent_id":context["agent_id"]})).status_code==200
    assert (await client.patch(f"/orders/{second}/status",json={"status":"PICKED_UP","delivery_agent_id":context["agent_id"]})).status_code==409
