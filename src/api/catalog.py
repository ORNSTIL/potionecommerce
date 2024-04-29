from fastapi import APIRouter
import sqlalchemy
from src import database as db
import ast

router = APIRouter()

def fetch_catalog_items(connection):
    # Query to fetch potion details along with their available quantities
    get_catalog_sql = """
    SELECT pc.sku, pc.name, pc.price, pc.potion_type, 
           COALESCE(SUM(pl.change), 0) as quantity
    FROM potion_catalog pc
    LEFT JOIN potion_ledger pl ON pc.potion_type = pl.potion_type
    GROUP BY pc.sku, pc.name, pc.price, pc.potion_type
    HAVING COALESCE(SUM(pl.change), 0) > 0;
    """
    catalog_items = connection.execute(sqlalchemy.text(get_catalog_sql)).fetchall()
    catalog = []
    for item in catalog_items:
        catalog.append({
            "sku": item["sku"],
            "name": item["name"],
            "quantity": item["quantity"],
            "price": item["price"],
            "potion_type": ast.literal_eval(item["potion_type"]),  # Convert string to list
        })
    return catalog

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        catalog = fetch_catalog_items(connection)
    print(f"catalog: {catalog}")
    return catalog

