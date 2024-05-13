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
    """
    Retrieve the total inventory of potions, the total milliliters of potion ingredients in barrels,
    and the total gold, each calculated from ledger tables.
    """
    with db.engine.begin() as connection:
        # Calculate total potions from the potion ledger
        potion_inventory_query = sqlalchemy.text("""
            SELECT COALESCE(SUM(change), 0) AS total_potions
            FROM potion_ledger
        """)
        potion_inventory = connection.execute(potion_inventory_query).scalar()

        # Calculate total milliliters from the ml ledger
        ml_inventory_query = sqlalchemy.text("""
            SELECT COALESCE(SUM(change), 0) AS total_ml
            FROM ml_ledger
        """)
        barrel_inventory = connection.execute(ml_inventory_query).scalar()

        # Calculate total gold from the gold ledger
        gold_inventory_query = sqlalchemy.text("""
            SELECT COALESCE(SUM(change), 0) AS total_gold
            FROM gold_ledger
        """)
        gold_total = connection.execute(gold_inventory_query).scalar()

        # Output the totals for verification in development environments
        print(f"number_of_potions: {potion_inventory}, number_of_ml: {barrel_inventory}, gold_count: {gold_total}")

        return [
            {
                "number_of_potions": potion_inventory,
                "ml_in_barrels": barrel_inventory,
                "gold": gold_total
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
        "ml_capacity": 1
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
