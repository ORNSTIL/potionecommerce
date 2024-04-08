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
    for potion_inventory in potions_delivered:
        if potion_inventory.potion_type == [0, 100, 0]:  # Green potion logic
            # Update database with delivered potion quantities
            sql_to_execute = """
            UPDATE global_inventory
            SET num_green_ml = num_green_ml + :delivered_ml
            WHERE id = 1;
            """
            ml_delivered = potion_inventory.quantity * 50  # Assuming 50 ml per potion quantity for simplicity
            with db.engine.begin() as connection:
                connection.execute(sqlalchemy.text(sql_to_execute), {"delivered_ml": ml_delivered})
                
    return {"message": f"Delivered potions for order {order_id}"}


@router.post("/plan")
def get_bottle_plan():
    """
    Calculate the potential number of green potions that can be produced
    from the available green ml without updating the inventory.
    """

    ml_per_potion = 50 
    
    with db.engine.begin() as connection:
        # Fetch the current state of the inventory
        fetch_inventory_sql = "SELECT num_green_ml FROM global_inventory WHERE id = 1;"
        inventory_result = connection.execute(sqlalchemy.text(fetch_inventory_sql))
        green_ml_available = inventory_result.scalar()

        # Calculate the number of new potions that could be produced
        potential_new_potions = green_ml_available // ml_per_potion

    # Return a plan indicating the number of potions that could potentially be produced
    return [{"potion_type": [0, 100, 0], "potential_quantity": potential_new_potions}]



if __name__ == "__main__":
    print(get_bottle_plan())
