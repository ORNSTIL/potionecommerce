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
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        gold_amount = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()

    total_ml_added = num_green_ml
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 100, 0, 0]:
            total_ml_added = barrel.ml_per_barrel * barrel.quantity
            total_cost = gold - (barrel.price * barrel.quantity)
            

    connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml"),
            {"green_ml": num_green_ml})
            
    connection.execute(sqlalchemy.text("UPDATE global_inventory SET gold = :gold"),
            {"gold": gold_amount})
    
    connection.commit()

    return "OK"



@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    plan_to_buy = []
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()

        gold_amount = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).scalar_one()

        for barrel in wholesale_catalog:
            if barrel.potion_type == [0, 100, 0, 0]:
                if num_green_potions < 10 and gold >= barrel.price: 
                    gold_amount = gold_amount - barrel.price
                    plan_to_buy.append({
                        "sku": barrel.sku, 
                        "quantity": 1,
                    })
                    break 
                
                
    print(wholesale_catalog)
    return plan_to_buy



