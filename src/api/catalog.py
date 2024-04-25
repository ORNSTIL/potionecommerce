from fastapi import APIRouter
import sqlalchemy
from src import database as db
import ast

router = APIRouter()


def fetch_catalog_items(connection):
    get_catalog_sql = "SELECT * FROM potion_catalog WHERE quantity > 0"
    get_catalogs = connection.execute(sqlalchemy.text(get_catalog_sql)).fetchall()
    catalog = []
    for get_catalog in get_catalogs:
        get_catalog = get_catalog._asdict()
        catalog.append({
            "sku": get_catalog["sku"],
            "name": get_catalog["name"],
            "quantity": get_catalog["quantity"],
            "price": get_catalog["price"],
            "potion_type": ast.literal_eval(get_catalog["potion_type"]),
        })
    return catalog

@router.get("/catalog/", tags=["catalog"])
def get_catalog():
    with db.engine.begin() as connection:
        catalog = fetch_catalog_items(connection)
    print(f"catalog: {catalog}")
    return catalog
