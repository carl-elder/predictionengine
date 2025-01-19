#!/usr/bin/env python3

import logging
import os
import sys
import time

# Import your DB manager + exchange classes
from bot.database.database_manager import DatabaseManager
from bot.exchange.robinhood import CryptoAPITrading
from bot.database.db_connect import connect_to_database  # Example if you have a db_connect file

logging.basicConfig(level=logging.INFO)

def main():
    logging.info("Starting update_order_history job...")

    # 1) Establish DB connection
    connection = connect_to_database()  # or however you connect
    if not connection:
        logging.error("Failed to connect to DB.")
        sys.exit(1)

    # 2) Create the DB manager
    db_mgr = DatabaseManager(connection)

    # 3) Initialize Robinhood client
    api_client = CryptoAPITrading()

    # 4) Fetch the data from Robinhood 
    # (In your new method, you might do a loop over all coins, fetch orders, etc.)
    symbols = ["XRP-USD", "ADA-USD", "SOL-USD", "ETC-USD", "XTZ-USD", "LINK-USD", "UNI-USD"]
    for symbol in symbols:
        logging.info(f"Updating order history for {symbol}...")
        try:
            # For example, if you have a helper method that fetches new orders
            new_orders = fetch_new_orders(api_client, db_mgr, symbol)

            # Then you pass them into your DatabaseManager method
            for order_data in new_orders:
                db_mgr.insert_or_update_order_history(symbol, order_data)

        except Exception as e:
            logging.error(f"Error updating {symbol} order history: {e}")

    # 5) Clean up
    connection.close()
    logging.info("Finished update_order_history job.")

def fetch_new_orders(api_client, db_mgr, symbol):
    """
    Example function that gets the last updated timestamp
    from the DB, calls Robinhood, and returns a list of orders.
    """
    table_name = f"{symbol.replace('-USD','').lower()}_order_history"
    last_updated = db_mgr.get_last_updated_at(table_name)  # e.g., if you have that method

    # Convert to the correct format for Robinhood
    if last_updated:
        last_updated_str = last_updated.isoformat() + "Z"
    else:
        last_updated_str = "2022-01-01T00:00:00Z"  # default if table is empty

    # Example path, you may adjust limit, etc.
    path = f"/api/v1/crypto/trading/orders/?limit=500&symbol={symbol}&created_at_start={last_updated_str}"
    response = api_client.make_api_request("GET", path)
    if not response or "results" not in response:
        return []
    return response["results"]

if __name__ == "__main__":
    main()

