import logging
import pandas as pd

class ValueHistoryManager:
    def __init__(self, connection):
        self.connection = connection

    def insert_data(self, coin_data):
        cursor = self.connection.cursor()
        try:
            for data in coin_data:  # Iterate through the list of dictionaries
                coin = data.get("symbol")
                if not coin:
                    logging.warning("Skipping entry without a symbol.")
                    continue
                
                table_name = f"{coin.replace('-USD', '').lower()}_value_history"
                timestamp = data.get("timestamp") or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
                price = float(data.get("price", 0.0))
                ask_price = float(data.get("ask_inclusive_of_buy_spread", 0.0))
                bid_price = float(data.get("bid_inclusive_of_sell_spread", 0.0))
                values = (timestamp, price, ask_price, bid_price)
                
                sql = f"""
                    INSERT INTO {table_name} (timestamp, price, ask_inclusive_of_buy_spread, bid_inclusive_of_sell_spread)
                    VALUES (%s, %s, %s, %s)
                """
                cursor.execute(sql, values)
            
            self.connection.commit()
        except Exception as e:
            logging.error(f"Error inserting data: {e}", exc_info=True)
        finally:
            cursor.close()

    def get_value_history(self, coin_symbol, length):
        cursor = self.connection.cursor()
        table_name = f"{coin_symbol.replace('-USD', '').lower()}_value_history"
        query = f"SELECT timestamp, bid_inclusive_of_sell_spread, ask_inclusive_of_buy_spread FROM {table_name} ORDER BY timestamp DESC LIMIT {length}"
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        # Convert to DataFrame
        df = pd.DataFrame(results, columns=["timestamp", "bid_inclusive_of_sell_spread", "ask_inclusive_of_buy_spread"])
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
        
        # Feature engineering
        df['spread'] = df['ask_inclusive_of_buy_spread'] - df['bid_inclusive_of_sell_spread']
        df['price_change'] = df['bid_inclusive_of_sell_spread'].pct_change()
        df['momentum'] = df['bid_inclusive_of_sell_spread'] - df['bid_inclusive_of_sell_spread'].shift(5)
        df['volatility'] = df['bid_inclusive_of_sell_spread'].rolling(window=10).std()
        
        return df.dropna()
