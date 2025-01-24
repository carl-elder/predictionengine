import logging


class TimestampsManager:
    def __init__(self, connection):
        self.connection = connection

    def get_last_timestamp(self, coin):
        query = "SELECT last_timestamp FROM last_checked WHERE coin = %s"
        cursor = self.connection.cursor()
        cursor.execute(query, (coin,))
        result = cursor.fetchone()
        cursor.close()
        return result[0] if result else None

    def update_last_timestamp(self, coin, timestamp):
        query = """
            INSERT INTO last_checked (coin, last_timestamp)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE last_timestamp = %s
        """
        cursor = self.connection.cursor()
        cursor.execute(query, (coin, timestamp, timestamp))
        self.connection.commit()
        cursor.close()

