import logging
from .strategy import TradingStrategy

class ScalpingStrategy(TradingStrategy):
    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager):
        """
        Execute the scalping strategy by checking moving averages
        and placing buy or sell orders accordingly.
        """
        try:
            short_ma, medium_ma, long_ma = self.calculate_moving_averages(historical_data)

            if short_ma > medium_ma * 1.0025 > long_ma * 1.001:
                # Uptrend detected
                holdings = api.get_holdings(coin)

                # Check if holdings data is valid
                holding_quantity = 0
                if holdings and holdings.get("results"):
                    holding_quantity = float(holdings["results"][0]["total_quantity"])

                if holding_quantity == 0:
                    price = float(coin_data["results"][0]["price"])
                    quantity = 10  # Example quantity
                    api.place_order("buy", coin, price, quantity)
                    logging.info(f"Placed buy order for {coin} at {price}")
                else:
                    price = float(coin_data["results"][0]["price"]) * 1.02
                    api.place_order("sell", coin, price, holding_quantity)
                    logging.info(f"Placed sell order for {coin} at {price}")
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
