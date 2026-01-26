"""
IBKR TWS Trading Bot - Main Entry Point

This is the main script to run the trading bot.
Configure your settings in .env file before running.

@author: Pedro Gronda Garrigues
"""

import sys
from pathlib import Path

# add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.bot import TradingBot
from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.strategies.momentum_strategy import MomentumStrategy
from src.utils.logger import get_logger
from config import config


def main():
    """Main entry point"""
    logger = get_logger("Main")
    
    logger.info("=" * 60)
    logger.info("IBKR TWS Trading Bot")
    logger.info("=" * 60)
    
    # define symbols to trade
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    # create strategies
    strategies = [
        # Moving Average Crossover Strategy (20/50 MA)
        MovingAverageStrategy(symbols=symbols, short_period=20, long_period=50),
        
        # Momentum Strategy
        # MomentumStrategy(symbols=symbols, period=14, buy_threshold=2.0, sell_threshold=-1.0)
    ]
    
    # create bot
    bot = TradingBot(strategies)
    
    # initialize bot
    if not bot.initialize():
        logger.error("Bot initialization failed!")
        return 1
    
    # run bot
    try:
        # update every 5 seconds (adjust based on your needs)
        bot.run(update_interval=5.0)
    except Exception as e:
        logger.error(f"Bot crashed: {e}", exc_info=True)
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())

