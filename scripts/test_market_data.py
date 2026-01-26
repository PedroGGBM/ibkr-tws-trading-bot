"""
Test Market Data Providers

Quick script to verify market data is working.
Tests Yahoo Finance (free) and IBKR providers.

@author: Pedro Gronda Garrigues
"""

import sys
from pathlib import Pathfffffffff

# add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.market_data.yahoo_provider import YahooFinanceProvider
from src.utils.logger import get_logger

def test_yahoo_finance():
    """Test Yahoo Finance provider"""
    logger = get_logger("MarketDataTest")
    
    logger.info("=" * 60)
    logger.info("Testing Yahoo Finance Market Data (FREE)")
    logger.info("=" * 60)
    
    # create provider
    provider = YahooFinanceProvider()
    
    # connect
    if not provider.connect():
        logger.error("STATUS: Failed to initialize Yahoo Finance")
        return False
    
    logger.info("STATUS: Yahoo Finance provider ready")
    
    # test symbols
    symbols = ["AAPL", "MSFT", "GOOGL"]
    
    logger.info(f"\nTesting quotes for: {symbols}")
    logger.info("-" * 60)
    
    # get quotes
    quotes = provider.get_quotes(symbols)
    
    if not quotes:
        logger.error("STATUS: Failed to get quotes")
        return False
    
    # display quotes
    for symbol, quote in quotes.items():
        logger.info(f"\n{symbol}:")
        logger.info(f"  Last: ${quote.last:.2f}" if quote.last else "  Last: N/A")
        logger.info(f"  Bid: ${quote.bid:.2f}" if quote.bid else "  Bid: N/A")
        logger.info(f"  Ask: ${quote.ask:.2f}" if quote.ask else "  Ask: N/A")
        logger.info(f"  Volume: {quote.volume:,}" if quote.volume else "  Volume: N/A")
    
    logger.info("\n" + "-" * 60)
    
    # test historical data
    logger.info("\nTesting historical data for AAPL (last 5 days)...")
    bars = provider.get_historical_bars("AAPL", period="5d", interval="1d")
    
    if bars:
        logger.info(f"STATUS: Got {len(bars)} daily bars")
        logger.info("\nLast 3 bars:")
        for bar in bars[-3:]:
            logger.info(f"  {bar.timestamp.date()}: O=${bar.open:.2f} H=${bar.high:.2f} "
                       f"L=${bar.low:.2f} C=${bar.close:.2f} V={bar.volume:,}")
    else:
        logger.warning("STATUS: No historical data available")
    
    # disconnect
    provider.disconnect()
    
    logger.info("\n" + "=" * 60)
    logger.info("STATUS: Market data test PASSED!")
    logger.info("=" * 60)
    
    return True


def test_combined():
    """Test multiple providers with fallback"""
    logger = get_logger("MarketDataTest")
    
    logger.info("\n" + "=" * 60)
    logger.info("Testing Multi-Provider Setup")
    logger.info("=" * 60)
    
    from src.market_data.market_data_manager import MarketDataManager
    
    # create providers
    yahoo = YahooFinanceProvider()
    
    # create manager
    manager = MarketDataManager(
        primary_provider=yahoo,
        fallback_providers=[]
    )
    
    # connect
    if not manager.connect():
        logger.error("STATUS: Failed to connect to market data")
        return False
    
    logger.info("STATUS: Market data manager ready")
    
    # get quotes
    logger.info("\nGetting quotes via manager...")
    quote = manager.get_quote("AAPL")
    
    if quote:
        logger.info(f"STATUS: AAPL: ${quote.last:.2f} (via {manager.active_provider.name})")
    else:
        logger.error("STATUS: Failed to get quote")
        return False
    
    # get provider status
    status = manager.get_provider_status()
    logger.info(f"\nProvider Status:")
    logger.info(f"  Active: {status['active_provider']}")
    for name, info in status['providers'].items():
        logger.info(f"  {name}: {'STATUS: Connected' if info['connected'] else 'STATUS: Disconnected'}")
    
    manager.disconnect()
    
    logger.info("\n" + "=" * 60)
    logger.info("STATUS: Multi-provider test PASSED!")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    success = True
    
    # test Yahoo Finance
    if not test_yahoo_finance():
        success = False
    
    # test combined
    if not test_combined():
        success = False
    
    sys.exit(0 if success else 1)

