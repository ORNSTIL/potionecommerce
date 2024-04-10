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

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    total_ml_added = 0
    total_cost = 0

     with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar()

    total_ml_added = num_green_ml
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 100, 0, 0]:  # Assuming a way to identify green potion barrels
            total_ml_added += barrel.ml_per_barrel
            total_cost += barrel.price

   
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET num_green_ml = {num_green_ml} "))
        gold_amount = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar() - total_cost
        connection.execute(sqlalchemy.text(f"UPDATE global_inventory SET gold = {gold_amount} "))



@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    plan_to_buy = []
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("""
            SELECT num_green_potions FROM global_inventory WHERE id = 1
        """)).scalar()

        gold_amount = connection.execute(sqlalchemy.text("""
            SELECT gold FROM global_inventory WHERE id = 1
        """)).scalar()

        for barrel in wholesale_catalog:
            if barrel.potion_type == [0, 100, 0, 0]:  # Identifying green potion barrels by potion_type
                if num_green_potions < 10 and gold >= barrel.price:    
                    plan_to_buy.append({"sku": barrel.sku, "quantity": 1})
                    break 
                
                
    print(wholesale_catalog)
    return plan_to_buy



