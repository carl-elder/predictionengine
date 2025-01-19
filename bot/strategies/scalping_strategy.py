import logging
from .strategy import TradingStrategy


class ScalpingStrategy(TradingStrategy):

    def __init__(self, profit_threshold=0.02, loss_threshold=0.01):
        """
        Initialize ScalpingStrategy with profit and loss thresholds.
        :param profit_threshold: Percent gain to trigger a limit order (default: 2%).
        :param loss_threshold: Percent loss to trigger a stop-loss order (default: 1%).
        """
        self.profit_threshold = profit_threshold
        self.loss_threshold = loss_threshold
        
    @staticmethod
    def calculate_moving_averages(data):
        """
        Calculate short-term, medium-term, and long-term moving averages.
        """
        values = [float(row[1]) for row in data if row[1] is not None]
        short_ma = sum(values[:6]) / 6 if len(values) >= 6 else float('nan')
        medium_ma = sum(values[:30]) / 30 if len(values) >= 30 else float('nan')
        long_ma = sum(values[:48]) / 48 if len(values) >= 48 else float('nan')
        return short_ma, medium_ma, long_ma

    @staticmethod
    def already_holds_coin(api, coin) -> bool:
        """
        Returns True if the user already holds any of 'coin' (e.g., "BTC-USD").
        """
        try:
            holdings_data = api.get_holdings()
            all_holdings_results = holdings_data.get("results", [])
            asset_code = coin.split("-")[0]  # Extract asset code (e.g., "BTC" from "BTC-USD")

            for holding in all_holdings_results:
                if holding["asset_code"] == asset_code and float(holding["total_quantity"]) > 0:
                    return True
            return False
        except Exception as e:
            logging.error(f"Error checking holdings for {coin}: {e}", exc_info=True)
            return False


    def buy_strategy(self, coin, coin_data, api, best_price_dict):
        """
        Executes the buy logic for the scalping strategy.
        """
        try:
            # Compute quantity to buy
            quantity_to_buy = self.calculate_buy_quantity_for_two_percent_allocation(
                api, coin, best_price_dict
            )
            if quantity_to_buy > 0:
                ask_price_info = coin_data["results"][0]
                adjusted_ask = float(ask_price_info["ask_inclusive_of_buy_spread"])
                # Place the buy order
                api.place_order("buy", coin, adjusted_ask, quantity_to_buy)
                logging.info(
                    f"BUY {coin}: 2% allocation => {quantity_to_buy:.6f} at {adjusted_ask:.4f}"
                )
            else:
                logging.warning(f"Skipped buy for {coin}: calculated quantity was 0 or invalid.")
        except Exception as e:
            logging.error(f"Error executing buy strategy for {coin}: {e}", exc_info=True)

    def sell_strategy(self, executed_order, api):
        """
        Executes the post-buy sell strategy: places a limit order and a stop-loss order.
        """
        try:
            buy_price = float(executed_order["price"])
            symbol = executed_order["symbol"]
            quantity = float(executed_order["quantity"])

            # 1) Place a limit order for profit-taking
            limit_price = buy_price * (1 + self.profit_threshold)
            api.place_order("sell", symbol, limit_price, quantity)
            logging.info(f"Limit order placed for {symbol} at {limit_price:.2f} (Profit: {self.profit_threshold*100}%).")

            # 2) Place a stop-loss order to minimize losses
            stop_loss_price = buy_price * (1 - self.loss_threshold)
            stop_loss_config = {"stop_price": stop_loss_price, "asset_quantity": quantity}
            api.place_order("sell", symbol, stop_loss_price, quantity, stop_loss_config)
            logging.info(f"Stop-loss order placed for {symbol} at {stop_loss_price:.2f} (Loss: {self.loss_threshold*100}%).")

        except Exception as e:
            logging.error(f"Error executing sell strategy for {symbol}: {e}", exc_info=True)

    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager, best_price_dict):
        """
        Buys 2% of total portfolio in `coin` if short, medium, and long MAs
        indicate an uptrend, using pre-fetched coin_data and best_price_dict.
        """
        try:
            short_ma, medium_ma, long_ma = self.calculate_moving_averages(historical_data)

            # Check for an uptrend
            if short_ma > medium_ma * 1.004 > long_ma * 1.003:
                # Skip buy logic if already holding the coin
                if self.already_holds_coin(api, coin):
                    logging.info(f"Already hold {coin}, skipping additional buy.")
                else:
                    logging.info(f"Uptrend detected for {coin}. Executing buy strategy.")
                    self.buy_strategy(coin, coin_data, api, best_price_dict)
            else:
                logging.info(f"No uptrend detected for {coin}. No action taken.")
        except Exception as e:
            logging.error(f"Error executing scalping strategy for {coin}: {e}", exc_info=True)

    
