from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import ast

router = APIRouter(
    prefix="/bottler",
    tags=["bottler"],
    dependencies=[Depends(auth.get_api_key)],
)

def potion_type_tostr(potion_type):
    return str(potion_type)

def list_floor_division(list1, list2):
    if len(list1) != len(list2):
        raise ValueError("Lists must be of the same length")
    available = []
    for i in range(len(list1)):
        if list2[i] == 0:
            continue
        available.append(list1[i] // list2[i])
    return min(available)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

def update_barrel_and_potion_inventory(connection, potion):
    for i in range(4):
        barrel_type = [0] * 4
        barrel_type[i] = 1
        if potion.potion_type[i] == 0:
            continue
        barrel_sql = f"""
            UPDATE barrel_inventory SET potion_ml = potion_ml - {potion.quantity * potion.potion_type[i]}
            WHERE barrel_type = '{potion_type_tostr(barrel_type)}'
        """
        connection.execute(sqlalchemy.text(barrel_sql))

    gold_sql = f"""
        UPDATE potion_catalog SET quantity = quantity + {potion.quantity}
        WHERE potion_type = '{potion_type_tostr(potion.potion_type)}'
    """
    connection.execute(sqlalchemy.text(gold_sql))

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    print(f"potions delivered: {potions_delivered} order_id: {order_id}")
    with db.engine.begin() as connection:
        for potion in potions_delivered:
            update_barrel_and_potion_inventory(connection, potion)
    return "OK"

def fetch_potion_threshold(connection):
    result = connection.execute(sqlalchemy.text("SELECT potion_threshold FROM global_inventory"))
    return result.fetchone()[0]

def fetch_max_potions(connection):
    result = connection.execute(sqlalchemy.text("SELECT potion_capacity FROM global_plan"))
    return result.fetchone()[0] * 50

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        potion_threshold = fetch_potion_threshold(connection)
        max_potions = fetch_max_potions(connection)
        potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_catalog")).fetchone()[0]
        available_potions = max_potions - potions

        barrel_inventory = connection.execute(sqlalchemy.text("SELECT * FROM barrel_inventory"))
        ml_inventory = [0] * 4
        rows = barrel_inventory.fetchall()
        rows = [row._asdict() for row in rows]
        for row in rows:
            potion_ml = row["potion_ml"]
            barrel_type_list = ast.literal_eval(row["barrel_type"])
            for i in range(4):
                ml_inventory[i] += row["potion_ml"] * barrel_type_list[i]

        potion_catalog = connection.execute(sqlalchemy.text("SELECT * FROM potion_catalog"))
        potions = potion_catalog.fetchall()
        potions.sort(key=lambda x: x.price, reverse=True)
        bottling_plan = []

        for potion in potions:
            result = connection.execute(sqlalchemy.text("SELECT quantity FROM potion_catalog WHERE potion_type = :potion_type"), {"potion_type": potion_type_tostr(potion.potion_type)})
            potion_quantity = result.fetchone()[0]
            if potion_quantity > potion_threshold:
                continue

            potion = potion._asdict()
            quantity = list_floor_division(ml_inventory, ast.literal_eval(potion["potion_type"]))
            quantity = min(quantity, available_potions)
            available_potions -= quantity
            ml_inventory = [ml_inventory[i] - quantity * (ast.literal_eval(potion["potion_type"]))[i] for i in range(4)]

            if quantity > 0:
                bottling_plan.append({"potion_type": ast.literal_eval(potion["potion_type"]), "quantity": quantity})

        print(f"bottling_plan: {bottling_plan}")
        return bottling_plan



if __name__ == "__main__":
    print(get_bottle_plan())
