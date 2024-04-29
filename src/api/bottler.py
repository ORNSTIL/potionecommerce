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

@router.post("/deliver/{order_id}")
def post_deliver_bottles(potions_delivered: list[PotionInventory], order_id: int):
    transaction_sql = """
        INSERT INTO transactions (type, created_at)
        VALUES ('potion_delivery', CURRENT_TIMESTAMP) RETURNING id;
    """
    potion_ledger_sql = """
        INSERT INTO potion_ledger (transaction_id, potion_type, change)
        VALUES (:transaction_id, :potion_type, :change);
    """
    ml_ledger_sql = """
        INSERT INTO ml_ledger (transaction_id, barrel_type, change)
        VALUES (:transaction_id, :barrel_type, :change);
    """

    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(transaction_sql)
        ).fetchone()[0]

        for potion in potions_delivered:
            print("potion to be delivered:", potion)
            connection.execute(
                sqlalchemy.text(potion_ledger_sql),
                {
                    "transaction_id": transaction_id,
                    "potion_type": strconvert(potion.potion_type),
                    "change": potion.quantity
                }
            )
            
            # Deduct the ml used from the ml ledger for each ingredient type
            for color_index, ml in enumerate(potion.potion_type):
                if ml > 0:
                    connection.execute(
                        sqlalchemy.text(ml_ledger_sql),
                        {
                            "transaction_id": transaction_id,
                            "barrel_type": strconvert([1 if i == color_index else 0 for i in range(4)]),
                            "change": -ml * potion.quantity
                        }
                    )

    return {"status": "success"}


@router.post("/plan")
def get_bottle_plan():
    transaction_sql = """
        INSERT INTO transactions (type, created_at)
        VALUES ('bottle_plan', CURRENT_TIMESTAMP) RETURNING id;
    """
    potion_capacity_sql = """
        SELECT potion_capacity FROM global_plan;
    """
    potion_inventory_sql = """
        SELECT potion_type, SUM(change) AS total_quantity
        FROM potion_ledger
        GROUP BY potion_type;
    """
    ml_inventory_sql = """
        SELECT barrel_type, SUM(change) AS total_ml
        FROM ml_ledger
        GROUP BY barrel_type;
    """
    desired_potions_sql = """
        SELECT potion_type FROM potion_catalog;
    """

    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(transaction_sql)
        ).fetchone()[0]

        potion_capacity = connection.execute(
            sqlalchemy.text(potion_capacity_sql)
        ).scalar()

        current_potion_inventory = {
            row['potion_type']: row['total_quantity']
            for row in connection.execute(sqlalchemy.text(potion_inventory_sql))
        }

        ml_inventory = {
            row['barrel_type']: row['total_ml']
            for row in connection.execute(sqlalchemy.text(ml_inventory_sql))
        }

        dp = connection.execute(sqlalchemy.text(desired_potions_sql))
        desired_potions = [
            ast.literal_eval(row['potion_type']) for row in dp.mappings()
        ]

        bottling_plan = []
        available_potion_space = potion_capacity - sum(current_potion_inventory.values())

        for potion_type in desired_potions:
            potion_type_str = strconvert(potion_type)
            can_produce = min(
                (ml_inventory.get(strconvert([1 if i == index else 0 for index in range(4)]), 0) // amount)
                for index, amount in enumerate(potion_type)
                if amount > 0
            )

            quantity_to_produce = min(can_produce, available_potion_space)
            if quantity_to_produce > 0:
                bottling_plan.append({
                    "potion_type": potion_type,
                    "quantity": quantity_to_produce
                })

                available_potion_space -= quantity_to_produce
    print(bottling_plan)

    return bottling_plan




if __name__ == "__main__":
    print(get_bottle_plan())
