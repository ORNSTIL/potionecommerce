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
    total_ml_added = 0
    total_cost = 0
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 100, 0, 0]:  # Assuming a way to identify green potion barrels
            total_ml_added += barrel.ml_per_barrel * barrel.quantity
            total_cost += barrel.price * barrel.quantity  # Assuming price is per barrel

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("""
            UPDATE global_inventory SET num_green_ml = num_green_ml + :ml, gold = gold - :cost WHERE id = 1
        """), ml=total_ml_added, cost=total_cost)
    return "OK"


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    plan_to_buy = []
    with db.engine.begin() as connection:
        num_green_potions = connection.execute(sqlalchemy.text("""
            SELECT num_green_potions FROM global_inventory WHERE id = 1
        """)).scalar()

        if num_green_potions < 10:
            for barrel in wholesale_catalog:
                if barrel.potion_type == [0, 100, 0, 0]:  # Identifying green potion barrels by potion_type
                    plan_to_buy.append({"sku": barrel.sku, "quantity": 1})
                    break 

    return plan_to_buy



