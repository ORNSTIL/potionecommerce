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
    barrel_inventory = connection.execute(sqlalchemy.text("SELECT * FROM barrel_inventory"))
    barrels = barrel_inventory.fetchall()
    barrels = [barrel._asdict() for barrel in barrels]

    return barrels

def calculate_proportions(array, ratios):
    total = sum(array)
    results = []
    
    for i, ratio in enumerate(ratios):
        if ratio > 0:
            x = ratio / 100
            proportion = (x * array[i]) / total if total > 0 else 0
        else:
            proportion = 0
        results.append(proportion)
    
    return results

@router.post("/plan")
def get_bottle_plan():
    with db.engine.begin() as connection:
        potion_threshold = fetch_potion_threshold(connection)
        
        max_potions = 50
        total_potions = connection.execute(sqlalchemy.text("SELECT SUM(quantity) FROM potion_catalog")).fetchone()[0]
        available_potions = max_potions - total_potions

        ml_inventory = 4*[0]
        
        barrel_inventory = fetch_barrel_inventory(connection)
        for barrel in barrel_inventory:
            potion_ml = barrel["potion_ml"]
            barrel_type_list = ast.literal_eval(barrel["barrel_type"])
            for i in range(4):
                ml_inventory[i] += potion_ml * barrel_type_list[i]
        print(ml_inventory)

        potions = connection.execute(sqlalchemy.text("SELECT potion_type FROM potion_catalog WHERE quantity <= :potion_threshold ORDER BY price DESC"), {"potion_threshold": potion_threshold}).fetchall()

  
        total_ml_required = {}
        for potion in potions:
            potion_type_str = potion[0] 
            potion_type_list = ast.literal_eval(potion_type_str)
            total_ml_required[tuple(potion_type_list)] = 0

        print(total_ml_required)
        ml_allocation = {}
        for potion_type in total_ml_required.keys():
            print(potion_type)
            print(ml_inventory)
            amount_array = calculate_proportions(ml_inventory, potion_type)
            print(amount_array)
            ml_allocation[potion_type] = int(sum(amount_array) * available_potions)

        print(ml_allocation)
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
