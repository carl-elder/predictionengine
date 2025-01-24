from .strategy import TradingStrategy  # Adjust this if TradingStrategy is in another module
import logging

class ScalpingStrategy(TradingStrategy):

    def calculate_moving_averages(self, data):
        """
        Calculate short-term, medium-term, and long-term moving averages.
        """
        values = [float(row[1]) for row in data if row[1] is not None]
        short_ma = sum(values[:6]) / 6 if len(values) >= 6 else float('nan')
        medium_ma = sum(values[:30]) / 30 if len(values) >= 30 else float('nan')
        long_ma = sum(values[:48]) / 48 if len(values) >= 48 else float('nan')
        return short_ma, medium_ma, long_ma

    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager, best_price_dict):
        try:
            short_ma, medium_ma, long_ma = self.calculate_moving_averages(historical_data)
            if short_ma > medium_ma * 1.004 > long_ma * 1.003:
                if self.already_holds_coin(api, coin):
                    logging.info(f"Already hold {coin}, skipping buy.")
                else:
                    self.buy_strategy(coin, coin_data, api, best_price_dict)
            else:
                logging.info(f"No uptrend detected for {coin}.")
        except Exception as e:
            logging.error(f"Error in scalping strategy for {coin}: {e}", exc_info=True)

    def buy_strategy(self, coin, coin_data, api, best_price_dict):
        try:
            quantity_to_buy = self.calculate_buy_quantity_for_two_percent_allocation(api, coin, best_price_dict)
            if quantity_to_buy > 0:
                ask_price_info = coin_data["results"][0]
                adjusted_ask = float(ask_price_info["ask_inclusive_of_buy_spread"])
                api.place_order("buy", coin, adjusted_ask, quantity_to_buy)
        except Exception as e:
            logging.error(f"Error executing buy strategy for {coin}: {e}", exc_info=True)
            

