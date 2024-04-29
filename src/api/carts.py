from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from src.api import auth
from enum import Enum
import sqlalchemy
from src import database as db

cart_id_tracker = 0

router = APIRouter(
    prefix="/carts",
    tags=["cart"],
    dependencies=[Depends(auth.get_api_key)],
)

class search_sort_options(str, Enum):
    customer_name = "customer_name"
    item_sku = "item_sku"
    line_item_total = "line_item_total"
    timestamp = "timestamp"

class search_sort_order(str, Enum):
    asc = "asc"
    desc = "desc"   

@router.get("/search/", tags=["search"])
def search_orders(
    customer_name: str = "",
    potion_sku: str = "",
    search_page: str = "",
    sort_col: search_sort_options = search_sort_options.timestamp,
    sort_order: search_sort_order = search_sort_order.desc,
):
    """
    Search for cart line items by customer name and/or potion sku.

    Customer name and potion sku filter to orders that contain the 
    string (case insensitive). If the filters aren't provided, no
    filtering occurs on the respective search term.

    Search page is a cursor for pagination. The response to this
    search endpoint will return previous or next if there is a
    previous or next page of results available. The token passed
    in that search response can be passed in the next search request
    as search page to get that page of results.

    Sort col is which column to sort by and sort order is the direction
    of the search. They default to searching by timestamp of the order
    in descending order.

    The response itself contains a previous and next page token (if
    such pages exist) and the results as an array of line items. Each
    line item contains the line item id (must be unique), item sku, 
    customer name, line item total (in gold), and timestamp of the order.
    Your results must be paginated, the max results you can return at any
    time is 5 total line items.
    """

    return {
        "previous": "",
        "next": "",
        "results": [
            {
                "line_item_id": 1,
                "item_sku": "1 oblivion potion",
                "customer_name": "Scaramouche",
                "line_item_total": 50,
                "timestamp": "2021-01-01T00:00:00Z",
            }
        ],
    }


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
    delete_cart_items_sql = """
        DELETE FROM cart_inventory WHERE cart_id = :cart_id
    """
    
    with db.engine.begin() as connection:
        transaction_id = connection.execute(
            sqlalchemy.text(transaction_sql)
        ).fetchone()[0]

        cart_items = connection.execute(
            sqlalchemy.text(cart_items_sql), {"cart_id": cart_id}
        ).fetchall()

        total_gold = 0
        for item in cart_items:
            price, potion_type = connection.execute(
                sqlalchemy.text(potion_price_and_type_sql), {"sku": item['item_sku']}
            ).fetchone()

            total_cost = item['quantity'] * price
            total_gold += total_cost

            # Update the potion ledger with the actual potion type
            connection.execute(
                sqlalchemy.text(potion_ledger_update_sql), 
                {
                    "transaction_id": transaction_id,
                    "potion_type": potion_type,
                    "change": -item['quantity']
                }
            )

            # Update the gold ledger
            connection.execute(
                sqlalchemy.text(gold_ledger_update_sql),
                {
                    "transaction_id": transaction_id,
                    "change": total_cost
                }
            )

        # Clear the cart items after checkout
        connection.execute(
            sqlalchemy.text(delete_cart_items_sql), {"cart_id": cart_id}
        )

    return {"total_potions_bought": sum(item['quantity'] for item in cart_items), "total_gold_paid": total_gold}
