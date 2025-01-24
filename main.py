import logging
import time
import os
from bot.strategies import ScalpingStrategy
from bot.exchange import ExchangeAPI
from bot.database import DatabaseManager
from bot.core.bot import Bot
from bot.exchange import robinhood
from mysql.connector import connect
from dotenv import load_dotenv

# Load environment variables
load_dotenv('/Users/carlelder/Documents/predictionengine/.env')

LOG_FILE = 'var/log/app.log'
os.makedirs('var/log', exist_ok=True)

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logging.basicConfig(level=logging.INFO)  # Basic console config
logging.getLogger('').addHandler(file_handler)  # Add file handler to root logger

logger = logging.getLogger(__name__)

# Main Function
def main():
    """
    1. Move coins to json / xml settings
    2. Never put logic here - just set db connection, initialize objects, start core/bot, close the connection. The rest goes
        to Bot
    """
    # Coins we track and trade
    coins = [
        "ADA-USD",
        "ETC-USD",
        "LINK-USD",
        "SOL-USD",
        "UNI-USD",
        "XRP-USD",
        "XTZ-USD"
    ]

    # 1. Initialize database connection
    connection = connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

    # 2. Initialize API client and related objects
    api_client = robinhood.CryptoAPITrading()
    api = ExchangeAPI(api_client)
    db_manager = DatabaseManager(connection)
    """
    need to change this over. Do not create scalping here - create parent strategy, 
    let bot/core pass which child to create based on settings file
    """
    strategy = ScalpingStrategy()
    bot = Bot(coins, api, db_manager, strategy)

    # 3. Execute the bot
    bot.run()

    # 4. Close the database connection after execution
    connection.close()

if __name__ == "__main__":
    """
    Need to re-establish 10-second loop / while
    """
    main()
