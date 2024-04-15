from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(auth.get_api_key)],
)

@router.post("/reset")
def reset():
    """
    Reset the game state. Gold goes to 100, all potions are removed from
    inventory, and all barrels are removed from inventory. Carts are all reset.
    """
    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text("UPDATE global_inventory SET num_green_ml = :reset_ml, num_red_ml = :reset_ml, num_blue_ml = :reset_ml, num_green_potions = :reset_potions, num_red_potions = :reset_potions, num_blue_potions = :reset_potions, gold = :reset_gold"), {"reset_ml": 0, "reset_potions": 0, "reset_gold": 100})
        
    return "OK"

