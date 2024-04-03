from fastapi import APIRouter
import sqlalchemy
from src import database as db

router = APIRouter()


@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    sql_to_execute = "SELECT num_green_potions, gold FROM global_inventory WHERE id = 1;"
    with db.engine.begin() as connection:
        inventory_info = connection.execute(sqlalchemy.text(sql_to_execute)).fetchone()

    catalog_items = []
    if inventory_info['num_green_potions'] > 0:
        catalog_items.append({"sku": "GREEN_POTION", "quantity": inventory_info['num_green_potions'], "price": potion_price})

    return catalog_items
