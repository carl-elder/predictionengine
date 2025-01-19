from .value_history_manager import ValueHistoryManager
from .order_history_manager import OrderHistoryManager
from .timestamps_manager import TimestampsManager


class DatabaseManager:
    def __init__(self, connection):
        """
        Initialize DatabaseManager with a shared database connection
        and instantiate specialized managers.
        """
        self.connection = connection
        self.value_history = ValueHistoryManager(connection)
        self.order_history = OrderHistoryManager(connection)
        self.timestamps = TimestampsManager(connection)

    def close_connection(self):
        """
        Close the database connection.
        """
        if self.connection:
            self.connection.close()
