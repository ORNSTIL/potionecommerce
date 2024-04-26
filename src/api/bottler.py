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

def strconvert(intlist):
    return str(intlist)

def divide_lists(list1, list2):
    if len(list1) != len(list2):
        raise ValueError("Input error: Both lists must contain an equal number of elements.")

    results = (num1 // num2 for num1, num2 in zip(list1, list2) if num2 != 0)

    return min(results)

class PotionInventory(BaseModel):
    potion_type: list[int]
    quantity: int

def update_barrel_and_potion_inventory(connection, potion):
    for i in range(4):
        if potion.potion_type[i] == 0:
            continue

        barrel_inventory_sql = """
            UPDATE barrel_inventory SET potion_ml = potion_ml - :potion_ml_decrement
            WHERE barrel_type = :barrel_type
        """
        connection.execute(
            sqlalchemy.text(barrel_inventory_sql),
            {"potion_ml_decrement": potion.quantity * potion.potion_type[i], "barrel_type": strconvert([1 if j == i else 0 for j in range(4)])}
        )

    potion_catalog_sql = """
        UPDATE potion_catalog SET quantity = quantity + :quantity_increment
        WHERE potion_type = :potion_type
    """
    connection.execute(
        sqlalchemy.text(potion_catalog_sql),
        {"quantity_increment": potion.quantity, "potion_type": strconvert(potion.potion_type)}
    )


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

def fetch_barrel_inventory(connection):
    barrel_inventory_table = sqlalchemy.Table('barrel_inventory', metadata, autoload=True, autoload_with=connection)
    barrels = connection.execute(sqlalchemy.select([barrel_inventory_table])).fetchall()
    barrel_inventory = [dict(barrel) for barrel in barrels]
    return barrel_inventory


@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        max_potions = 50
        potion_threshold = fetch_potion_threshold(connection)
        
        print("max potions:", max_potions)
        potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_catalog")).fetchone()[0]
       
        available_potions = max_potions - potions

        barrel_inventory = fetch_barrel_inventory(connection)

        ml_inventory = [0] * 4

        for listing in barrel_inventory:
            potion_ml = listing["potion_ml"]
            barrel_type_list = ast.literal_eval(listing["barrel_type"])
            for i in range(4):
                ml_inventory[i] += potion_ml * barrel_type_list[i]



        potions = connection.execute(sqlalchemy.select([potion_catalog]).order_by(potion_catalog.c.price.desc())).fetchall()

        bottling_plan = []
        print("current available potion count:", available_potions)
        for potion in potions:
            if potion.quantity > potion_threshold:
                continue

            potion = dict(potion)
            quantity = min(divide_lists(ml_inventory, ast.literal_eval(potion["potion_type"])), available_potions)
            available_potions -= quantity
            
            ml_inventory = [ml_inventory[i] - quantity * ast.literal_eval(potion["potion_type"])[i] for i in range(4)]

            if quantity > 0:
                bottling_plan.append({"potion_type": ast.literal_eval(potion["potion_type"]), "quantity": quantity})

            print("potion type:", potion["potion_type"])
            print("and now available potion count:", available_potions)

        print(f"bottling_plan: {bottling_plan}")
        return bottling_plan


if __name__ == "__main__":
    print(get_bottle_plan())
