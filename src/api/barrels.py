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

def potion_type_tostr(potion_type):
    return "{" + ",".join(map(str, potion_type)) + "}"
    
def update_barrel_inventory(connection, barrel):
    sql = f"""
        UPDATE barrel_inventory SET potion_ml = potion_ml + {barrel.ml_per_barrel * barrel.quantity}
        WHERE barrel_type = '{potion_type_tostr(barrel.potion_type)}'
    """
    connection.execute(sqlalchemy.text(sql))

def update_global_inventory(connection, barrel):
    sql = f"""
        UPDATE global_inventory SET gold = gold - {barrel.price * barrel.quantity}
    """
    connection.execute(sqlalchemy.text(sql))

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    print(f"barrels delivered: {barrels_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        for barrel in barrels_delivered:
            update_barrel_inventory(connection, barrel)
            update_global_inventory(connection, barrel)
    return "OK"


def get_available_capacity(connection):
    result = connection.execute(sqlalchemy.text("SELECT ml_capacity FROM global_plan"))
    max_ml = result.fetchone()[0] * 10000
    result = connection.execute(sqlalchemy.text("SELECT SUM(potion_ml) FROM barrel_inventory"))
    ml = result.fetchone()[0]
    return max_ml - ml

def fetch_global_inventory(connection):
    result = connection.execute(sqlalchemy.text("SELECT * FROM global_inventory"))
    return result.fetchone()._asdict()

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    print(wholesale_catalog)
    with db.engine.begin() as connection:
        available_ml = get_available_capacity(connection)
        global_inventory = fetch_global_inventory(connection)
        running_total = global_inventory["gold"]
        wholesale_catalog.sort(key=lambda x: x.ml_per_barrel / x.price, reverse=True)
        barrel_plan = []

        rows = connection.execute(sqlalchemy.text("SELECT * FROM barrel_inventory")).fetchall()
        barrel_inventory = [row._asdict() for row in rows]
        barrel_inventory.sort(key=lambda x: x["potion_ml"])

        for potion_type in barrel_inventory:
            if potion_type["potion_ml"] > global_inventory["ml_threshold"]:
                continue
            for barrel in wholesale_catalog:
                if barrel.ml_per_barrel > available_ml or barrel.price > running_total:
                    continue
                if potion_type["barrel_type"] == barrel.potion_type:
                    barrel_plan.append({"sku": barrel.sku, "quantity": 1})
                    running_total -= barrel.price
                    available_ml -= barrel.ml_per_barrel
                    break

        print(f"barrel purchase plan: {barrel_plan}, running_total: {running_total}")
        return barrel_plan
