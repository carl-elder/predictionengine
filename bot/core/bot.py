import logging
import time

class Bot:
    def __init__(self, symbols, strategy, api, db_manager):
        self.symbols = symbols
        self.strategy = strategy
        self.api = api
        self.db_manager = db_manager

    def run(self):
        for coin in self.symbols:
            logging.info(f"Processing {coin}...")
            try:
                coin_data = self.api.get_best_price(coin)
                if not coin_data or "results" not in coin_data:
                    logging.warning(f"No data for {coin}. Skipping...")
                    continue

                historical_data = self.db_manager.fetch_data(coin)
                self.strategy.execute_strategy(coin, coin_data, historical_data, self.api, self.db_manager)
            except Exception as e:
                logging.error(f"Error processing {coin}: {e}", exc_info=True)

    def execute(self, iterations=5, delay=10):
        for i in range(iterations):
            logging.info(f"Iteration {i + 1} started...")
            self.run()
            time.sleep(delay)
        logging.info("Bot execution completed.")
