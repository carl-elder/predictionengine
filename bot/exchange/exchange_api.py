import logging
import uuid

class ExchangeAPI:
    def __init__(self, client):
        self.client = client

    def place_order(self, order_type, coin, price, quantity):
        try:
            client_order_id = str(uuid.uuid4())  # Generate a unique client order ID
            side = "buy" if order_type == "buy" else "sell"  # Determine the side of the order

            order_config = {
                "asset_quantity": quantity,
                "limit_price": price,
                "time_in_force": "gtc",
            }
            return self.client.place_order(
                client_order_id=client_order_id,
                side=side,
                order_type=order_type,
                symbol=coin,
                order_config=order_config,
            )
        except Exception as e:
            logging.error(f"Error placing {order_type} order for {coin}: {e}", exc_info=True)
            return None

    def get_best_price(self, coin):
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
