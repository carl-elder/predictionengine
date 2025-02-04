import logging
import numpy as np
from decimal import Decimal
from bot.strategies.strategy import TradingStrategy

class ScalpingStrategy(TradingStrategy):
    def execute_strategy(self, compiled_data):
        """
        Executes the scalping strategy using compiled market data.
        """
        try:
            api = compiled_data["api"]
            value_history = compiled_data["value_history"]
            holdings = compiled_data["holdings"]
            buying_power = Decimal(compiled_data.get("buying_power", 0.0))
            coin = compiled_data.get("symbol", None)
            price_data = compiled_data.get("price_data", None)

            if not coin:
                logging.warning("No valid coin symbol found in compiled_data.")
                return

            # Ensure price data is valid
            if not price_data or not isinstance(price_data, dict):
                logging.error(f"Missing price data for {coin}. API response might be invalid: {price_data}")
                return

            bid_price = Decimal(price_data.get("bid_price", 0))
            ask_price = Decimal(price_data.get("ask_price", 0))

            if bid_price == 0 or ask_price == 0:
                logging.warning(f"Skipping {coin}, bid/ask prices are invalid: Bid={bid_price}, Ask={ask_price}")
                return

            logging.debug(f"Latest prices for {coin}: Bid={bid_price}, Ask={ask_price}")

            # Ensure value history is available
            if value_history is None or value_history.empty:
                logging.warning(f"Insufficient value history for {coin}")
                return

            # Compute gap values dynamically
            if "gap_1_3" not in value_history.columns:
                logging.warning("Gaps missing, computing them on the fly.")
                value_history["gap_1_3"] = value_history["avg_3min"] - value_history["avg_1min"]
                value_history["gap_3_5"] = value_history["avg_5min"] - value_history["avg_3min"]
                value_history["gap_5_15"] = value_history["avg_15min"] - value_history["avg_5min"]

            latest_data = value_history.iloc[-1]
            gap_1_3 = Decimal(latest_data["gap_1_3"])
            gap_3_5 = Decimal(latest_data["gap_3_5"])
            gap_5_15 = Decimal(latest_data["gap_5_15"])

            # Compute probability of a profitable trade
            expected_return = self.estimate_trade_probability(gap_1_3, gap_3_5, gap_5_15)

            # Determine trade size based on expected return
            trade_quantity = self.determine_trade_size(buying_power, ask_price, expected_return)

            # **SELL STRATEGY**: Take profit if price increased > 1%
            if self.already_holds_coin(holdings, coin):
                last_purchase_price = self.get_last_buy_price(holdings, coin)
                if last_purchase_price:
                    if bid_price >= last_purchase_price * Decimal("1.01"):  # Take profit at 1% gain
                        self.execute_trade(api, coin, bid_price, trade_quantity, "sell")
                        return
                    elif bid_price <= last_purchase_price * Decimal("0.99"):  # Stop-loss at 1% loss
                        self.execute_trade(api, coin, bid_price, trade_quantity, "sell")
                        return
                logging.info(f"Skipping trade: Already holding {coin} and conditions not met.")
                return

            # **BUY STRATEGY**: Execute only if expected return is favorable
            if trade_quantity > 0:
                self.execute_trade(api, coin, ask_price, trade_quantity, "buy")
            else:
                logging.info(f"No valid trade opportunity for {coin}. Probability not favorable.")

        except Exception as e:
            logging.error(f"Error in scalping strategy execution: {e}", exc_info=True)

    def already_holds_coin(self, holdings, coin):
        """
        Check if the user already holds this coin.
        """
        try:
            for holding in holdings:
                if holding.get("asset_code") == coin.replace("-USD", ""):
                    return True
            return False
        except Exception as e:
            logging.error(f"Error checking holdings for {coin}: {e}", exc_info=True)
            return False

    def get_last_buy_price(self, holdings, coin):
        """
        Get the last recorded purchase price for the coin.
        """
        try:
            for holding in holdings:
                if holding.get("asset_code") == coin.replace("-USD", ""):
                    return Decimal(holding.get("last_purchase_price", 0.0))
            return None
        except Exception as e:
            logging.error(f"Error fetching last buy price for {coin}: {e}", exc_info=True)
            return None

    def estimate_trade_probability(self, gap_1_3, gap_3_5, gap_5_15):
        """
        Estimate the probability of a price increase based on historical gaps.
        """
        probability = 0.0
        if gap_1_3 > Decimal("0.005") and gap_3_5 > Decimal("0.003") and gap_5_15 > Decimal("0.002"):
            probability = 0.75  # Strong trend continuation expected
        elif gap_1_3 > Decimal("0.003") and gap_3_5 > Decimal("0.002") and gap_5_15 > Decimal("0.001"):
            probability = 0.60  # Medium trend continuation
        elif gap_1_3 > Decimal("0.002") and gap_3_5 > Decimal("0.001"):
            probability = 0.45  # Weak trend
        else:
            probability = 0.25  # No trade (not worth the risk)

        return probability

    def determine_trade_size(self, buying_power, ask_price, probability):
        """
        Determine the optimal trade size based on probability.
        """
        min_trade_prob = Decimal("0.50")

        if probability > min_trade_prob:
            risk_factor = probability
            trade_size = buying_power * risk_factor
            trade_quantity = trade_size / ask_price  # Convert to coin quantity

            return trade_quantity
        else:
            return Decimal("0")  # Do not trade if probability is too low

    def execute_trade(self, api, coin, price, quantity, order_type):
        """
        Execute a buy/sell order.
        """
        try:
            order_response = api.place_order(
                order_type=order_type,
                coin=coin,
                price=float(price),
                quantity=float(quantity)
            )
            if order_response:
                logging.info(f"Trade executed: {order_type.capitalize()} {quantity} {coin} at {price}")
            else:
                logging.warning(f"Trade execution failed for {coin}")
        except Exception as e:
            logging.error(f"Error executing trade for {coin}: {e}", exc_info=True)
