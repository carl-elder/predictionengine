import logging
from datetime import datetime
import json

class Bot:
    """
    1. Initializes with all objects from main.py
    2. Bot is the top-level executor of all high-level logic.
    3. No sibling objects touch each other - everything goes through here.
    4. NOTE: PROBABLY SHOULD MOVE ALL THIS LOGIC FOR BUILDING `coin_data` DICTIONARY TO A NEW CLASS
    """

    def __init__(self, api, db_manager, strategy, config, coin_data, trade_decision):
        """
        :param api: Exchange API object with methods like get_best_price(...)
        :param db_manager: DatabaseManager object managing specialized managers like ValueHistoryManager.
        :param strategy: Instance of ScalpingStrategy (or TradingStrategy with the appropriate child passed).
        :param config: Configuration object for bot parameters.
        """
        self.api = api
        self.db_manager = db_manager
        self.strategy = strategy
        self.config = config
        self.coins = json.loads(self.config.get("DEFAULT", "coins"))
        self.coin_data = coin_data
        self.trade_decision = trade_decision

    # 8. Main execution loop
    def run(self):
        all_coin_data = self.coin_data.compile_data(self.api, self.db_manager, self.config, self.coins)

        if not all_coin_data or "results" not in all_coin_data:
            logging.error("Failed to retrieve valid coin values from API. Exiting bot execution.")
            return

        for coin_data in all_coin_data["results"]:
            try:
                coin_symbol = coin_data["symbol"]
                compiled_data = self.__compile_data(coin_symbol)
                compiled_data["api"] = self.api  # Inject API for orders

                self.strategy.execute_strategy(compiled_data)
            except Exception as e:
                logging.error(f"Error executing strategy for {coin_symbol}: {e}", exc_info=True)

            try:
                last_timestamp = self.db_manager.timestamps.get_last_timestamp(coin_symbol)
                executed_orders = self.api.get_executed_orders(coin_symbol, last_timestamp)

                for order in executed_orders:
                    self.strategy.handle_post_buy_actions(order, self.api)

                    table_name = f"{coin_symbol.replace('-USD', '').lower()}_order_history"
                    self.db_manager.order_history.insert_or_update_order(table_name, order)

                    self.db_manager.timestamps.update_last_timestamp(coin_symbol, order["updated_at"])
            except Exception as e:
                logging.error(f"Error processing executed orders for {coin_symbol}: {e}", exc_info=True)
