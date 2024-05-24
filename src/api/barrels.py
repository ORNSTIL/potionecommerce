from fastapi import APIRouter, Depends
from pydantic import BaseModel
from src.api import auth
import sqlalchemy
from src import database as db
from sqlalchemy.sql import func

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

def strconvert(intlist):
    return str(intlist)
    
@router.post("/deliver/{order_id}")
def post_deliver_barrels(barrels_delivered: list[Barrel], order_id: int):
    print(barrels_delivered)

    create_transaction_sql = """
        INSERT INTO transactions (type, created_at)
        VALUES ('barrel_delivery', CURRENT_TIMESTAMP) RETURNING id;
    """
    

    ml_ledger_sql = """
        INSERT INTO ml_ledger (transaction_id, barrel_type, change)
        VALUES (:transaction_id, :barrel_type, :change);
    """
    

    gold_ledger_sql = """
        INSERT INTO gold_ledger (transaction_id, change)
        VALUES (:transaction_id, :change);
    """
    
    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(create_transaction_sql)
        ).fetchone()[0]
        
        for barrel in barrels_delivered:
            print("barrel to be delivered:", barrel)
            # Calculate the total ML for this type of barrel
            total_ml = barrel.ml_per_barrel * barrel.quantity
            connection.execute(
                sqlalchemy.text(ml_ledger_sql),
                {"transaction_id": transaction_id, "barrel_type": strconvert(barrel.potion_type), "change": total_ml}
            )
            print("ml transaction_id:", transaction_id)
            print("barrel_type:", strconvert(barrel.potion_type)) 
            print("ml change:", total_ml)
            
            # Calculate the total cost for these barrels
            total_cost = barrel.price * barrel.quantity
            connection.execute(
                sqlalchemy.text(gold_ledger_sql),
                {"transaction_id": transaction_id, "change": -total_cost}
            )
            print("gold transaction_id:", transaction_id)
            print("gold change:", -total_cost)
            
    return {"status": "success"}


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    gold_balance_sql = """
        SELECT SUM(change) FROM gold_ledger;
    """
    ml_capacity_sql = """
        SELECT ml_capacity FROM global_plan;
    """
    total_ml_used_sql = """
        SELECT COALESCE(SUM(change), 0) FROM ml_ledger;
    """

    with db.engine.begin() as connection:
        gold_balance = connection.execute(sqlalchemy.text(gold_balance_sql)).scalar()
        ml_capacity = connection.execute(sqlalchemy.text(ml_capacity_sql)).scalar()
        total_ml_used = connection.execute(sqlalchemy.text(total_ml_used_sql)).scalar()

        available_ml = ml_capacity - total_ml_used

        barrel_plan = []
        for barrel in sorted(wholesale_catalog, key=lambda x: (x.ml_per_barrel / x.price), reverse=True):
            print("available ml:", available_ml)
            if barrel.ml_per_barrel <= 0:
                continue

            max_possible_by_ml = available_ml // barrel.ml_per_barrel
            max_possible_by_gold = gold_balance // barrel.price
            purchase_quantity = min(barrel.quantity, max_possible_by_ml, max_possible_by_gold)

            if purchase_quantity > 0:
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": purchase_quantity
                })

                gold_spent = purchase_quantity * barrel.price
                gold_balance -= gold_spent

                ml_added = purchase_quantity * barrel.ml_per_barrel
                available_ml -= ml_added

                if available_ml <= 0 or gold_balance <= 0:
                    break

        print(barrel_plan)
        return []

    return {"status": "success"}
