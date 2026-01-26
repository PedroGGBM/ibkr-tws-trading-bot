"""
Test IBKR Connection

Quick script to verify IBKR TWS/Gateway connection is working.

@author: Pedro Gronda Garrigues
"""

import sys
from pathlib import Path

# add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.connection.ibkr_client import IBKRClient
from src.utils.logger import get_logger


def test_connection():
    """Test IBKR connection"""
    logger = get_logger("ConnectionTest")
    
    logger.info("=" * 60)
    logger.info("Testing IBKR Connection")
    logger.info("=" * 60)
    
    # connection parameters
    host = "127.0.0.1"
    port = 7497  # Paper trading
    client_id = 1
    
    logger.info(f"Connecting to {host}:{port} (Paper Trading)")
    
    # create client
    client = IBKRClient(
        host=host,
        port=port,
        client_id=client_id,
        use_delayed_data=True
    )
    
    # try to connect
    if client.connect_and_run():
        logger.info("STATUS: Successfully connected to IBKR!")
        
        # request account summary
        logger.info("Requesting account summary...")
        client.request_account_summary()
        
        # wait a bit for data
        import time
        time.sleep(2)
        
        # print account info
        net_liq = client.get_account_value("NetLiquidation")
        if net_liq:
            logger.info(f"Account Net Liquidation: ${float(net_liq):,.2f}")
        
        # request positions
        logger.info("Requesting positions...")
        client.request_positions()
        time.sleep(1)
        
        positions = client.get_all_positions()
        logger.info(f"Current positions: {len(positions)}")
        
        for symbol, pos in positions.items():
            logger.info(f"  {symbol}: {pos['position']} @ ${pos['avg_cost']:.2f}")
        
        # disconnect
        logger.info("Disconnecting...")
        client.disconnect_gracefully()
        
        logger.info("=" * 60)
        logger.info("STATUS: Connection test PASSED!")
        logger.info("=" * 60)
        return True
    else:
        logger.error("=" * 60)
        logger.error("STATUS: Connection test FAILED!")
        logger.error("=" * 60)
        logger.error("\nTroubleshooting:")
        logger.error("1. Make sure TWS/Gateway is running")
        logger.error("2. Verify port number (7497 for paper, 7496 for live)")
        logger.error("3. Check API is enabled in TWS settings")
        logger.error("4. Add 127.0.0.1 to trusted IPs in TWS")
        return False


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)

