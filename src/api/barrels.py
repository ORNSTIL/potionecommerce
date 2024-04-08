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
        if barrel.potion_type == [0, 100, 0, 0]:  # green potion type
            with db.engine.begin() as connection:
                connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = num_green_ml + :ml WHERE id = 1"),
                                   ml=barrel.ml_per_barrel * barrel.quantity)
    return "OK"

@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    with db.engine.begin() as connection:
        inventory_info = connection.execute(sqlalchemy.text("SELECT gold, num_green_potions FROM global_inventory WHERE id = 1")).fetchone()
        if inventory_info[1] < 10:
            for barrel in wholesale_catalog:
                if barrel.potion_type == [0, 100, 0, 0] and inventory_info[0] >= barrel.price:  # green potions only
                    return [{"sku": barrel.sku, "quantity": 1}]
    return []
