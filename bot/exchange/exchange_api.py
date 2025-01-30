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
            
    def get_best_price(self, coins):
        """
        Fetch the best bid and ask prices for the given coin.
        """
        try:
            params = "?symbol="
            
            if len(coins) > 1:
                params = params + "&symbol=".join(str(element) for element in coins)
            else:
                params = params + str(coins[0])
                
            path = f"/api/v1/crypto/marketdata/best_bid_ask/{params}"
            response = self.client.make_api_request("GET", path)
            
            if not response or "results" not in response:
                logging.warning(f"No coin data found: {response}")
                return []
                
            return response["results"]
            
        except Exception as e:
            logging.error(f"Error fetching best price for: {e}", exc_info=True)
            return None

    def get_holdings(self):
        """
        Fetch all of my holdings.
        """
        try:
            response = self.client.get_holdings()
            if not response or "results" not in response:
                logging.warning(f"No holdings data.")
                return None
            return response["results"]
        except Exception as e:
            logging.error(f"Error fetching holdings: {e}", exc_info=True)
            return None
    
    def get_account(self):
        try:
            account = self.client.get_account()
            buying_power = account.get("buying_power")
            if not account or "buying_power" not in account:
                logging.warning(f"Account unavailable. {account} - {buying_power}")
                return None
            return buying_power
        except Exception as e:
            logging.error(f"Error fetching account: {e}", exc_info=True)
            return None
