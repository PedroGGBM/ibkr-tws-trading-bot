"""
IBKR Market Data Provider

Uses IBKR TWS/Gateway for market data.
Supports:
- Delayed market data (FREE - 15-20 min delay)
- Historical data (FREE)
- Real-time data (requires subscription)

@author: Pedro Gronda Garrigues
"""

from typing import Dict, List, Optional
from datetime import datetime
import time

from ibapi.contract import Contract

from src.market_data.base_provider import MarketDataProvider, Quote, Bar
from src.connection.ibkr_client import IBKRClient
from src.utils.logger import get_logger


class IBKRMarketDataProvider(MarketDataProvider):
    """IBKR market data provider with delayed data support (FREE)"""
    
    def __init__(self, client: IBKRClient):
        super().__init__("IBKR")
        self.client = client
        self.logger = get_logger("IBKRMarketData")
        self._quote_req_ids: Dict[str, int] = {}  # symbol -> req_id
        self._callbacks: Dict[str, callable] = {}  # symbol -> callback
    
    def connect(self) -> bool:
        """IBKR client should already be connected"""
        if self.client.is_connected:
            self.is_connected = True
            self.logger.info("IBKR market data provider ready")
            return True
        else:
            self.logger.error("IBKR client not connected")
            return False
    
    def disconnect(self):
        """Cancel all market data subscriptions"""
        for symbol, req_id in self._quote_req_ids.items():
            self.client.cancel_market_data(req_id)
        
        self._quote_req_ids.clear()
        self._callbacks.clear()
        self.is_connected = False
    
    def _create_contract(self, symbol: str) -> Contract:
        """Create a stock contract for a symbol"""
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get current quote for a symbol
        Note: IBKR requires subscription. This will subscribe and wait briefly for data.
        """
        # check if already subscribed
        if symbol not in self._quote_req_ids:
            contract = self._create_contract(symbol)
            req_id = self.client.request_market_data(contract)
            self._quote_req_ids[symbol] = req_id
            
            # wait (briefly) for data to arrive
            time.sleep(0.5)
        
        # get cached market data
        req_id = self._quote_req_ids[symbol]
        data = self.client.get_market_data(req_id)
        
        if not data:
            self.logger.warning(f"No data available for {symbol}")
            return None
        
        quote = Quote(
            symbol=symbol,
            timestamp=data.get('timestamp', datetime.now()),
            bid=data.get('bid'),
            ask=data.get('ask'),
            last=data.get('last'),
            bid_size=data.get('bid_size'),
            ask_size=data.get('ask_size'),
            volume=data.get('volume'),
            high=data.get('high'),
            low=data.get('low'),
            close=data.get('close')
        )
        
        return quote
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        # subscribe all symbols first
        for symbol in symbols:
            if symbol not in self._quote_req_ids:
                contract = self._create_contract(symbol)
                req_id = self.client.request_market_data(contract)
                self._quote_req_ids[symbol] = req_id
        
        # wait for data
        time.sleep(1.0)
        
        # collect quotes
        for symbol in symbols:
            quote = self.get_quote(symbol)
            if quote:
                quotes[symbol] = quote
        
        return quotes
    
    def get_historical_bars(self, symbol: str, period: str = "1d",
                           interval: str = "1m", limit: int = 100) -> List[Bar]:
        """
        Get historical bars from IBKR
        
        Note: This is a simplified version. IBKR historical data requires
        more complex handling with callbacks.
        """
        # this would require implementing historical data callbacks
        # [FOR NOW] returning empty list - use Yahoo Finance for historical data
        # TODO: Implement historical data callbacks
        self.logger.warning("IBKR historical data not yet implemented - use Yahoo Finance")
        return []
    
    def subscribe_quotes(self, symbols: List[str], callback):
        """Subscribe to real-time quote updates"""
        for symbol in symbols:
            if symbol in self._quote_req_ids:
                # Already subscribed
                self._callbacks[symbol] = callback
                continue
            
            contract = self._create_contract(symbol)
            
            # Create wrapper callback that converts to Quote object
            def quote_callback(req_id, tick_type, value):
                quote = self.get_quote(symbol)
                if quote and callback:
                    callback(quote)
            
            req_id = self.client.request_market_data(contract, quote_callback)
            self._quote_req_ids[symbol] = req_id
            self._callbacks[symbol] = callback
        
        self.logger.info(f"Subscribed to {len(symbols)} symbols")
    
    def unsubscribe_quotes(self, symbols: List[str]):
        """Unsubscribe from quote updates"""
        for symbol in symbols:
            if symbol in self._quote_req_ids:
                req_id = self._quote_req_ids[symbol]
                self.client.cancel_market_data(req_id)
                del self._quote_req_ids[symbol]
            
            if symbol in self._callbacks:
                del self._callbacks[symbol]
        
        self.logger.info(f"Unsubscribed from {len(symbols)} symbols")

