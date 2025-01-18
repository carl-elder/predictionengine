class DatabaseManager:
    def __init__(self, connection):
        self.connection = connection

    def insert_data(self, coin, timestamp, value):
        cursor = self.connection.cursor()
        table_name = f"{coin.replace('-USD', '').lower()}_value_history"
        sql = f"INSERT INTO {table_name} (timestamp, value) VALUES (%s, %s)"
        cursor.execute(sql, (timestamp, value))
        self.connection.commit()
        cursor.close()

    def fetch_data(self, coin):
        cursor = self.connection.cursor()
        table_name = f"{coin.replace('-USD', '').lower()}_value_history"
        sql = f"SELECT timestamp, value FROM {table_name} ORDER BY timestamp DESC LIMIT 48"
        cursor.execute(sql)
        data = cursor.fetchall()
        cursor.close()
        return data

