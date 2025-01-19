import logging
from .strategy import TradingStrategy

class ScalpingStrategy(TradingStrategy):
    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager):
        """
        Example scalping strategy that buys 2% of total portfolio in `coin`
        if short, medium, and long MAs indicate an uptrend.
        """
        try:
            short_ma, medium_ma, long_ma = self.calculate_moving_averages(historical_data)

            # Uptrend check (example logic)
            if short_ma > medium_ma * 1.0025 > long_ma * 1.001:
                # If conditions are met, compute the 2% buy quantity
                quantity_to_buy = self.calculate_buy_quantity_for_two_percent_allocation(api, coin)

                if quantity_to_buy > 0:
                    # 1) We also need the final price to place the order
                    best_prices = api.get_best_bid_ask(coin + "-USD")
                    if best_prices and best_prices.get("results"):
                        ask_price_info = best_prices["results"][0]
                        adjusted_ask = float(ask_price_info["ask_inclusive_of_buy_spread"])

                        # 2) Place the buy order
                        api.place_order("buy", coin, adjusted_ask, quantity_to_buy)
                        logging.info(
                            f"BUY {coin}: 2% allocation => {quantity_to_buy:.6f} at {adjusted_ask:.4f}"
                        )

                else:
                    logging.warning(
                        f"Skipped buy for {coin}: calculated quantity was 0 or invalid."
                    )

            else:
                logging.info(f"No uptrend detected for {coin}. Doing nothing.")

        except Exception as e:
            logging.error(f"Error in scalping strategy for {coin}: {e}")

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
    def calculate_buy_quantity_for_two_percent_allocation(api, target_coin_symbol: str) -> float:
        """
        Calculate how many units of `target_coin_symbol` should be bought so that
        it equals 2% of the total portfolio value (all holdings + buying power).
        """
        account_data = api.get_account()  # {"buying_power": "..."}
        buying_power = float(account_data["buying_power"])

        holdings_data = api.get_holdings()  # all holdings
        all_holdings_results = holdings_data.get("results", [])

        total_holdings_value_usd = 0.0
        for holding in all_holdings_results:
            coin_code = holding["asset_code"]  # e.g. "BTC"
            quantity_held = float(holding["total_quantity"])
            if quantity_held > 0:
                pair_symbol = coin_code + "-USD"
                best_prices = api.get_best_bid_ask(pair_symbol)
                if best_prices and best_prices.get("results"):
                    price_info = best_prices["results"][0]
                    adjusted_ask_price = float(price_info["ask_inclusive_of_buy_spread"])
                    total_holdings_value_usd += quantity_held * adjusted_ask_price

        total_portfolio_value_usd = total_holdings_value_usd + buying_power
        two_percent_dollars = 0.02 * total_portfolio_value_usd

        if "-" in target_coin_symbol:
            pair_symbol = target_coin_symbol
        else:
            pair_symbol = target_coin_symbol + "-USD"

        best_prices_target = api.get_best_bid_ask(pair_symbol)
        adjusted_ask_target = 0.0
        if best_prices_target and best_prices_target.get("results"):
            price_info_target = best_prices_target["results"][0]
            adjusted_ask_target = float(price_info_target["ask_inclusive_of_buy_spread"])

        if adjusted_ask_target > 0:
            quantity_to_buy = two_percent_dollars / adjusted_ask_target
        else:
            quantity_to_buy = 0.0

        return quantity_to_buy
