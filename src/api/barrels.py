from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/barrels",
    tags=["barrels"],
    dependencies=[Depends(auth.get_api_key)],
)

class Barrel(BaseModel):
    sku: str

    ml_per_barrel: int
    potion_type: list[int]
    price: int

    quantity: int

@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    for barrel in barrels_delivered:
        if barrel.potion_type == [0, 100, 0]:  # Assuming this identifies green potions
            # Calculate the total ml delivered
            total_ml_delivered = barrel.ml_per_barrel * barrel.quantity

            # Update the inventory
            sql_to_execute = """
            UPDATE global_inventory
            SET num_green_ml = num_green_ml + :total_ml_delivered
            WHERE id = 1;
            """
            with db.engine.begin() as connection:
                connection.execute(sqlalchemy.text(sql_to_execute), {"total_ml_delivered": total_ml_delivered})

    return {"message": f"Delivered barrels for order {order_id}"}


# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # Fetch the current gold amount from the database to decide what we can afford
    sql_to_execute = "SELECT gold FROM global_inventory WHERE id = 1;"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        current_gold = result.scalar()

    # Determine what can be bought from the wholesale catalog
    purchase_plan = []
    for barrel in wholesale_catalog:
        if barrel.price <= current_gold and barrel.quantity > 0 and barrel.potion_type == [0, 100, 0]:  # Assuming green potion type
            # Add to purchase plan; do not purchase here, just plan
            purchase_plan.append({"sku": barrel.sku, "quantity": 1})
            break

    return purchase_plan
