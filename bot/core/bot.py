import logging
from datetime import datetime

class Bot:
    def __init__(self, symbols, api, db_manager, strategy):
        """
        :param symbols: list of coins, e.g. ["BTC-USD", "ETH-USD", ...]
        :param api: an object with methods like get_best_price(...)
        :param db_manager: your DatabaseManager object with insert_data, fetch_data, etc.
        :param strategy: instance of ScalpingStrategy
        """
        self.symbols = symbols
        self.api = api
        self.db_manager = db_manager
        self.strategy = strategy

    def run(self):
        # Build a dictionary to hold best_price data for *each* coin (once per run)
        best_price_dict = {}

        for coin in self.symbols:
            logging.info(f"Processing {coin}...")
            try:
                # Fetch best price data once
                coin_data = self.api.get_best_price(coin)
                if not coin_data or "results" not in coin_data:
                    logging.warning(f"No data for {coin}. Skipping...")
                    continue

                # Insert into DB and store in dictionary
                self.db_manager.insert_data(coin, coin_data)
                best_price_dict[coin] = coin_data
            except Exception as e:
                logging.error(f"Error fetching or storing data for {coin}: {e}", exc_info=True)
                continue

            try:
                # Fetch historical data
                historical_data = self.db_manager.fetch_data(coin)

                # Execute strategy with pre-fetched best_price data
                self.strategy.execute_strategy(
                    coin,
                    coin_data,
                    historical_data,
                    self.api,
                    self.db_manager,
                    best_price_dict
                )
            except Exception as e:
                logging.error(f"Error executing strategy for {coin}: {e}", exc_info=True)
                continue

            try:
                # Handle executed orders for this coin
                last_timestamp = self.db_manager.get_last_timestamp(coin)
                executed_orders = self.api.get_executed_orders(coin, last_timestamp)

                for order in executed_orders:
                    self.strategy.handle_post_buy_actions(order, self.api)
                    self.db_manager.update_last_timestamp(coin, order["updated_at"])
            except Exception as e:
                logging.error(f"Error processing executed orders for {coin}: {e}", exc_info=True)
