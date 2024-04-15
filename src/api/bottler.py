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
        num_red = connection.execute(sqlalchemy.text("SELECT num_red_potions FROM global_inventory")).scalar_one()
        red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar_one()
        num_blue = connection.execute(sqlalchemy.text("SELECT num_blue_potions FROM global_inventory")).scalar_one()
        blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar_one()
        
        for potion in potions_delivered:
            if potion.potion_type == [0, 100, 0, 0]:
                num_green += potion.quantity
                green_ml -= potion.quantity*100
            elif potion.potion_type == [100, 0, 0, 0]:
                num_red += potion.quantity
                red_ml -= potion.quantity*100
            elif potion.potion_type == [0, 0, 100, 0]:
                num_blue += potion.quantity
                blue_ml -= potion.quantity*100

        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_potions = :green_potions"),{"green_potions": num_green})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :green_ml_count"),{"green_ml_count": green_ml})

        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_potions = :red_potions"),{"red_potions": num_red})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_red_ml = :red_ml_count"),{"red_ml_count": red_ml})

        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_potions = :blue_potions"),{"blue_potions": num_blue})
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_blue_ml = :blue_ml_count"),{"blue_ml_count": blue_ml})
        

    return "OK"



@router.post("/plan")
def get_bottle_plan():

    with db.engine.begin() as connection:
        num_green_ml = connection.execute(sqlalchemy.text("SELECT num_green_ml FROM global_inventory")).scalar_one()
        num_red_ml = connection.execute(sqlalchemy.text("SELECT num_red_ml FROM global_inventory")).scalar_one()
        num_blue_ml = connection.execute(sqlalchemy.text("SELECT num_blue_ml FROM global_inventory")).scalar_one()

    num_green_potions = num_green_ml//100
    num_red_potions = num_red_ml//100
    num_blue_potions = num_blue_ml//100

    return [
            {
                "potion_type": [0, 100, 0, 0],
                "quantity": num_green_potions,
            },
            {
                "potion_type": [100, 0, 0, 0],
                "quantity": num_red_potions,
            },
            {
                "potion_type": [0, 0, 100, 0],
                "quantity": num_blue_potions,
            }
        ]


if __name__ == "__main__":
    print(get_bottle_plan())
