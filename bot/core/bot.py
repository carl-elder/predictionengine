import logging
from datetime import datetime

class Bot:

    """
    1. initialize with all objects from main.py
    2. Bot is the top level executor of all high-level logic.
    3. No sibling objects touch each other - everything goes through here.
    """
    
    def __init__(self, coins, api, db_manager, strategy):
        """
        :param coins: list of coins, e.g. ["BTC-USD", "ETH-USD", ...]
        :param api: an object with methods like get_best_price(...)
        :param db_manager: DatabaseManager object managing specialized managers like ValueHistoryManager.
        :param strategy: instance of ScalpingStrategy - soon to be TradingStrategy with appropriate child passed to it.
        """
        self.coins = coins
        self.api = api
        self.db_manager = db_manager
        self.strategy = strategy
    
    # 1. get current value OF ALL COINS from API (1st API call)
    def get_coin_values() -> dict:
        coin_data = self.api.get_best_price(self.coins)
        return coin_data
    
    # 2. set current values in DB
    def set_coin_values(coin_data) -> bool:
        try:
            self.db_manager.value_history_manager.insert_data(coin_data)
            return True
        except Exception as e:
            logging.error(f"Error setting coin values: {e}", exc_info=True)
            return False
            
    # 3. get most recent n values from DB
    def get_value_history(self.coins) -> dict:
        value_history = self.db_manager.value_history_manager.get_value_history(self.coins)
        return value_history
    
    # 4. get current holdings from API (2nd API call)
    def get_holdings() -> dict:
        holdings = self.api.get_holdings()
        return holdings
    
    # 5. get current buying power from API (3rd API call)
    def get_buying_power() -> dict:
        buying_power = self.api.get_buying_power()
        return buying_power
    
    # 6. Alter buying power by adding sum of holdings value and buying power
    
    def true_buying_power(self, holdings, coin_data) -> float:
    """
    Calculate the true buying power as 2% of the total portfolio value,
    which includes cash and the value of current holdings.
    """
    # Fetch cash balance
    try:
        cash = float(self.get_buying_power())
    except Exception as e:
        logging.error(f"Error fetching buying power: {e}", exc_info=True)
        cash = 0.0

    # Calculate the total value of holdings
    total_holdings_value_usd = 0.0
    for holding in holdings:
        try:
            coin_code = holding["asset_code"]  # e.g., "BTC"
            quantity_held = float(holding["total_quantity"])
            if quantity_held > 0:
                pair_symbol = f"{coin_code}-USD"
                # Find the current price in coin_data
                if pair_symbol in coin_data:
                    adjusted_ask_price = float(coin_data[pair_symbol]["ask_inclusive_of_buy_spread"])
                    total_holdings_value_usd += quantity_held * adjusted_ask_price
        except Exception as e:
            logging.warning(f"Error processing holding {holding}: {e}", exc_info=True)

    # Total portfolio value = cash + holdings value
    total_portfolio_value_usd = cash + total_holdings_value_usd

    # Calculate 2% of the portfolio value
    buying_power_percentage = 0.02  # Adjust as needed
    true_buying_power = total_portfolio_value_usd * buying_power_percentage
    return true_buying_power

    
    # 7. compile all for running
    def compile_data(coin_data) -> dict:
        compiled_data = {}
        compiled_data['value_history'] = get_value_history(self.coins)
        compiled_data['holdings'] = get_holdings()
        compiled_data['buying_power'] = true_buying_power(compiled_data['holdings'], coin_data)
        return compiled_data
    
    # 8. run (if all prior are collected)
    def run(self):
        if set_coin_values(get_coin_values(self.coins)):
            continue
        else:
            logging.error("Failed to set coin_values in Bot. Exiting.")
            return
        
        compiled_data = compile_data(coin_data)
        
        # 1. The good stuff. Loop through all coins performing the primary functions of this program.
        for coin in self.coins:
            try:
                self.strategy.execute_strategy(compiled_data)
            except Exception as e:
                logging.error(f"Error executing strategy for {coin}: {e}", exc_info=True)
                return
                
        try:
            last_timestamp = self.db_manager.timestamps.get_last_timestamp(coin)
            executed_orders = self.api.get_executed_orders(coin, last_timestamp)

            for order in executed_orders:
                self.strategy.handle_post_buy_actions(order, self.api)

                # Insert or update the order in the order history table
                table_name = f"{coin.replace('-USD', '').lower()}_order_history"
                self.db_manager.order_history.insert_or_update_order(table_name, order)

                # Update the last timestamp for the coin
                self.db_manager.timestamps.update_last_timestamp(coin, order["updated_at"])
        except Exception as e:
            logging.error(f"Error processing executed orders for {coin}: {e}", exc_info=True)
