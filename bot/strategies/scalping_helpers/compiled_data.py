class ScalpingData:
    def __init__(self, api, db_manager, config, coins):
        self.api = api
        self.db_manager = db_manager
        self.config = config
        self.coins = coins
        return true

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
    def compile_data(self, coin_symbol) -> dict:
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