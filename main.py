import logging
import os
import json
import time
from dotenv import load_dotenv
from bot.strategies import ScalpingStrategy
from bot.exchange import ExchangeAPI
from bot.database import DatabaseManager
from bot.core.bot import Bot
from bot.exchange import robinhood
from mysql.connector import connect
from sklearn.ensemble import RandomForestClassifier
import configparser

# Load configuration and environment variables
def setup_environment():
    config = configparser.ConfigParser()
    base_dir = os.path.dirname(os.path.realpath(__file__))
    config.read(f"{base_dir}/config.ini")

    env_file = config.get("DEFAULT", "environment_vars")
    load_dotenv(f"{base_dir}{env_file}")

    log_dir = config.get("DEFAULT", "log_directory")
    log_file = config.get("DEFAULT", "log_file")
    os.makedirs(log_dir, exist_ok=True)

    return config, log_file

# Setup logging
def setup_logging(log_file):
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_file)
        ]
    )
    return logging.getLogger(__name__)

# Main function
def main():
    # Setup environment and logging
    config, log_file = setup_environment()
    logger = setup_logging(log_file)

    # Initialize database connection
    connection = connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
    )

    # Initialize API client and bot components
    api_client = robinhood.CryptoAPITrading()
    api = ExchangeAPI(api_client)
    db_manager = DatabaseManager(connection)
    strategy = ScalpingStrategy()
    bot = Bot(api, db_manager, strategy, config)  # Pass config to Bot
    i = 0
    try:
        while i < 6:
            bot.run()  # Run the bot
            time.sleep(10) 
            i += 1
    except Exception as e:
        logger.error(f"An error occurred during bot execution: {e}", exc_info=True)
    finally:
        connection.close()  # Ensure database connection is closed

if __name__ == "__main__":
    main()
