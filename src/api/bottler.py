from fastapi import APIRouter, Depends
from enum import Enum
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
import ast
from sqlalchemy import Table, MetaData, Column, Integer, String, Text, Float, select, func


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
    barrels = connection.execute(sqlalchemy.text("SELECT * FROM barrel_inventory"))
    barrel_inventory = [dict(barrel) for barrel in barrels.fetchall()] 

    return barrel_inventory


@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        potion_threshold = fetch_potion_threshold(connection)
        
        max_potions = 50
        total_potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_catalog")).fetchone()[0]
        available_potions = max_potions - total_potions

        ml_inventory = 4*[0]
        
        barrel_inventory = fetch_barrel_inventory(connection)
        for listing in barrel_inventory:
            potion_ml = listing["potion_ml"]
            barrel_type_list = ast.literal_eval(listing["barrel_type"])
            for i in range(4):
                ml_inventory[i] += potion_ml * barrel_type_list[i]

        potions = connection.execute(text("SELECT potion_catalog WHERE quantity <= potion_threshold ORDER_BY price DESC"), {"potion_threshold": potion_threshold}).fetchall()


        total_ml_required = {tuple(ast.literal_eval(potion["potion_type"])): 0 for potion in potions}
        for potion in potions:
            potion_type = tuple(ast.literal_eval(potion["potion_type"]))
            total_ml_required[potion_type] += sum(potion_type)

        ml_allocation = {}
        for potion_type, ml in zip(total_ml_required.keys(), ml_inventory):
            if sum(potion_type) > 0:
                ml_allocation[potion_type] = min(ml, available_potions * sum(potion_type) / sum(ml_inventory))

        bottling_plan = []
        print("current available potion count:", available_potions)

        for potion_type, ml_needed in total_ml_required.items():
            quantity = min(ml_allocation.get(potion_type, 0), available_potions)
            available_potions -= quantity

            if quantity > 0:
                bottling_plan.append({"potion_type": potion_type, "quantity": quantity})

            print("potion type:", potion_type)
            print("and now available potion count:", available_potions)

        print(f"bottling_plan: {bottling_plan}")
        return bottling_plan


if __name__ == "__main__":
    print(get_bottle_plan())
