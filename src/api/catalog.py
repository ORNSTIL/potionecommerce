from fastapi import APIRouter
import sqlalchemy
from src import database as db
import ast

router = APIRouter()


def fetch_catalog_items(connection):
    sql = "SELECT * FROM potion_catalog WHERE quantity > 0"
    rows = connection.execute(sqlalchemy.text(sql)).fetchall()
    catalog = []
    for row in rows:
        row = row._asdict()
        catalog.append({
            "sku": row["sku"],
            "name": row["name"],
            "quantity": row["quantity"],
            "price": row["price"],
            "potion_type": ast.literal_eval(row["potion_type"]),
        })
    return catalog

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        catalog = fetch_catalog_items(connection)
    print(f"catalog: {catalog}")
    return catalog
