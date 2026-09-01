import os
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import create_engine, text

st.set_page_config(page_title="Food Delivery Analytics", page_icon="🍽️", layout="wide")
dsn = os.getenv("SYNC_DATABASE_URL", "postgresql+psycopg2://food_admin:food_password@localhost:5432/food_delivery")
engine = create_engine(dsn, pool_pre_ping=True)


@st.cache_data(ttl=60)
def query(sql: str) -> pd.DataFrame:
    with engine.connect() as connection:
        return pd.read_sql(text(sql), connection)


st.title("Food Delivery Operations & Analytics")
page = st.sidebar.radio("Dashboard", ["Overview", "Sales Analytics", "Restaurant Analytics", "Customer Analytics", "Delivery Analytics"])

if page == "Overview":
    kpi = query("""SELECT COALESCE(sum(total_amount) FILTER(WHERE order_status='DELIVERED'),0) revenue,
    count(*) total_orders,count(DISTINCT user_id) customers,count(DISTINCT restaurant_id) restaurants,
    COALESCE(avg(total_amount) FILTER(WHERE order_status='DELIVERED'),0) average_order_value,
    100.0*count(*) FILTER(WHERE order_status='CANCELLED')/NULLIF(count(*),0) cancellation_rate FROM orders""").iloc[0]
    columns = st.columns(6)
    labels = [("Revenue",f"₹{kpi.revenue:,.0f}"),("Orders",f"{kpi.total_orders:,}"),("Customers",f"{kpi.customers:,}"),
              ("Restaurants",f"{kpi.restaurants:,}"),("Avg. order",f"₹{kpi.average_order_value:,.0f}"),("Cancellation",f"{kpi.cancellation_rate:.1f}%")]
    for column,(label,value) in zip(columns,labels): column.metric(label,value)
    daily=query("SELECT * FROM daily_sales_view ORDER BY sales_date")
    st.plotly_chart(px.area(daily,x="sales_date",y="revenue",title="Daily delivered revenue"),use_container_width=True)

elif page == "Sales Analytics":
    daily=query("SELECT * FROM daily_sales_view ORDER BY sales_date")
    monthly=query("SELECT date_trunc('month',order_time)::date AS revenue_month,sum(total_amount) revenue,count(*) orders FROM orders WHERE order_status='DELIVERED' GROUP BY 1 ORDER BY 1")
    c1,c2=st.columns(2)
    c1.plotly_chart(px.line(daily,x="sales_date",y="revenue",title="Daily revenue"),use_container_width=True)
    c2.plotly_chart(px.bar(monthly,x="revenue_month",y="revenue",title="Monthly revenue"),use_container_width=True)
    weekday=query("SELECT extract(isodow FROM order_time) n,to_char(order_time,'FMDay') weekday,count(*) orders FROM orders GROUP BY 1,2 ORDER BY 1")
    hourly=query("SELECT extract(hour FROM order_time)::int hour,count(*) orders FROM orders GROUP BY 1 ORDER BY 1")
    c3,c4=st.columns(2)
    c3.plotly_chart(px.bar(weekday,x="weekday",y="orders",title="Order volume by weekday"),use_container_width=True)
    c4.plotly_chart(px.line(hourly,x="hour",y="orders",markers=True,title="Order volume by hour"),use_container_width=True)

elif page == "Restaurant Analytics":
    data=query("SELECT *,round(100.0*cancelled_orders/NULLIF(total_orders,0),2) cancellation_rate FROM restaurant_performance_view ORDER BY revenue DESC")
    c1,c2=st.columns(2)
    c1.plotly_chart(px.bar(data.head(10),x="revenue",y="restaurant",orientation="h",title="Top restaurants by revenue"),use_container_width=True)
    c2.plotly_chart(px.bar(data.sort_values("total_orders",ascending=False).head(10),x="total_orders",y="restaurant",orientation="h",title="Top restaurants by orders"),use_container_width=True)
    st.plotly_chart(px.scatter(data,x="average_rating",y="revenue",size="total_orders",color="cancellation_rate",hover_name="restaurant",title="Rating, revenue, and cancellations"),use_container_width=True)
    st.dataframe(data,use_container_width=True,hide_index=True)

elif page == "Customer Analytics":
    customers=query("SELECT * FROM customer_summary_view ORDER BY total_spent DESC")
    frequency=query("SELECT total_orders,count(*) customers FROM customer_summary_view GROUP BY total_orders ORDER BY total_orders")
    repeat=query("SELECT CASE WHEN total_orders>1 THEN 'Repeat' ELSE 'One-time' END customer_type,count(*) customers FROM customer_summary_view WHERE total_orders>0 GROUP BY 1")
    firsts=query("SELECT date_trunc('month',first_order)::date AS acquisition_month,count(*) new_customers FROM (SELECT user_id,min(order_time) first_order FROM orders GROUP BY user_id)x GROUP BY 1 ORDER BY 1")
    c1,c2=st.columns(2)
    c1.plotly_chart(px.bar(customers.head(15),x="total_spent",y="customer",orientation="h",title="Top customers by spend"),use_container_width=True)
    c2.plotly_chart(px.bar(frequency,x="total_orders",y="customers",title="Customer order frequency"),use_container_width=True)
    c3,c4=st.columns(2)
    c3.plotly_chart(px.pie(repeat,names="customer_type",values="customers",title="Repeat customers"),use_container_width=True)
    c4.plotly_chart(px.bar(firsts,x="acquisition_month",y="new_customers",title="New customers by first-order month"),use_container_width=True)

else:
    agents=query("SELECT * FROM delivery_agent_performance_view ORDER BY completed_deliveries DESC")
    delays=query("SELECT extract(hour FROM order_time)::int hour,count(*) FILTER(WHERE delivered_time-order_time>interval '45 minutes') late,count(*) total FROM orders WHERE order_status='DELIVERED' GROUP BY 1 ORDER BY 1")
    avg_minutes=query("SELECT extract(epoch FROM avg(delivered_time-picked_up_time))/60 minutes FROM orders WHERE order_status='DELIVERED'").iloc[0,0]
    st.metric("Average delivery time",f"{avg_minutes:.1f} min")
    c1,c2=st.columns(2)
    c1.plotly_chart(px.bar(agents.head(15),x="completed_deliveries",y="agent",color="average_rating",orientation="h",title="Agent performance"),use_container_width=True)
    c2.plotly_chart(px.scatter(agents,x="completed_deliveries",y="average_rating",hover_name="agent",title="Agent ratings vs deliveries"),use_container_width=True)
    st.plotly_chart(px.bar(delays,x="hour",y=["late","total"],barmode="group",title="Late deliveries by ordering hour"),use_container_width=True)
    st.dataframe(agents,use_container_width=True,hide_index=True)
