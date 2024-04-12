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
    print(f"potions delievered: {potions_delivered} order_id: {order_id}")
    
    with db.engine.begin() as connection:
        num_green = connection.execute(sqlalchemy.text("SELECT num_green_potions FROM global_inventory")).scalar_one()
        green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        
        for potion in potions_delivered:
            if potion.potion_type == [0, 100, 0, 0] or barrel.potion_type == [0, 100, 0, 0]:
                num_green += potion.quantity
                green_ml -= potion.quantity*100
                break
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :green_potions"),{"green_potions": num_green})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml_count"),{"green_ml_count": green_ml})
        
        connection.commit()

    return "OK"



@router.post("/plan")
def get_bottle_plan():
    order_plan = []
    num_green_potions = 0

    with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()

    while("true"):
        if num_green_ml >= 100:
            num_green_potions += 1
            num_green_ml -= 100
        else:
            break

    if num_green_potions >= 1:
        order.append({
            "potion_type": [0, 100, 0, 0],
            "quantity": num_green_potions,
        })

    return order_plan


if __name__ == "__main__":
    print(get_bottle_plan())
