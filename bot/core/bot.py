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
        # 1) Build a dictionary to hold best_price data for *each* coin (once per run)
        best_price_dict = {}

        for coin in self.symbols:
            logging.info(f"Processing {coin}...")

            try:
                # 2) Fetch best price data once
                coin_data = self.api.get_best_price(coin)
                if not coin_data or "results" not in coin_data:
                    logging.warning(f"No data for {coin}. Skipping...")
                    continue

                # 3) Insert into DB so we have the record
                self.db_manager.insert_data(coin, coin_data)

                # 4) Store in a dictionary so strategy can use it (and we avoid re-calling the API)
                best_price_dict[coin] = coin_data

            except Exception as e:
                logging.error(f"Error fetching data for {coin}: {e}", exc_info=True)

        # 5) For each coin, fetch historical data and run the strategy
        for coin in self.symbols:
            try:
                # If we didn't get coin_data, skip
                if coin not in best_price_dict:
                    continue

                coin_data = best_price_dict[coin]
                historical_data = self.db_manager.fetch_data(coin)
                self.strategy.execute_strategy(
                    coin,
                    coin_data,
                    historical_data,
                    self.api,
                    self.db_manager,
                    best_price_dict  # pass all price data for synergy
                )
            except Exception as e:
                logging.error(f"Error processing strategy for {coin}: {e}", exc_info=True)
