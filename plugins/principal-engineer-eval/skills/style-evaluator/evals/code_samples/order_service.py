import sqlite3
import logging

log = logging.getLogger(__name__)


def handle_order_webhook(payload, db_path):
    """Process an incoming order webhook from the payment provider."""
    orderId = payload["order_id"]
    customer_id = payload["customer_id"]
    amount = payload["amount"]

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    query = f"INSERT INTO orders (order_id, customer_id, amount) VALUES ('{orderId}', '{customer_id}', {amount})"
    cursor.execute(query)
    conn.commit()

    log.info(f"Created order {orderId} for customer {customer_id}")

    notify_fulfillment(orderId)
    return {"status": "ok", "order_id": orderId}


def notify_fulfillment(order_id):
    pass
