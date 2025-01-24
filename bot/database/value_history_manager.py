import logging


class ValueHistoryManager:
    def __init__(self, connection):
        self.connection = connection

    def insert_data(self, coin, coin_data):
        cursor = self.connection.cursor()
        table_name = f"{coin.replace('-USD', '').lower()}_value_history"
        results = coin_data.get("results", [])
        if not results:
            return
        data_entry = results[0]
        timestamp = data_entry.get("timestamp") or datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        price = float(data_entry.get("price", 0.0))
        ask_price = float(data_entry.get("ask_inclusive_of_buy_spread", 0.0))
        bid_price = float(data_entry.get("bid_inclusive_of_sell_spread", 0.0))
        values = (timestamp, price, ask_price, bid_price)
        sql = f"""
            INSERT INTO {table_name} (timestamp, price, ask_inclusive_of_buy_spread, bid_inclusive_of_sell_spread)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(sql, values)
        self.connection.commit()
        cursor.close()

    def fetch_data(self):
        """Fetch historical data for the symbol from the database."""
        table_name = f"{self.symbol.replace('-', '_')}_value_history"
        query = f"SELECT timestamp, bid_inclusive_of_sell_spread, ask_inclusive_of_buy_spread FROM {table_name} ORDER BY timestamp DESC LIMIT 500"
        
        results = self.db_manager.execute_query(query)  # Assuming execute_query returns a list of tuples
        if not results:
            raise ValueError(f"No data found for {self.symbol} in {table_name}.")
        
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
