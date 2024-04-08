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
                connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = num_green_potions + :qty WHERE id = 1"),
                                   qty=potion.quantity)
    return "OK"

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory WHERE id = 1")).fetchone()['num_green_ml']
        # Assuming each potion requires 100 ml
        if num_green_ml >= 100:
            num_potions = num_green_ml // 100
            connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = num_green_potions + :qty, num_green_ml = num_green_ml - (:qty * 100) WHERE id = 1"),
                               qty=num_potions)
            return [{
                "potion_type": [0, 100, 0, 0],  # 100% green potion
                "quantity": num_potions,
            }]
    return []

if __name__ == "__main__":
    print(get_bottle_plan())
