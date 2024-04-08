from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    """ """
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")

    return "OK"

@router.post("/plan")
def get_bottle_plan():
    """
    Logic to calculate the number of green potions that can be produced
    from the available green ml and update the inventory.
    """

    # Constants
    ml_per_potion = 50  # Assume each potion requires 50 ml to produce
    
    with db.engine.begin() as connection:
        # Fetch the current state of the inventory
        fetch_inventory_sql = "SELECT num_green_ml, num_green_potions FROM global_inventory WHERE id = 1;"
        inventory_result = connection.execute(sqlalchemy.text(fetch_inventory_sql))
        inventory = inventory_result.fetchone()
        green_ml_available, current_green_potions = inventory['num_green_ml'], inventory['num_green_potions']

        # Calculate the number of new potions that can be produced
        new_potions = green_ml_available // ml_per_potion

        # Update inventory with new potion count and remaining ml
        new_ml_amount = green_ml_available % ml_per_potion  # Remainder ml after potion production
        new_potion_count = current_green_potions + new_potions
        update_inventory_sql = """
            UPDATE global_inventory
            SET num_green_ml = :new_ml, num_green_potions = :new_potions
            WHERE id = 1;
        """
        connection.execute(sqlalchemy.text(update_inventory_sql), {"new_ml": new_ml_amount, "new_potions": new_potion_count})

    return [{"potion_type": [0, 100, 0], "quantity": new_potions}]


if __name__ == "__main__":
    print(get_bottle_plan())
