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
    print(wholesale_catalog)
    gold_balance_sql = """
        SELECT SUM(change) FROM gold_ledger;
    """

    ml_capacity_sql = """
        SELECT ml_capacity FROM global_plan;
    """

    potion_quantity_sql = """
        SELECT potion_type, COALESCE(SUM(change), 0) AS total_quantity
        FROM potion_ledger
        GROUP BY potion_type;
    """

    barrel_inventory_sql = """
        SELECT barrel_type, SUM(change) as total_ml FROM ml_ledger GROUP BY barrel_type;
    """

    with db.engine.begin() as connection:
        gold_balance = connection.execute(sqlalchemy.text(gold_balance_sql)).scalar()
        ml_capacity = connection.execute(sqlalchemy.text(ml_capacity_sql)).scalar()

        potion_quantities = connection.execute(sqlalchemy.text(potion_quantity_sql)).mappings().fetchall()
        potion_inventory = {row['potion_type']: row['total_quantity'] for row in potion_quantities}

        barrel_inventory_results = connection.execute(sqlalchemy.text(barrel_inventory_sql)).mappings().fetchall()
        barrel_inventory = {row['barrel_type']: row['total_ml'] for row in barrel_inventory_results}

        barrels_by_efficiency = [
            {
                "barrel": barrel,
                "efficiency": barrel.ml_per_barrel / barrel.price,
                "shortage": ml_capacity - potion_inventory.get(str(barrel.potion_type), 0),
                "available_ml": ml_capacity - barrel_inventory.get(str(barrel.potion_type), 0)
            }
            for barrel in wholesale_catalog if barrel.ml_per_barrel > 0
        ]

        # Sort barrels by efficiency and shortage (higher efficiency and more shortage first)
        barrels_by_efficiency.sort(key=lambda x: (-x['efficiency'], -x['shortage']))

        barrel_plan = []
        for barrel_info in barrels_by_efficiency:
            barrel = barrel_info['barrel']

            max_possible_by_ml = barrel_info['available_ml'] // barrel.ml_per_barrel
            max_possible_by_gold = gold_balance // barrel.price
            purchase_quantity = min(barrel.quantity, max_possible_by_ml, max_possible_by_gold)

            if purchase_quantity > 0:
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": purchase_quantity
                })

                gold_spent = purchase_quantity * barrel.price
                gold_balance -= gold_spent

                if gold_balance < 0:
                    break

    print(barrel_plan)
    return barrel_plan
