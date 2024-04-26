from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str
    ml_per_barrel: int
    potion_type: list[int]
    price: int
    quantity: int

def strconvert(intlist):
    return str(intlist)
    
def update_barrel_inventory(connection, barrel):
    barrel_inventory_sql = """
        UPDATE barrel_inventory SET potion_ml = potion_ml + :ml_increment
        WHERE barrel_type = :barrel_type
    """
    connection.execute(
        sqlalchemy.text(barrel_inventory_sql),
        {"ml_increment": barrel.ml_per_barrel * barrel.quantity, "barrel_type": str(barrel.potion_type)}
    )

def update_global_inventory(connection, barrel):
    global_inventory_sql = """
        UPDATE global_inventory SET gold = gold - :price_decrement
    """
    connection.execute(
        sqlalchemy.text(global_inventory_sql),
        {"price_decrement": barrel.price * barrel.quantity}
    )

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            update_barrel_inventory(connection, barrel)
            update_global_inventory(connection, barrel)
    return "OK"


def get_available_capacity(connection):
    result = connection.execute(sqlalchemy.text("""
        SELECT (gp.ml_capacity * 10000) - COALESCE(SUM(bi.potion_ml), 0) AS available_capacity
        FROM global_plan gp
        LEFT JOIN barrel_inventory bi ON 1=1
        GROUP BY gp.ml_capacity  -- Group by gp.ml_capacity
    """))
    available_capacity = result.fetchone()[0]
    return available_capacity


def fetch_global_inventory(connection):
    result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
    return result.fetchone()._asdict()

def fetch_and_sort_barrel_inventory(connection):
    result = connection.execute(sqlalchemy.text("""
        SELECT * FROM barrel_inventory ORDER BY potion_ml
    """))
    barrel_inventory = [row._asdict() for row in result.fetchall()]
    return barrel_inventory

def calculate_sort_key(barrel):
    return barrel.ml_per_barrel / barrel.price

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        
        global_inventory = fetch_global_inventory(connection)
        gold_total = global_inventory["gold"]
        available_ml = get_available_capacity(connection)
        
        
        wholesale_catalog_sorted = sorted(wholesale_catalog, key=calculate_sort_key, reverse=True)
        
        barrel_plan = []

        barrel_inventory = fetch_and_sort_barrel_inventory(connection)
        filtered_barrel_inventory = [potion_type for potion_type in barrel_inventory if potion_type["potion_ml"] <= global_inventory["ml_threshold"]]
        for potion_type in filtered_barrel_inventory:
            for barrel in wholesale_catalog_sorted:
                if barrel.ml_per_barrel > available_ml or barrel.price > gold_total:
                    continue
                if potion_type["barrel_type"] == strconvert(barrel.potion_type):
                    barrel_plan.append({"sku": barrel.sku, "quantity": 1})
                    
                    available_ml -= barrel.ml_per_barrel
                    gold_total -= barrel.price
                    break
        print(f"barrel purchase plan: {barrel_plan}, gold_total: {gold_total}")
        return barrel_plan
