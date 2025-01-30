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

    
