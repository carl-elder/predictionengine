from abc import ABC, abstractmethod

class TradingStrategy(ABC):
    @abstractmethod
    def execute_strategy(self, coin, coin_data, historical_data, api, db_manager):
        """
        Execute the trading strategy for a given coin.
        """
        pass

