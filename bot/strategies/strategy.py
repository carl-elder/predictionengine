import logging
from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    @abstractmethod
    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager, best_price_dict):
        pass

    @staticmethod
    def already_holds_coin(api, coin) -> bool:
        holdings_data = api.get_holdings()
        all_holdings_results = holdings_data.get("results", [])
        asset_code = coin.split("-")[0]  # Extract asset code (e.g., "BTC" from "BTC-USD")
        for holding in all_holdings_results:
            if holding["asset_code"] == asset_code and float(holding["total_quantity"]) > 0:
                return True
        return False

    def handle_post_buy_actions(self, executed_order, api, profit_threshold=0.02, loss_threshold=0.01):
        try:
            buy_price = float(executed_order["average_price"])
            symbol = executed_order["symbol"]
            quantity = float(executed_order["filled_asset_quantity"])

            # Place a limit order for profit-taking
            limit_price = buy_price * (1 + profit_threshold)
            api.place_order("sell", symbol, limit_price, quantity)

            # Place a stop-loss order to minimize losses
            stop_loss_price = buy_price * (1 - loss_threshold)
            stop_loss_config = {"stop_price": stop_loss_price, "asset_quantity": quantity}
            api.place_order("sell", symbol, stop_loss_price, quantity, stop_loss_config)
        except Exception as e:
            logging.error(f"Error handling post-buy actions: {e}", exc_info=True)
