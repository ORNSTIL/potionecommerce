from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db
from datetime import datetime
from fastapi import HTTPException, Query
from sqlalchemy import select, text, desc, asc
from sqlalchemy.sql import func


cart_id_tracker = 0

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "quantity"
    timestamp = "created_at"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   


@router.get("/search/", tags=["search"])
async def search_orders(
    request: Request,
    customer_name: str = Query(None),
    potion_sku: str = Query(None),
    search_page: int = 1,
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
    limit: int = 5
):

    offset = (search_page - 1) * limit
    params = {"limit": limit, "offset": offset}

    base_query = """
        SELECT c.id AS cart_id, c.customer_name, ci.item_sku, ci.quantity AS line_item_total, 
               c.created_at AS timestamp
        FROM carts c
        JOIN cart_inventory ci ON c.id = ci.cart_id
        WHERE 1=1
    """

    if customer_name:
        base_query += " AND c.customer_name ILIKE :customer_name"
        params['customer_name'] = f"%{customer_name}%"
    if potion_sku:
        base_query += " AND ci.item_sku ILIKE :potion_sku"
        params['potion_sku'] = f"%{potion_sku}%"

    order_clause = f" ORDER BY c.{sort_col} {sort_order.value} LIMIT :limit OFFSET :offset"
    final_query = base_query + order_clause

    try:
        with db.engine.begin() as connection:
            result = connection.execute(text(final_query), params).mappings().all()
            data = [dict(row) for row in result]
            return {
                "previous": search_page - 1 if search_page > 1 else None,
                "next": search_page + 1 if len(data) == limit else None,
                "results": data
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class Customer(BaseModel):
    customer_name: str
    character_class: str
    level: int

@router.post("/visits/{visit_id}")
def post_visits(visit_id: int, customers: list[Customer]):
    """
    Which customers visited the shop today?
    """
    print(customers)

    return "OK"


@router.post("/")
def create_cart(new_cart: Customer):
    create_cart_sql = """
        INSERT INTO carts (customer_name, character_class, level, created_at)
        VALUES (:customer_name, :character_class, :level, :created_at) RETURNING id
    """

    with db.engine.begin() as connection:
        cart_id = connection.execute(sqlalchemy.text(create_cart_sql), {
            "customer_name": new_cart.customer_name,
            "character_class": new_cart.character_class,
            "level": new_cart.level,
            "created_at": datetime.now()
        }).fetchone()[0]
    print("cart id:", cart_id)
    
    return {"cart_id": cart_id}


class CartItem(BaseModel):
    quantity: int


@router.put("/{cart_id}/items/{item_sku}")
def set_item_quantity(cart_id: int, item_sku: str, cart_item: CartItem):
    add_item_sql = """
        INSERT INTO cart_inventory (cart_id, item_sku, quantity, added_at)
        VALUES (:cart_id, :item_sku, :quantity, :added_at)
        ON CONFLICT (cart_id, item_sku) DO UPDATE
        SET quantity = excluded.quantity, added_at = excluded.added_at
    """

    with db.engine.begin() as connection:
        connection.execute(sqlalchemy.text(add_item_sql), {
            "cart_id": cart_id,
            "item_sku": item_sku,
            "quantity": cart_item.quantity,
            "added_at": datetime.now()
        })

    print("setting item quantity:", cart_item.quantity, "on cart id:", cart_id, "for item:", item_sku)
        
    return {"status": "success"}



class CartCheckout(BaseModel):
    payment: str

@router.post("/{cart_id}/checkout")
def checkout(cart_id: int, cart_checkout: CartCheckout):
    transaction_sql = """
        INSERT INTO transactions (type, created_at)
        VALUES ('checkout', CURRENT_TIMESTAMP) RETURNING id;
    """
    cart_items_sql = """
        SELECT item_sku, quantity FROM cart_inventory WHERE cart_id = :cart_id
    """
    potion_price_and_type_sql = """
        SELECT price, potion_type FROM potion_catalog WHERE sku = :sku
    """
    potion_ledger_update_sql = """
        INSERT INTO potion_ledger (transaction_id, potion_type, change)
        VALUES (:transaction_id, :potion_type, :change)
    """
    gold_ledger_update_sql = """
        INSERT INTO gold_ledger (transaction_id, change)
        VALUES (:transaction_id, :change)
    """

    
    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(transaction_sql)
        ).fetchone()[0]

        cart_items = connection.execute(
            sqlalchemy.text(cart_items_sql), {"cart_id": cart_id}
        ).mappings().all()

        total_gold = 0
        for item in cart_items:
            print("total gold:", total_gold)
            price, potion_type = connection.execute(
                sqlalchemy.text(potion_price_and_type_sql), {"sku": item['item_sku']}
            ).fetchone()

            print("price:", price)
            print("potion_type:", potion_type)

            total_cost = item['quantity'] * price
            print("total cost:", total_cost)
            total_gold += total_cost

            connection.execute(
                sqlalchemy.text(potion_ledger_update_sql), 
                {
                    "transaction_id": transaction_id,
                    "potion_type": potion_type,
                    "change": -item['quantity']
                }
            )
            print("potion ledger update")
            print("transaction_id:", transaction_id)
            print("potion_type:", potion_type)
            print("change:", -item['quantity'])
            
            connection.execute(
                sqlalchemy.text(gold_ledger_update_sql),
                {
                    "transaction_id": transaction_id,
                    "change": total_cost
                }
            )
            print("gold ledger update")
            print("transaction_id:", transaction_id)
            print("change:", total_cost)
        
        print("total gold:", total_gold)

        
    print("total_potions_bought:", sum(item['quantity'] for item in cart_items), "total_gold_paid:", total_gold)
    return {"total_potions_bought": sum(item['quantity'] for item in cart_items), "total_gold_paid": total_gold}
