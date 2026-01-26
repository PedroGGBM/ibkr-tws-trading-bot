#!/usr/bin/env python3
"""
Simple script to list all current positions in IBKR TWS

Quick check to verify you can retrieve your holdings.
Run with: python list_positions.py

@author: Pedro Gronda Garrigues
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.connection.ibkr_client import IBKRClient
from src.utils.logger import get_logger


def list_positions():
    """List all current positions in IBKR account"""
    logger = get_logger("PositionsList")
    
    print("\n" + "=" * 70)
    print("IBKR TWS - Current Holdings")
    print("=" * 70 + "\n")
    
    # Connection settings
    host = "127.0.0.1"
    port = 7496  # Change to 7496 for live account
    client_id = 999  # Use different ID to avoid conflicts
    
    print(f"Connecting to TWS at {host}:{port}...")
    
    # Create and connect client
    client = IBKRClient(
        host=host,
        port=port,
        client_id=client_id,
        use_delayed_data=True
    )
    
    if not client.connect_and_run():
        print("STATUS: Failed to connect to IBKR TWS/Gateway")
        print("\nMake sure:")
        print("  1. TWS or IB Gateway is running")
        print("  2. API is enabled in TWS settings")
        print("  3. Port number is correct (7497 for paper, 7496 for live)")
        return 1
    
    print("STATUS: Connected!\n")
    
    # request positions
    print("Requesting current positions...")
    client.request_positions()
    
    # wait for positions to be received
    time.sleep(2)
    
    # get all positions
    positions = client.get_all_positions()
    
    # display results
    print("\n" + "=" * 70)
    print(f"CURRENT HOLDINGS ({len(positions)} positions)")
    print("=" * 70 + "\n")
    
    if not positions:
        print("No positions found.")
        print("\nThis could mean:")
        print("  • Your account has no open positions")
        print("  • You're connected to the wrong account (paper vs live)")
        print("  • Positions are still loading (try running again)")
    else:
        # print table header
        print(f"{'Symbol':<10} {'Quantity':>12} {'Avg Cost':>12} {'Market Value':>15}")
        print("-" * 70)
        
        total_value = 0.0
        
        for symbol, pos_data in sorted(positions.items()):
            quantity = pos_data['position']
            avg_cost = pos_data['avg_cost']
            market_value = abs(quantity * avg_cost)
            total_value += market_value
            
            # format position type
            pos_type = "LONG" if quantity > 0 else "SHORT"
            
            print(f"{symbol:<10} {quantity:>12.0f} {'$' + f'{avg_cost:,.2f}':>12} "
                  f"{'$' + f'{market_value:,.2f}':>15}")
        
        print("-" * 70)
        print(f"{'TOTAL':<10} {'':<12} {'':<12} {'$' + f'{total_value:,.2f}':>15}")
    
    # request account summary for additional info
    print("\n" + "=" * 70)
    print("ACCOUNT SUMMARY")
    print("=" * 70 + "\n")
    
    client.request_account_summary()
    time.sleep(1.5)
    
    net_liq = client.get_account_value("NetLiquidation")
    cash = client.get_account_value("TotalCashValue")
    buying_power = client.get_account_value("BuyingPower")
    
    if net_liq:
        print(f"Net Liquidation Value: ${float(net_liq):,.2f}")
    if cash:
        print(f"Total Cash:            ${float(cash):,.2f}")
    if buying_power:
        print(f"Buying Power:          ${float(buying_power):,.2f}")
    
    # disconnect
    print("\nDisconnecting...")
    client.disconnect_gracefully()
    
    print("\n" + "=" * 70)
    print("STATUS: Done!")
    print("=" * 70 + "\n")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(list_positions())
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nSTATUS: Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

