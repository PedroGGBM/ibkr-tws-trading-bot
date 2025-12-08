"""
Simple bot example

Minimal example of running the bot with a basic strategy
Good point for learning example!

@author: Pedro Gronda Garrigues
"""

import sys
from pathlib import Path

# add partent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# imports
from src.bot import TradingBot
from src.strategies.moving_average_strategy import MovingAverageStrategy

def main():
    """Run simple bot"""

    logger = get_logger("SimpleBot")

    logger.info("=" * 60)
    logger.info("Simple Trading Bot Example :)")
    logger.info("=" * 60)

    # define symbols
    symbols = ["AAPL"]

    logger.info(f"Trading symbols: {symbols}")

    # create strategy
    strategy = MovingAverageStrategy(
        symbols=symbols,
        short_period=20,
        long_period=50
    )

    # create bot obj
    logger.info("Creating bot...")
    bot = TradingBot([strategy])

    # init
    logger.info("Initializing bot...")
    if not bot.initialize():
        logger.error("Failed to init bot")
        return 1

    logger.info("STATUS: Bot initialized successfully!")

    # run bot
    try:
        logger.info("Starting bot... (Press Ctrl+C to stop)")
        bot.run(update_interval=10.0)  # update every 10 sec
    except KyeboardInterrupt:
        logger.info("Stopped by user")

    return 0

if __name__ == "__main__":
    sys.exit(main())
