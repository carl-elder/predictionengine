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

    def insert_or_update_order(self, table_name, order_data):
            """
            Takes a dictionary representing a single order row and
            inserts or updates it in <coin>_order_history table.
            """
            cursor = self.connection.cursor()
            sql = f"""
                INSERT INTO {table_name}
                (id, timestamp, updated_at, side, state, price, limit_order_configuration, quantity, fee, order_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    updated_at = VALUES(updated_at),
                    state = VALUES(state),
                    price = VALUES(price),
                    limit_order_configuration = VALUES(limit_order_configuration),
                    quantity = VALUES(quantity),
                    fee = VALUES(fee),
                    order_type = VALUES(order_type)
            """

            vals = (
                order_data["id"],
                order_data["timestamp"],
                order_data["updated_at"],
                order_data["side"],
                order_data["state"],
                order_data["price"],
                order_data["limit_order_configuration"],
                order_data["quantity"],
                order_data["fee"],
                order_data["order_type"]
            )
            cursor.execute(sql, vals)
            self.connection.commit()
            cursor.close()

        def get_last_updated_at(self, table_name):
            """
            Returns the latest updated_at timestamp from <coin>_order_history.
            """
            cursor = self.connection.cursor()
            sql = f"SELECT updated_at FROM {table_name} ORDER BY updated_at DESC LIMIT 1"
            cursor.execute(sql)
            row = cursor.fetchone()
            cursor.close()
            return row[0] if row else None
