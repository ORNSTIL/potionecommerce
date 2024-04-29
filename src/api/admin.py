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
    Reset the game state. Set gold back to 100, and remove all potions and barrels from inventory.
    This is done by inserting compensating transactions in the ledgers that negate existing quantities and balances.
    """
    with db.engine.begin() as connection:
        # Get the current total changes from each ledger to know how much to offset
        current_gold_total = connection.execute(
            sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM gold_ledger")
        ).scalar()

        # Calculate the difference needed to reset gold to 100
        gold_difference = 100 - current_gold_total

        # Adjust the gold ledger to set balance to 100
        connection.execute(
            sqlalchemy.text("INSERT INTO gold_ledger (change) VALUES (:change)"),
            {"change": gold_difference}
        )

        # Reset potion quantities in the potion ledger
        potion_types = connection.execute(
            sqlalchemy.text("SELECT DISTINCT potion_type FROM potion_ledger")
        ).fetchall()

        for potion in potion_types:
            current_quantity = connection.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM potion_ledger WHERE potion_type = :potion_type"),
                {"potion_type": potion['potion_type']}
            ).scalar()
            
            # Compensate to reset quantity to zero
            if current_quantity != 0:
                connection.execute(
                    sqlalchemy.text("INSERT INTO potion_ledger (potion_type, change) VALUES (:potion_type, :change)"),
                    {"potion_type": potion['potion_type'], "change": -current_quantity}
                )

        # Reset barrel quantities in the ml ledger
        barrel_types = connection.execute(
            sqlalchemy.text("SELECT DISTINCT barrel_type FROM ml_ledger")
        ).fetchall()

        for barrel in barrel_types:
            current_ml = connection.execute(
                sqlalchemy.text("SELECT COALESCE(SUM(change), 0) FROM ml_ledger WHERE barrel_type = :barrel_type"),
                {"barrel_type": barrel['barrel_type']}
            ).scalar()
            
            # Compensate to reset ml to zero
            if current_ml != 0:
                connection.execute(
                    sqlalchemy.text("INSERT INTO ml_ledger (barrel_type, change) VALUES (:barrel_type, :change)"),
                    {"barrel_type": barrel['barrel_type'], "change": -current_ml}
                )

        # Reset carts and cart inventory
        connection.execute(sqlalchemy.text("DELETE FROM carts"))
        connection.execute(sqlalchemy.text("DELETE FROM cart_inventory"))

    return "OK"
