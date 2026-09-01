"""Generate a deterministic, analytics-friendly dataset (100 users, 20 restaurants, 1,200 orders)."""
import os
import random
from datetime import UTC, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from faker import Faker
import psycopg2
from psycopg2.extras import execute_values
from passlib.context import CryptContext

fake = Faker("en_IN")
Faker.seed(2026)
random.seed(2026)
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
D = Decimal
q = lambda value: D(value).quantize(D("0.01"), rounding=ROUND_HALF_UP)


def main() -> None:
    dsn = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://food_admin:food_password@localhost:5432/food_delivery").replace("postgresql+psycopg2://", "postgresql://")
    conn = psycopg2.connect(dsn)
    with conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM orders")
        if cur.fetchone()[0] >= 1000:
            print("Seed skipped: database already contains at least 1,000 orders")
            return
        cur.execute("TRUNCATE order_coupons,delivery_reviews,restaurant_reviews,payments,order_status_history,order_items,orders,coupons,delivery_agents,menu_items,menu_categories,restaurants,addresses,users RESTART IDENTITY CASCADE")
        password_hash = pwd.hash("DemoPassword123!")
        users = [(fake.name(), f"customer{i:03d}@example.com", f"+9190000{i:05d}", password_hash) for i in range(1,101)]
        execute_values(cur, "INSERT INTO users(full_name,email,phone,password_hash) VALUES %s", users)
        addresses = [(i, "Home", fake.street_address(), random.choice(["Bengaluru","Hyderabad","Pune","Chennai"]), random.choice(["Karnataka","Telangana","Maharashtra","Tamil Nadu"]), str(random.randint(100000,799999)), D("12.971600")+q(str(random.uniform(-.2,.2))), D("77.594600")+q(str(random.uniform(-.2,.2))), True) for i in range(1,101)]
        execute_values(cur, "INSERT INTO addresses(user_id,label,address_line,city,state,postal_code,latitude,longitude,is_default) VALUES %s", addresses)
        cuisines = ["North Indian","South Indian","Chinese","Italian","Biryani","Cafe","Mexican","Thai"]
        restaurants = [(f"{fake.first_name()} {random.choice(['Kitchen','Bistro','Dhaba','Cafe','Foods'])} {i}", random.choice(cuisines), f"+9188000{i:05d}", f"restaurant{i}@example.com", fake.street_address(), random.choice(["Bengaluru","Hyderabad","Pune","Chennai"]), "09:00", "23:00") for i in range(1,21)]
        execute_values(cur, "INSERT INTO restaurants(name,cuisine_type,phone,email,address,city,opening_time,closing_time) VALUES %s", restaurants)
        category_ids = {}
        for restaurant_id in range(1,21):
            for category in ("Starters","Main Course","Desserts","Beverages"):
                cur.execute("INSERT INTO menu_categories(restaurant_id,category_name) VALUES(%s,%s) RETURNING category_id", (restaurant_id,category))
                category_ids[(restaurant_id,category)] = cur.fetchone()[0]
        menu_by_restaurant = {}
        adjectives = ["Classic","Spicy","Royal","Smoky","Garden","Chef's","Crispy","Creamy"]
        nouns = ["Paneer","Chicken","Rice Bowl","Noodles","Pasta","Dosa","Kebab","Curry","Brownie","Lassi","Soup","Wrap"]
        for restaurant_id in range(1,21):
            menu_by_restaurant[restaurant_id] = []
            for item_no in range(12):
                category = ("Starters","Main Course","Desserts","Beverages")[item_no % 4]
                price = q(str(random.uniform(89,499)))
                cur.execute("INSERT INTO menu_items(restaurant_id,category_id,item_name,description,price,is_vegetarian,is_available) VALUES(%s,%s,%s,%s,%s,%s,true) RETURNING menu_item_id",
                            (restaurant_id,category_ids[(restaurant_id,category)],f"{random.choice(adjectives)} {random.choice(nouns)} {item_no+1}",fake.sentence(),price,random.random()<.55))
                menu_by_restaurant[restaurant_id].append((cur.fetchone()[0],price))
        agents = [(fake.name(),f"+9177000{i:05d}",f"KA01FD{i:04d}",random.choice(["BIKE","SCOOTER","BICYCLE"])) for i in range(1,26)]
        execute_values(cur,"INSERT INTO delivery_agents(full_name,phone,vehicle_number,vehicle_type) VALUES %s",agents)
        cur.execute("INSERT INTO coupons(coupon_code,discount_type,discount_value,minimum_order_value,maximum_discount,valid_from,valid_until,usage_limit,is_active) VALUES ('WELCOME20','PERCENTAGE',20,299,120,current_date-365,current_date+365,10000,true),('FLAT75','FIXED',75,499,75,current_date-365,current_date+365,5000,true),('EXPIRED50','PERCENTAGE',50,200,200,current_date-730,current_date-365,100,false)")
        histories = {"DELIVERED":["PLACED","ACCEPTED","PREPARING","READY_FOR_PICKUP","PICKED_UP","OUT_FOR_DELIVERY","DELIVERED"], "CANCELLED":["PLACED","ACCEPTED","CANCELLED"], "PLACED":["PLACED"], "PREPARING":["PLACED","ACCEPTED","PREPARING"]}
        delivered_orders = []
        start = datetime.now(UTC)-timedelta(days=240)
        for n in range(1200):
            user_id = random.randint(1,100); restaurant_id = random.randint(1,20)
            chosen = random.sample(menu_by_restaurant[restaurant_id],random.randint(1,4))
            lines = [(item_id,random.randint(1,3),price) for item_id,price in chosen]
            subtotal = q(sum((price*qty for _,qty,price in lines),D("0"))); tax=q(subtotal*D("0.05")); fee=D("40.00")
            coupon_id = random.choice([None,None,None,1,2])
            discount = min(q(subtotal*D("0.20")),D("120")) if coupon_id==1 and subtotal>=299 else (D("75") if coupon_id==2 and subtotal>=499 else D("0"))
            if discount == 0: coupon_id=None
            total=q(subtotal+tax+fee-discount); order_time=start+timedelta(minutes=random.randint(0,240*24*60))
            outcome=random.random(); final="DELIVERED" if outcome<.78 else ("CANCELLED" if outcome<.91 else ("PREPARING" if outcome<.96 else "PLACED"))
            agent_id=random.randint(1,25) if final=="DELIVERED" else None
            accepted=order_time+timedelta(minutes=random.randint(2,8)) if final in {"DELIVERED","CANCELLED","PREPARING"} else None
            prepared=accepted+timedelta(minutes=random.randint(12,35)) if final=="DELIVERED" else None
            picked=prepared+timedelta(minutes=random.randint(2,10)) if final=="DELIVERED" else None
            delivered=picked+timedelta(minutes=random.randint(12,40)) if final=="DELIVERED" else None
            cancelled=accepted+timedelta(minutes=random.randint(1,15)) if final=="CANCELLED" else None
            cur.execute("INSERT INTO orders(user_id,restaurant_id,delivery_address_id,delivery_agent_id,order_status,subtotal,delivery_fee,tax_amount,discount_amount,total_amount,order_time,accepted_time,prepared_time,picked_up_time,delivered_time,cancelled_time) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING order_id",
                        (user_id,restaurant_id,user_id,agent_id,final,subtotal,fee,tax,discount,total,order_time,accepted,prepared,picked,delivered,cancelled))
            order_id=cur.fetchone()[0]
            execute_values(cur,"INSERT INTO order_items(order_id,menu_item_id,quantity,unit_price,total_price) VALUES %s",[(order_id,i,qty,price,q(price*qty)) for i,qty,price in lines])
            method=random.choice(["UPI","CARD","CASH","WALLET"]); pstatus="FAILED" if random.random()<.04 else ("SUCCESS" if final in {"DELIVERED","CANCELLED"} else "PENDING")
            if final=="CANCELLED" and pstatus=="SUCCESS": pstatus="REFUNDED"
            cur.execute("INSERT INTO payments(order_id,payment_method,payment_status,transaction_reference,amount,paid_at) VALUES(%s,%s,%s,%s,%s,%s)",(order_id,method,pstatus,f"TXN{order_id:08d}" if pstatus!="PENDING" else None,total,order_time+timedelta(minutes=1) if pstatus=="SUCCESS" else None))
            if coupon_id:
                cur.execute("INSERT INTO order_coupons VALUES(%s,%s,%s)",(order_id,coupon_id,discount))
            cur.execute("DELETE FROM order_status_history WHERE order_id=%s",(order_id,))
            sequence=histories[final]
            for step,new_status in enumerate(sequence):
                changed=order_time+timedelta(minutes=step*8)
                cur.execute("INSERT INTO order_status_history(order_id,previous_status,new_status,changed_at) VALUES(%s,%s,%s,%s)",(order_id,sequence[step-1] if step else None,new_status,changed))
            if final=="DELIVERED": delivered_orders.append((order_id,user_id,restaurant_id,agent_id,delivered))
        cur.execute("UPDATE coupons c SET current_usage=(SELECT count(*) FROM order_coupons oc WHERE oc.coupon_id=c.coupon_id)")
        for order_id,user_id,restaurant_id,agent_id,delivered in random.sample(delivered_orders,min(500,len(delivered_orders))):
            rating=random.choices([1,2,3,4,5],weights=[2,4,12,35,47])[0]
            cur.execute("INSERT INTO restaurant_reviews(user_id,restaurant_id,order_id,rating,review_text,created_at) VALUES(%s,%s,%s,%s,%s,%s)",(user_id,restaurant_id,order_id,rating,fake.sentence(),delivered+timedelta(hours=2)))
            if random.random()<.8:
                arating=random.choices([1,2,3,4,5],weights=[1,3,10,37,49])[0]
                cur.execute("INSERT INTO delivery_reviews(user_id,delivery_agent_id,order_id,rating,review_text,created_at) VALUES(%s,%s,%s,%s,%s,%s)",(user_id,agent_id,order_id,arating,fake.sentence(),delivered+timedelta(hours=3)))
    conn.close()
    print("Seeded 100 customers, 20 restaurants, 240 menu items, 25 agents, and 1,200 orders")


if __name__ == "__main__":
    main()
