import logging
import json


class OrderHistoryManager:
    def __init__(self, connection):
        self.connection = connection

    def insert_or_update_order(self, table_name, order_data):
        """
        Insert or update an order in the <coin>_order_history table.
        """
        try:
            # Extract data with defaults
            id = order_data.get("id", "N/A")
            timestamp = order_data.get("created_at", None)
            updated_at = order_data.get("updated_at", None)
            side = order_data.get("side", "N/A")
            state = order_data.get("state", "N/A")
            price = float(order_data.get("average_price", 0.0))
            quantity = float(order_data.get("filled_asset_quantity", 0.0))

            # Dynamically handle configurations
            limit_config = json.dumps(order_data.get("limit_order_config", {}))
            stop_loss_config = json.dumps(order_data.get("stop_loss_order_config", {}))
            stop_limit_config = json.dumps(order_data.get("stop_limit_order_config", {}))

            # SQL Query
            sql = f"""
                INSERT INTO {table_name}
                (id, timestamp, updated_at, side, state, price, quantity,
                 limit_order_configuration, stop_loss_order_configuration, stop_limit_order_configuration)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    updated_at = VALUES(updated_at),
                    state = VALUES(state),
                    price = VALUES(price),
                    quantity = VALUES(quantity),
                    limit_order_configuration = VALUES(limit_order_configuration),
                    stop_loss_order_configuration = VALUES(stop_loss_order_configuration),
                    stop_limit_order_configuration = VALUES(stop_limit_order_configuration);
            """

            # Values for the SQL query
            values = (
                id, timestamp, updated_at, side, state, price, quantity,
                limit_config, stop_loss_config, stop_limit_config
            )

            # Execute the query
            cursor = self.connection.cursor()
            cursor.execute(sql, values)
            self.connection.commit()
            cursor.close()

        except KeyError as missing_field:
            logging.error(f"Order data missing required field '{missing_field}': {order_data}")
        except Exception as e:
            logging.error(f"Error inserting/updating order: {e}", exc_info=True)
            raise



    def get_last_updated_at(self, table_name):
        cursor = self.connection.cursor()
        sql = f"SELECT updated_at FROM {table_name} ORDER BY updated_at DESC LIMIT 1"
        cursor.execute(sql)
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else None

