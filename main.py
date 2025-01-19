import logging
import time
from bot.strategies import ScalpingStrategy
from bot.exchange import ExchangeAPI
from bot.database import DatabaseManager
from bot.core.bot import Bot
from bot.exchange import robinhood
from mysql.connector import connect
from dotenv import load_dotenv
import os

LOG_FILE = 'var/log/app.log'

if not os.path.exists('var/log'):
    os.makedirs('dvar/log')

file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logging.getLogger('').addHandler(file_handler)
logger = logging.getLogger(__name__)

# Main Function
def main():
    # Coins we track and trade
    symbols = [
        "XRP-USD",
        "ADA-USD",
        "SOL-USD",
        "ETC-USD",
        "XTZ-USD",
        "LINK-USD",
        "UNI-USD",
    ]

    # Load environment variables
    load_dotenv()

    # Initialize database connection
    connection = connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

    # Initialize API client and related objects
    api_client = robinhood.CryptoAPITrading()
    db_manager = DatabaseManager(connection)
    api = ExchangeAPI(api_client)
    strategy = ScalpingStrategy()
    bot = Bot(symbols, strategy, api, db_manager)

    # Execute the bot
    bot.execute()

    # Close the database connection after execution
    connection.close()

if __name__ == "__main__":
    main()
