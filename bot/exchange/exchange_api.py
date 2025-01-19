import logging
import uuid

class ExchangeAPI:
    def __init__(self, client):
        self.client = client

    def place_order(self, order_type, coin, price, quantity, order_config=None):
        try:
            client_order_id = str(uuid.uuid4())
            side = "buy" if order_type == "buy" else "sell"

            order_data = {
                "asset_quantity": quantity,
                "limit_price": price,
                "time_in_force": "gtc",
            }

            if order_config:
                order_data.update(order_config)

            return self.client.place_order(
                client_order_id=client_order_id,
                side=side,
                order_type=order_type,
                symbol=coin,
                order_config=order_data,
            )
        except Exception as e:
            logging.error(f"Error placing {order_type} order for {coin}: {e}", exc_info=True)
            return None


    def get_executed_orders(self, symbol: str, last_timestamp: str = None) -> list:
        """
        Fetch executed orders for a specific symbol after a given timestamp.
        :param symbol: Coin symbol (e.g., "BTC-USD").
        :param last_timestamp: ISO8601 timestamp for filtering newer orders.
        :return: List of executed orders.
        """
        try:
            # Build the request path
            params = f"?symbol={symbol}"
            if last_timestamp:
                params += f"&created_at_start={last_timestamp}"
            path = f"/api/v1/crypto/trading/orders/{params}"

            # Fetch orders from API
            response = self.client.make_api_request("GET", path)
            if not response or "results" not in response:
                logging.warning(f"No order data found for {symbol}.")
                return []

            # Filter executed orders
            executed_orders = [
                order for order in response["results"] if order["state"] == "filled"
            ]
            return executed_orders

        except Exception as e:
            logging.error(f"Error fetching executed orders: {e}", exc_info=True)
            return []
            
    def get_best_price(self, coin = ''):
        """
        Fetch the best bid and ask prices for the given coin.
        """
        try:
            response = self.client.get_best_bid_ask(coin)
            if not response or "results" not in response:
                logging.warning(f"No best price data for {coin}.")
                return None
            return response
        except Exception as e:
            logging.error(f"Error fetching best price for {coin}: {e}", exc_info=True)
            return None

    def get_holdings(self):
        """
        Fetch the holdings for aall coin.
        """
        try:
            response = self.client.get_holdings()
            if not response or "results" not in response:
                logging.warning(f"No holdings data.")
                return None
            return response
        except Exception as e:
            logging.error(f"Error fetching holdings: {e}", exc_info=True)
            return None
    
    def get_account(self):
        try:
            response = self.client.get_account()
            if not response or "buying_power" not in response:
                logging.warning(f"Account unavailable.")
                return None
            return response
        except Exception as e:
            logging.error(f"Error fetching account: {e}", exc_info=True)
            return None
