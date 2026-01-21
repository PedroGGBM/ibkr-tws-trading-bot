"""
Base Market Data Provider Interface

Defines the common interface that all market data providers must implement.
This allows easy switching between IBKR, Polygon, Alpha Vantage, Yahoo Finance, etc.

@author: Pedro Gronda Garrigues
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class Quote:
    """Market quote data structure"""
    symbol: str
    timestamp: datetime
    bid: Optional[float] = None
    ask: Optional[float] = None
    last: Optional[float] = None
    bid_size: Optional[int] = None
    ask_size: Optional[int] = None
    volume: Optional[int] = None
    high: Optional[float] = None
    low: Optional[float] = None
    open: Optional[float] = None
    close: Optional[float] = None
    
    @property
    def mid_price(self) -> Optional[float]:
        """Calculate mid price from bid/ask"""
        if self.bid is not None and self.ask is not None:
            return (self.bid + self.ask) / 2
        return self.last
    
    @property
    def spread(self) -> Optional[float]:
        """Calculate bid-ask spread"""
        if self.bid is not None and self.ask is not None:
            return self.ask - self.bid
        return None
    
    def __repr__(self):
        return (f"Quote({self.symbol}: Last=${self.last}, "
                f"Bid=${self.bid}, Ask=${self.ask}, Vol={self.volume})")


@dataclass
class Bar:
    """OHLCV bar data structure"""
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    
    def __repr__(self):
        return (f"Bar({self.symbol} {self.timestamp}: "
                f"O={self.open} H={self.high} L={self.low} C={self.close} V={self.volume})")


class MarketDataProvider(ABC):
    """
    Abstract base class for market data providers
    
    All market data providers must implement these methods to ensure
    consistent interface across different data sources.
    """
    
    def __init__(self, name: str):
        self.name = name
        self.is_connected = False
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Connect to the market data provider
        
        Returns:
            bool: True if connection successful
        """
        pass
    
    @abstractmethod
    def disconnect(self):
        """Disconnect from the market data provider"""
        pass
    
    @abstractmethod
    def get_quote(self, symbol: str) -> Optional[Quote]:
        """
        Get current quote for a symbol
        
        Args:
            symbol: Stock ticker symbol
        
        Returns:
            Quote object or None if unavailable
        """
        pass
    
    @abstractmethod
    def get_quotes(self, symbols: List[str]) -> Dict[str, Quote]:
        """
        Get quotes for multiple symbols
        
        Args:
            symbols: List of ticker symbols
        
        Returns:
            Dictionary mapping symbols to Quote objects
        """
        pass
    
    @abstractmethod
    def get_historical_bars(self, symbol: str, period: str = "1d",
                           interval: str = "1m", limit: int = 100) -> List[Bar]:
        """
        Get historical OHLCV bars
        
        Args:
            symbol: Stock ticker symbol
            period: Time period (e.g., '1d', '5d', '1mo', '1y')
            interval: Bar interval (e.g., '1m', '5m', '1h', '1d')
            limit: Maximum number of bars to return
        
        Returns:
            List of Bar objects
        """
        pass
    
    @abstractmethod
    def subscribe_quotes(self, symbols: List[str], callback):
        """
        Subscribe to real-time quote updates
        
        Args:
            symbols: List of ticker symbols
            callback: Function to call with Quote updates
        """
        pass
    
    @abstractmethod
    def unsubscribe_quotes(self, symbols: List[str]):
        """
        Unsubscribe from quote updates
        
        Args:
            symbols: List of ticker symbols
        """
        pass
    
    def is_market_open(self) -> bool:
        """
        Check if market is currently open
        
        Default implementation checks US market hours.
        Override for different markets.
        """
        now = datetime.now()
        
        # check if weekend
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # US market hours: 9:30 AM - 4:00 PM ET
        market_open = now.replace(hour=9, minute=30, second=0)
        market_close = now.replace(hour=16, minute=0, second=0)
        
        return market_open <= now <= market_close
    
    def __repr__(self):
        status = "connected" if self.is_connected else "disconnected"
        return f"{self.name} ({status})"

