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

    def __init__(self, api, db_manager, strategy, config):
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

    # 1. Get current bid/ask values for all coins from API (1st API call)
    def __get_coin_values(self) -> dict:
        coin_data = self.api.get_best_price(self.coins)
        return coin_data

    # 2. Store current values in the database
    def __set_coin_values(self, all_coin_data) -> bool:
        try:
            self.db_manager.value_history.insert_data(all_coin_data)
            return True
        except Exception as e:
            logging.error(f"Error setting coin values: {e}", exc_info=True)
            return False

    # 3. Get the most recent `n` values from the database
    def __get_value_history(self, coin_symbol, length) -> dict:
        return self.db_manager.value_history.get_value_history(coin_symbol, length)

    # 4. Get current holdings from API (2nd API call)
    def __get_holdings(self) -> dict:
        holdings = self.api.get_holdings()
        if not holdings:
            logging.warning("No holdings data found.")
        return holdings

    # 5. Get current buying power from API (3rd API call)
    def __get_buying_power(self) -> float:
        buying_power = self.api.get_account()
        if not buying_power:
            logging.error("Error fetching buying power. API returned None.")
            return 0.0
        return float(buying_power)

    # 6. Compute "true buying power" by including portfolio holdings
    def __true_buying_power(self, holdings, coin_symbol) -> float:
        """
        Calculate true buying power by adding the total holdings value in USD to cash balance.
        """
        cash = self.__get_buying_power()
        total_holdings_value_usd = 0.0

        if isinstance(holdings, dict):
            holdings_list = holdings.get("results", [])
        else:
            holdings_list = holdings

        for holding in holdings_list:
            asset_code = holding["asset_code"]
            quantity_held = float(holding["total_quantity"])

            if quantity_held > 0:
                pair_symbol = f"{asset_code}-USD"
                price_data = self.api.get_best_price([pair_symbol])

                if price_data and "results" in price_data and price_data["results"]:
                    price_info = next((item for item in price_data["results"] if item["symbol"] == pair_symbol), None)
                    if price_info:
                        adjusted_ask_price = float(price_info["ask_inclusive_of_buy_spread"])
                        total_holdings_value_usd += quantity_held * adjusted_ask_price

        total_portfolio_value_usd = total_holdings_value_usd + cash
        allocation = 0.02 * total_portfolio_value_usd  # Allocates 2% of total portfolio value

        return allocation

    # 7. Compile data necessary for strategy execution
    def __compile_data(self, coin_symbol) -> dict:
        compiled_data = {
            "symbol": coin_symbol,
            "value_history": self.__get_value_history(coin_symbol, self.config.get("DEFAULT", "coin_history_length")),
            "holdings": self.__get_holdings(),
        }
        compiled_data["buying_power"] = self.__true_buying_power(compiled_data["holdings"], coin_symbol)

        # Fetch bid/ask prices (previously done multiple times, now centralized)
        price_data = self.api.get_best_price([coin_symbol])
        if price_data and "results" in price_data and price_data["results"]:
            price_info = next((item for item in price_data["results"] if item["symbol"] == coin_symbol), None)
            if price_info:
                compiled_data["price_data"] = {
                    "bid_price": price_info["bid_inclusive_of_sell_spread"],
                    "ask_price": price_info["ask_inclusive_of_buy_spread"]
                }
            else:
                logging.warning(f"No price data found for {coin_symbol}.")
        else:
            logging.warning(f"Invalid price data response for {coin_symbol}: {price_data}")
            compiled_data["price_data"] = None

        return compiled_data

    # 8. Main execution loop
    def run(self):
        all_coin_data = self.__get_coin_values()

        if not all_coin_data or "results" not in all_coin_data:
            logging.error("Failed to retrieve valid coin values from API. Exiting bot execution.")
            return

        if not self.__set_coin_values(all_coin_data):
            logging.error("Failed to store coin values in database. Exiting bot execution.")
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
