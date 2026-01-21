"""
Yahoo Finance Market Data Provider

FREE market data provider - no API key required!
Great for development and testing.

Features:
- Real-time quotes (15-20 min delayed)
- Historical data
- No rate limits for reasonable use
- Supports stocks, ETFs, indices

@author: Pedro Gronda Garrigues
"""

import yfinance as yf
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from src.market_data.base_provider import MarketDataProvider, Quote, Bar
from src.utils.logger import get_logger


class YahooFinanceProvider(MarketDataProvider):
    """Yahoo Finance data provider - completely FREE"""
    
    def __init__(self):
        super().__init__("YahooFinance")
        self.logger = get_logger("YahooFinance")
        self._subscriptions = {}
    
    def connect(self) -> bool:
        """Yahoo Finance doesn't require explicit connection"""
        self.is_connected = True
        self.logger.info("Yahoo Finance provider ready (no auth required)")
        return True
    
    def disconnect(self):
        """Cleanup"""
        self.is_connected = False
        self._subscriptions.clear()
    
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """Get current quote for a symbol"""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            # get the most recent price data
            hist = ticker.history(period="1d", interval="1m")
            
            if hist.empty:
                self.logger.warning(f"No data available for {symbol}")
                return None
            
            latest = hist.iloc[-1]
            
            quote = Quote(
                symbol=symbol,
                timestamp=datetime.now(),
                last=latest['Close'],
                open=latest['Open'],
                high=latest['High'],
                low=latest['Low'],
                volume=int(latest['Volume']),
                bid=info.get('bid'),
                ask=info.get('ask'),
                bid_size=info.get('bidSize'),
                ask_size=info.get('askSize')
            )
            
            self.logger.debug(f"Got quote for {symbol}: ${quote.last:.2f}")
            return quote
            
        except Exception as e:
            self.logger.error(f"Error getting quote for {symbol}: {e}")
            return None
    
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        for symbol in symbols:
            quote = self.get_quote(symbol)
            if quote:
                quotes[symbol] = quote
        
        return quotes
    
    def get_historical_bars(self, symbol: str, period: str = "1d",
                           interval: str = "1m", limit: int = 100) -> List[Bar]:
        """
        Get historical OHLCV bars
        
        Args:
            symbol: Stock ticker
            period: '1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max'
            interval: '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h', '1d', '5d', '1wk', '1mo', '3mo'
            limit: Maximum number of bars
        """
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period, interval=interval)
            
            if hist.empty:
                self.logger.warning(f"No historical data for {symbol}")
                return []
            
            # convert to Bar objects
            bars = []
            for timestamp, row in hist.iterrows():
                bar = Bar(
                    symbol=symbol,
                    timestamp=timestamp.to_pydatetime(),
                    open=row['Open'],
                    high=row['High'],
                    low=row['Low'],
                    close=row['Close'],
                    volume=int(row['Volume'])
                )
                bars.append(bar)
            
            # apply limit
            if len(bars) > limit:
                bars = bars[-limit:]
            
            self.logger.debug(f"Got {len(bars)} bars for {symbol}")
            return bars
            
        except Exception as e:
            self.logger.error(f"Error getting historical data for {symbol}: {e}")
            return []
    
    def subscribe_quotes(self, symbols: List[str], callback):
        """
        Yahoo Finance doesn't support true real-time streaming.
        This stores the callback for polling-based updates.
        """
        for symbol in symbols:
            self._subscriptions[symbol] = callback
        
        self.logger.info(f"Subscribed to {len(symbols)} symbols (polling mode)")
    
    def unsubscribe_quotes(self, symbols: List[str]):
        """Unsubscribe from symbols"""
        for symbol in symbols:
            if symbol in self._subscriptions:
                del self._subscriptions[symbol]
        
        self.logger.info(f"Unsubscribed from {len(symbols)} symbols")
    
    def poll_subscriptions(self):
        """
        Poll all subscribed symbols and trigger callbacks
        Should be called periodically (e.g., every 1-5 seconds)
        """
        for symbol, callback in self._subscriptions.items():
            quote = self.get_quote(symbol)
            if quote and callback:
                callback(quote)

