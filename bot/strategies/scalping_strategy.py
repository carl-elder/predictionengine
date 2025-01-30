from .strategy import TradingStrategy
import logging
import pandas as pd

class ScalpingStrategy(TradingStrategy):

    def calculate_moving_averages(self, compiled_data):
        """
        Calculate moving averages and gaps based on latest compiled data.
        """
        df = compiled_data["value_history"]
        if df.empty or len(df) < 15:
            return None, None, None, None

        df['avg_1min'] = df['bid_inclusive_of_sell_spread'].rolling(window=1).mean()
        df['avg_3min'] = df['bid_inclusive_of_sell_spread'].rolling(window=3).mean()
        df['avg_5min'] = df['bid_inclusive_of_sell_spread'].rolling(window=5).mean()
        df['avg_15min'] = df['bid_inclusive_of_sell_spread'].rolling(window=15).mean()

        df.dropna(inplace=True)
        
        latest = df.iloc[-1]
        return latest['avg_1min'], latest['avg_3min'], latest['avg_5min'], latest['avg_15min']

    def determine_gap_category(self, gap_1_3):
        """
        Classifies the trade opportunity into Medium, Large, or Extreme gaps.
        """
        if 0.0001 <= gap_1_3 < 0.0003:
            return "medium"
        elif 0.0003 <= gap_1_3 < 0.0005:
            return "large"
        elif gap_1_3 >= 0.0005:
            return "extreme"
        return None

    def execute_strategy(self, compiled_data):
        """
        Executes trades based on gap-based strategy.
        """
        try:
            avg_1min, avg_3min, avg_5min, avg_15min = self.calculate_moving_averages(compiled_data)
            if avg_1min is None:
                logging.info("Not enough data for moving averages.")
                return

            # Calculate gaps
            gap_1_3 = avg_1min - avg_3min
            gap_3_5 = avg_3min - avg_5min
            gap_5_15 = avg_5min - avg_15min

            # Classify the trade opportunity
            category = self.determine_gap_category(gap_1_3)

            if category:
                coin_data = compiled_data["value_history"]
                coin = coin_data.iloc[-1]["symbol"]
                api = compiled_data["api"]
                best_price_dict = api.get_best_price(coin)

                if self.already_holds_coin(api, coin):
                    logging.info(f"Already holding {coin}, skipping buy.")
                else:
                    self.buy_strategy(coin, best_price_dict, api, category)
            else:
                logging.info("No valid trade opportunity.")

        except Exception as e:
            logging.error(f"Error in scalping strategy execution: {e}", exc_info=True)

    def buy_strategy(self, coin, best_price_dict, api, category):
        """
        Executes a buy order based on gap category.
        """
        try:
            trade_parameters = {
                "medium": {"profit": 1.015, "stop_loss": 0.9925},
                "large": {"profit": 1.03, "stop_loss": 0.9875},
                "extreme": {"profit": 1.05, "stop_loss": 0.98},
            }

            quantity_to_buy = self.calculate_buy_quantity_for_two_percent_allocation(api, coin, best_price_dict)

            if quantity_to_buy > 0:
                ask_price_info = best_price_dict["results"][0]
                adjusted_ask = float(ask_price_info["ask_inclusive_of_buy_spread"])
                api.place_order("buy", coin, adjusted_ask, quantity_to_buy)

                # Set take-profit and stop-loss orders
                profit_target = adjusted_ask * trade_parameters[category]["profit"]
                stop_loss_price = adjusted_ask * trade_parameters[category]["stop_loss"]

                api.place_order("sell", coin, profit_target, quantity_to_buy)
                api.place_order("sell", coin, stop_loss_price, quantity_to_buy, order_config={"stop_price": stop_loss_price})

        except Exception as e:
            logging.error(f"Error executing buy strategy for {coin}: {e}", exc_info=True)
