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
            
            # Calculate the total cost for these barrels
            total_cost = barrel.price * barrel.quantity
            connection.execute(
                sqlalchemy.text(gold_ledger_sql),
                {"transaction_id": transaction_id, "change": -total_cost}
            )
            
    return {"status": "success"}


@router.post("/plan")
def get_wholesale_purchase_plan(wholesale_catalog: list[Barrel]):
    # Get the current gold balance from the ledger
    gold_balance_sql = """
        SELECT SUM(change) FROM gold_ledger;
    """
    
    # Get the current ml capacity from the global plan
    ml_capacity_sql = """
        SELECT ml_capacity FROM global_plan;
    """
    
    # Get the current inventory from the ml ledger for each type of barrel
    barrel_inventory_sql = """
        SELECT barrel_type, SUM(change) as total_ml FROM ml_ledger GROUP BY barrel_type;
    """
    
    with db.engine.begin() as connection:
        gold_balance = connection.execute(sqlalchemy.text(gold_balance_sql)).scalar()
        ml_capacity = connection.execute(sqlalchemy.text(ml_capacity_sql)).scalar()
        
        barrel_inventory = {
            row['barrel_type']: row['total_ml']
            for row in connection.execute(sqlalchemy.text(barrel_inventory_sql))
        }
        
        barrel_plan = []
        for barrel in wholesale_catalog:
            barrel_type_str = strconvert(barrel.potion_type)
            available_ml_for_type = ml_capacity - barrel_inventory.get(barrel_type_str, 0)
            
            max_barrels_by_ml = available_ml_for_type // barrel.ml_per_barrel
            max_barrels_by_gold = gold_balance // barrel.price
            max_barrels = min(barrel.quantity, max_barrels_by_ml, max_barrels_by_gold)
            
            if max_barrels > 0:
                barrel_plan.append({
                    "sku": barrel.sku,
                    "quantity": max_barrels
                })
                
                # Update the available ML and gold balance after planning to buy
                available_ml_for_type -= max_barrels * barrel.ml_per_barrel
                gold_balance -= max_barrels * barrel.price
                
                # Update the barrel_inventory dictionary
                barrel_inventory[barrel_type_str] = barrel_inventory.get(barrel_type_str, 0) + max_barrels * barrel.ml_per_barrel

    print(barrel_plan)

    return barrel_plan
