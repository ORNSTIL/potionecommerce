from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))

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
    """ """
    print(f"barrels delievered: {barrels_delivered} order_id: {order_id}")

    return "OK"

# Gets called once a day
@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    """ """
    sql_to_execute = "SELECT num_green_potions FROM global_inventory WHERE id = 1;"
    with db.engine.begin() as connection:
        result = connection.execute(sqlalchemy.text(sql_to_execute))
        current_potions = result.scalar()

    purchase_plan = []
    if current_potions < 10:
        # Logic to determine the purchase plan for new barrels
        purchase_plan.append({"sku": "SMALL_GREEN_BARREL", "quantity": 1})
    
    return purchase_plan
