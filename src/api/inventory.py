from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import math
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/inventory",
    tags=["inventory"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.get("/audit")
def get_inventory():
    """ """
    with db.engine.begin() as connection:
        total_inventory = connection.execute(sqlalchemy.text("SELECT gold FROM global_inventory")).fetchone().asdict()
        potion_inventory = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_catalog")).fetchone()[0]
        barrel_inventory = connection.execute(sqlalchemy.text("SELECT SUM(potion_ml) FROM barrel_inventory")).fetchone()[0]

        print(f"number_of_potions: {potion_inventory} number_of_ml: {barrel_inventory} gold_count: {total_inventory['gold']}")

        return [
                {
                    "number_of_potions": number_of_potions,
                    "ml_in_barrels": number_of_ml,
                    "gold": total_inventory["gold"]
                }
            ]

# Gets called once a day
@router.post("/plan")
def get_capacity_plan():
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return {
        "potion_capacity": 0,
        "ml_capacity": 0
        }

class CapacityPurchase(BaseModel):
    potion_capacity: int
    ml_capacity: int

# Gets called once a day
@router.post("/deliver/{order_id}")
def deliver_capacity_plan(capacity_purchase : CapacityPurchase, order_id: int):
    """ 
    Start with 1 capacity for 50 potions and 1 capacity for 10000 ml of potion. Each additional 
    capacity unit costs 1000 gold.
    """

    return "OK"
