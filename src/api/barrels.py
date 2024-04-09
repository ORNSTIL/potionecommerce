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
        # Assuming 'gold' and 'num_green_ml' are available in 'global_inventory'
        inventory_info = connection.execute(sqlalchemy.text("""
            SELECT gold, num_green_ml FROM global_inventory WHERE id = 1
        """)).fetchone()
        gold, num_green_ml = inventory_info

        # Decision to buy based on gold and whether we need more ml
        # This example assumes each green barrel costs 100 gold and adds 1000 ml.
        # Adjust numbers based on your game's logic.
        needed_ml = 1000 - num_green_ml  # Assuming you want to keep at least 1000 ml in stock.
        barrels_needed = needed_ml // 1000  # Assuming each barrel adds 1000 ml.
        barrel_cost = 100  # Assuming each barrel costs 100 gold.

        for barrel in wholesale_catalog:
            if barrel.sku == "SMALL_GREEN_BARREL" and gold >= barrel_cost * barrels_needed:
                plan_to_buy.append({"sku": barrel.sku, "quantity": barrels_needed})
                break  # Assuming you stop after finding the barrels you can afford.

    return plan_to_buy


