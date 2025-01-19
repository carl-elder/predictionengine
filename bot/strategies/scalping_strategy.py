import logging
from .strategy import TradingStrategy

class ScalpingStrategy(TradingStrategy):
    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager, best_price_dict):
        """
        Buys 2% of total portfolio in `coin` if short, medium, and long MAs
        indicate an uptrend, using pre-fetched coin_data and best_price_dict.
        """
        try:
            short_ma, medium_ma, long_ma = self.calculate_moving_averages(historical_data)

            if short_ma > medium_ma * 1.004 > long_ma * 1.003:
                # 1) Check if we already hold any of this coin. If so, skip the buy logic.
                if self.already_holds_coin(api, coin):
                    logging.info(f"Already hold {coin}, skipping additional buy.")
                    return

                # 2) Compute quantity to buy
                quantity_to_buy = self.calculate_buy_quantity_for_two_percent_allocation(
                    api, coin, best_price_dict
                )

                if quantity_to_buy > 0:
                    # 4) We already have coin_data from best_price_dict
                    # So no need to call get_best_price again
                    if coin_data and coin_data.get("results"):
                        ask_price_info = coin_data["results"][0]
                        adjusted_ask = float(ask_price_info["ask_inclusive_of_buy_spread"])

                        # 5) Place buy
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
        data is the result of db_manager.fetch_data(coin),
        typically a list of (timestamp, price, ask_inclusive_of_buy_spread, bid_inclusive_of_sell_spread).
        We'll assume the second value in each row is 'price'.
        """
        values = [float(row[1]) for row in data if row[1] is not None]
        short_ma = sum(values[:6]) / 6 if len(values) >= 6 else float('nan')
        medium_ma = sum(values[:30]) / 30 if len(values) >= 30 else float('nan')
        long_ma = sum(values[:48]) / 48 if len(values) >= 48 else float('nan')
        return short_ma, medium_ma, long_ma

    @staticmethod
    def calculate_buy_quantity_for_two_percent_allocation(api, target_coin_symbol, best_price_dict) -> float:
        """
        Calculate how many units of `target_coin_symbol` to buy to equal 2% of
        total portfolio (all holdings + buying power). We now rely on best_price_dict
        to avoid multiple calls to get_best_price for each holding.
        """
        account_data = api.get_account()  # {"buying_power": "..."}
        buying_power = float(account_data["buying_power"])

        holdings_data = api.get_holdings()  # all holdings
        all_holdings_results = holdings_data.get("results", [])

        # Sum up the total USD value of each holding using pre-fetched best_price_dict
        total_holdings_value_usd = 0.0
        for holding in all_holdings_results:
            coin_code = holding["asset_code"]  # e.g. "BTC"
            quantity_held = float(holding["total_quantity"])
            if quantity_held > 0:
                pair_symbol = f"{coin_code}-USD"
                holding_price_data = best_price_dict.get(pair_symbol)
                if holding_price_data and holding_price_data.get("results"):
                    price_info = holding_price_data["results"][0]
                    adjusted_ask_price = float(price_info["ask_inclusive_of_buy_spread"])
                    total_holdings_value_usd += quantity_held * adjusted_ask_price

        # 2% of (buying_power + total_holdings_value_usd)
        total_portfolio_value_usd = total_holdings_value_usd + buying_power
        two_percent_dollars = 0.02 * total_portfolio_value_usd

        # If target_coin_symbol is "BTC" or "BTC-USD", unify
        if "-" in target_coin_symbol:
            pair_symbol = target_coin_symbol
        else:
            pair_symbol = f"{target_coin_symbol}-USD"

        # Use pre-fetched price for the target coin
        best_prices_target = best_price_dict.get(pair_symbol)
        adjusted_ask_target = 0.0
        if best_prices_target and best_prices_target.get("results"):
            price_info_target = best_prices_target["results"][0]
            adjusted_ask_target = float(price_info_target["ask_inclusive_of_buy_spread"])

        # Final quantity
        if adjusted_ask_target > 0:
            quantity_to_buy = two_percent_dollars / adjusted_ask_target
        else:
            quantity_to_buy = 0.0

        return quantity_to_buy

    @staticmethod
    def already_holds_coin(api, coin) -> bool:
        """
        Returns True if the user already holds any of 'coin' (e.g., "BTC-USD").
        """
        holdings_data = api.get_holdings()
        all_holdings_results = holdings_data.get("results", [])

        # The asset_code might be "BTC" if coin is "BTC-USD"
        asset_code = coin.split("-")[0]  # "BTC" from "BTC-USD"

        for holding in all_holdings_results:
            if holding["asset_code"] == asset_code:
                if float(holding["total_quantity"]) > 0:
                    return True

        return False
