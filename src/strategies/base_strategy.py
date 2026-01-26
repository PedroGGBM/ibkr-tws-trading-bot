"""
Base Trading Strategy Interface

Provides abstract base class for all trading strategies.
Implements common functionality and enforces strategy interface.

@author: Pedro Gronda Garrigues
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass

from src.market_data.base_provider import Quote, Bar
from src.utils.logger import get_logger


class SignalType(Enum):
    """Trading signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    CLOSE_LONG = "CLOSE_LONG"
    CLOSE_SHORT = "CLOSE_SHORT"


@dataclass
class TradingSignal:
    """Trading signal with metadata"""
    symbol: str
    signal_type: SignalType
    timestamp: datetime
    price: float
    quantity: int = 0
    confidence: float = 1.0  # 0-1 confidence score
    reason: str = ""
    
    def __repr__(self):
        return (f"Signal({self.signal_type.value} {self.quantity} {self.symbol} "
                f"@ ${self.price:.2f} - {self.reason})")


class BaseStrategy(ABC):
    """
    Abstract base class for trading strategies
    
    All trading strategies must inherit from this class and implement
    the required methods.
    """
    
    def __init__(self, name: str, symbols: List[str]):
        """
        Initialize strategy
        
        Args:
            name: Strategy name
            symbols: List of symbols to trade
        """
        self.name = name
        self.symbols = symbols
        self.logger = get_logger(f"Strategy.{name}")
        
        # Strategy state
        self.is_active = False
        self.positions: Dict[str, int] = {}  # symbol -> quantity
        self.entry_prices: Dict[str, float] = {}  # symbol -> entry price
        
        # Performance tracking
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        
        # Historical data storage
        self.price_history: Dict[str, List[float]] = {s: [] for s in symbols}
        self.signal_history: List[TradingSignal] = []
        
        self.logger.info(f"Initialized strategy '{name}' for symbols: {symbols}")
    
    @abstractmethod
    def on_quote(self, quote: Quote) -> Optional[TradingSignal]:
        """
        Process a new quote and generate trading signal
        
        Args:
            quote: Market quote
        
        Returns:
            TradingSignal if action needed, None otherwise
        """
        pass
    
    @abstractmethod
    def on_bar(self, bar: Bar) -> Optional[TradingSignal]:
        """
        Process a new bar and generate trading signal
        
        Args:
            bar: OHLCV bar
        
        Returns:
            TradingSignal if action needed, None otherwise
        """
        pass
    
    def on_position_update(self, symbol: str, quantity: int, avg_price: float):
        """
        Called when position is updated
        
        Args:
            symbol: Symbol
            quantity: New position quantity (positive=long, negative=short, 0=flat)
            avg_price: Average entry price
        """
        old_quantity = self.positions.get(symbol, 0)
        self.positions[symbol] = quantity
        
        if quantity != 0:
            self.entry_prices[symbol] = avg_price
        elif symbol in self.entry_prices:
            del self.entry_prices[symbol]
        
        self.logger.info(f"Position updated: {symbol} {old_quantity} -> {quantity} @ ${avg_price:.2f}")
    
    def on_fill(self, symbol: str, quantity: int, price: float):
        """
        Called when an order is filled
        
        Args:
            symbol: Symbol
            quantity: Filled quantity (positive=bought, negative=sold)
            price: Fill price
        """
        self.total_trades += 1
        
        # Update PnL if closing position
        if symbol in self.entry_prices and symbol in self.positions:
            old_position = self.positions[symbol]
            
            # Calculate realized PnL
            if (old_position > 0 and quantity < 0) or (old_position < 0 and quantity > 0):
                closed_qty = min(abs(quantity), abs(old_position))
                pnl = closed_qty * (price - self.entry_prices[symbol]) * (1 if old_position > 0 else -1)
                
                self.total_pnl += pnl
                
                if pnl > 0:
                    self.winning_trades += 1
                    self.logger.info(f"Winning trade: ${pnl:.2f} on {symbol}")
                else:
                    self.losing_trades += 1
                    self.logger.info(f"Losing trade: ${pnl:.2f} on {symbol}")
        
        self.logger.trade(f"Fill: {quantity} {symbol} @ ${price:.2f}")
    
    def start(self):
        """Start the strategy"""
        self.is_active = True
        self.logger.info(f"Strategy '{self.name}' started")
    
    def stop(self):
        """Stop the strategy"""
        self.is_active = False
        self.logger.info(f"Strategy '{self.name}' stopped")
    
    def reset(self):
        """Reset strategy state"""
        self.positions.clear()
        self.entry_prices.clear()
        self.price_history = {s: [] for s in self.symbols}
        self.signal_history.clear()
        self.total_trades = 0
        self.winning_trades = 0
        self.losing_trades = 0
        self.total_pnl = 0.0
        self.logger.info(f"Strategy '{self.name}' reset")
    
    def get_position(self, symbol: str) -> int:
        """Get current position for symbol"""
        return self.positions.get(symbol, 0)
    
    def has_position(self, symbol: str) -> bool:
        """Check if we have a position in symbol"""
        return symbol in self.positions and self.positions[symbol] != 0
    
    def add_price(self, symbol: str, price: float):
        """Add price to history"""
        if symbol in self.price_history:
            self.price_history[symbol].append(price)
    
    def get_price_history(self, symbol: str, length: int = None) -> List[float]:
        """Get price history for symbol"""
        history = self.price_history.get(symbol, [])
        if length:
            return history[-length:]
        return history
    
    def create_signal(self, symbol: str, signal_type: SignalType, 
                     price: float, quantity: int = 0, 
                     confidence: float = 1.0, reason: str = "") -> TradingSignal:
        """
        Create and log a trading signal
        
        Args:
            symbol: Symbol
            signal_type: Type of signal
            price: Current price
            quantity: Order quantity
            confidence: Signal confidence (0-1)
            reason: Reason for signal
        
        Returns:
            TradingSignal object
        """
        signal = TradingSignal(
            symbol=symbol,
            signal_type=signal_type,
            timestamp=datetime.now(),
            price=price,
            quantity=quantity,
            confidence=confidence,
            reason=reason
        )
        
        self.signal_history.append(signal)
        self.logger.info(f"Signal generated: {signal}")
        
        return signal
    
    def get_performance_summary(self) -> Dict:
        """Get strategy performance metrics"""
        win_rate = (self.winning_trades / self.total_trades * 100 
                   if self.total_trades > 0 else 0)
        
        avg_pnl = self.total_pnl / self.total_trades if self.total_trades > 0 else 0
        
        return {
            'strategy_name': self.name,
            'is_active': self.is_active,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': win_rate,
            'total_pnl': self.total_pnl,
            'avg_pnl': avg_pnl,
            'current_positions': self.positions.copy()
        }
    
    def __repr__(self):
        return f"{self.name} ({'active' if self.is_active else 'inactive'})"

