import logging
from datetime import datetime
import json

class Bot:

    """
    1. initialize with all objects from main.py
    2. Bot is the top level executor of all high-level logic.
    3. No sibling objects touch each other - everything goes through here.
    4. NOTE: PROBABLY SHOULD TO MOVE ALL THIS LOGIC FOR BUILDING coin_data DICTIONARY TO A NEW CLASS
    """
    
    def __init__(self, api, db_manager, strategy, config):
        """
        :param coins: list of coins, e.g. ["BTC-USD", "ETH-USD", ...]
        :param api: an object with methods like get_best_price(...)
        :param db_manager: DatabaseManager object managing specialized managers like ValueHistoryManager.
        :param strategy: instance of ScalpingStrategy - soon to be TradingStrategy with appropriate child passed to it.
        """
        self.api = api
        self.db_manager = db_manager
        self.strategy = strategy
        self.config = config
        self.coins = json.loads(self.config.get("DEFAULT","coins"))
    
    # 1. get current value OF ALL COINS from API (1st API call)
    def __get_coin_values(self) -> dict:
        coin_data = self.api.get_best_price(self.coins)
        return coin_data
    
    # 2. set current values in DB
    def __set_coin_values(self, all_coin_data) -> bool:
        try:
            self.db_manager.value_history.insert_data(all_coin_data)
            return True
        except Exception as e:
            logging.error(f"Error setting coin values: {e}", exc_info=True)
            return False
            
    # 3. get most recent n values from DB
    def __get_value_history(self, coin_data, length) -> dict:
        value_history = self.db_manager.value_history.get_value_history(coin_data, length)
        return value_history
    
    # 4. get current holdings from API (2nd API call)
    def __get_holdings(self) -> dict:
        holdings = self.api.get_holdings()
        return holdings
    
    # 5. get current buying power from API (3rd API call)
    def __get_buying_power(self) -> dict:
        buying_power = self.api.get_account()
        return buying_power
    
    # 6. Alter buying power by adding sum of holdings value and buying power
    def __true_buying_power(self, holdings, coin_data) -> float:
        """
        Calculate true buying power by adding the total holdings value in USD to cash balance.
        """
        # Fetch cash balance
        account_data = self.api.get_account()
        cash = float(account_data.get("buying_power", 0))  # Ensure fallback default

        # Ensure `holdings` is a dictionary, then extract results list
        if isinstance(holdings, dict):
            holdings_list = holdings.get("results", [])  # Extract list from "results"
        else:
            holdings_list = holdings  # Assume it's already a list

        total_holdings_value_usd = 0.0

        for holding in holdings_list:
            asset_code = holding["asset_code"]  # Example: "BTC"
            quantity_held = float(holding["total_quantity"])

            if quantity_held > 0:
                pair_symbol = f"{asset_code}-USD"  # Example: "BTC-USD"
                best_price = self.api.get_best_price(pair_symbol)

                if best_price and "results" in best_price and best_price["results"]:
                    price_info = best_price["results"][0]
                    adjusted_ask_price = float(price_info["ask_inclusive_of_buy_spread"])
                    total_holdings_value_usd += quantity_held * adjusted_ask_price

        # Calculate 2% allocation
        total_portfolio_value_usd = total_holdings_value_usd + cash
        allocation = 0.02 * total_portfolio_value_usd  # Adjusted percentage of total value

        return allocation

    
    # 7. compile all for running
    def __compile_data(self, coin_data) -> dict:
        compiled_data = {}
        compiled_data['value_history'] = self.__get_value_history(coin_data, self.config.get("DEFAULT", "coin_history_length"))
        compiled_data['holdings'] = self.__get_holdings()
        compiled_data['buying_power'] = self.__true_buying_power(compiled_data['holdings'], coin_data)
        return compiled_data
    
    # 8. run (if all prior are collected)
    def run(self):
        all_coin_data = self.__get_coin_values()

        if not self.__set_coin_values(all_coin_data):
            logging.error("Failed to set coin_values in Bot. Exiting.")
            return

        for coin_data in all_coin_data:
            try:
                compiled_data = self.__compile_data(coin_data)
                compiled_data["api"] = self.api  # Inject API for orders

                self.strategy.execute_strategy(compiled_data)
            except Exception as e:
                logging.error(f"Error executing strategy for {coin_data['symbol']}: {e}", exc_info=True)

            try:
                last_timestamp = self.db_manager.timestamps.get_last_timestamp(coin_data["symbol"])
                executed_orders = self.api.get_executed_orders(coin_data["symbol"], last_timestamp)

                for order in executed_orders:
                    self.strategy.handle_post_buy_actions(order, self.api)

                    table_name = f"{coin_data['symbol'].replace('-USD', '').lower()}_order_history"
                    self.db_manager.order_history.insert_or_update_order(table_name, order)

                    self.db_manager.timestamps.update_last_timestamp(coin_data["symbol"], order["updated_at"])
            except Exception as e:
                logging.error(f"Error processing executed orders for {coin_data['symbol']}: {e}", exc_info=True)
