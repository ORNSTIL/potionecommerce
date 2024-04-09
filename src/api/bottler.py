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
    for potion in potions_delivered:
        if potion.potion_type == [0, 100, 0, 0]:  # green potions
            with db.engine.begin() as connection:
                # Correctly passing 'qty' as part of a dictionary
                connection.execute(sqlalchemy.text("""
                    UPDATE global_inventory 
                    SET num_green_potions = num_green_potions + :qty 
                    WHERE id = 1
                """), {'qty': potion.quantity})  # Note the change here
    return "OK"


@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory WHERE id = 1")).scalar()
        potions_possible = num_green_ml // 100 + 1 # Each potion requires 100 ml
        # No database modifications here, just planning
        return [{
            "potion_type": [0, 100, 0, 0],
            "quantity": potions_possible,
        }]


if __name__ == "__main__":
    print(get_bottle_plan())
