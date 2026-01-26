"""
Moving Average Crossover Strategy

Classic strategy that trades on moving average crossovers.

Strategy Logic:
- BUY when short MA crosses above long MA (golden cross)
- SELL when short MA crosses below long MA (death cross)
- Uses simple moving averages (SMA)

Parameters:
- short_period: Period for short MA (default: 20)
- long_period: Period for long MA (default: 50)

@author: Pedro Gronda Garrigues
"""

from typing import Optional, List
import statistics

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.market_data.base_provider import Quote, Bar


class MovingAverageStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy
    
    Generates BUY signals on golden cross (short MA > long MA)
    Generates SELL signals on death cross (short MA < long MA)
    """
    
    def __init__(self, symbols: List[str], short_period: int = 20, 
                 long_period: int = 50):
        """
        Initialize strategy
        
        Args:
            symbols: List of symbols to trade
            short_period: Short moving average period
            long_period: Long moving average period
        """
        super().__init__(f"MA_Cross_{short_period}_{long_period}", symbols)
        
        self.short_period = short_period
        self.long_period = long_period
        
        # Track previous MA values for crossover detection
        self.prev_short_ma: dict[str, float] = {}
        self.prev_long_ma: dict[str, float] = {}
        
        self.logger.info(f"MA Crossover Strategy: {short_period}/{long_period}")
    
    def calculate_sma(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Simple Moving Average
        
        Args:
            prices: List of prices
            period: Number of periods
        
        Returns:
            SMA value or None if insufficient data
        """
        if len(prices) < period:
            return None
        
        return statistics.mean(prices[-period:])
    
    def on_quote(self, quote: Quote) -> Optional[TradingSignal]:
        """
        Process quote and generate signal based on MA crossover
        
        Args:
            quote: Market quote
        
        Returns:
            Trading signal or None
        """
        if not self.is_active:
            return None
        
        symbol = quote.symbol
        price = quote.last or quote.mid_price
        
        if price is None:
            return None
        
        # Add price to history
        self.add_price(symbol, price)
        
        # Get price history
        prices = self.get_price_history(symbol)
        
        # Need enough data for long MA
        if len(prices) < self.long_period:
            self.logger.debug(f"{symbol}: Need {self.long_period} prices, have {len(prices)}")
            return None
        
        # Calculate MAs
        short_ma = self.calculate_sma(prices, self.short_period)
        long_ma = self.calculate_sma(prices, self.long_period)
        
        if short_ma is None or long_ma is None:
            return None
        
        # Get previous MAs for crossover detection
        prev_short = self.prev_short_ma.get(symbol)
        prev_long = self.prev_long_ma.get(symbol)
        
        # Store current MAs for next iteration
        self.prev_short_ma[symbol] = short_ma
        self.prev_long_ma[symbol] = long_ma
        
        # Need previous values to detect crossover
        if prev_short is None or prev_long is None:
            return None
        
        # Check for crossovers
        signal = None
        
        # Golden Cross: Short MA crosses above Long MA
        if prev_short <= prev_long and short_ma > long_ma:
            if not self.has_position(symbol):
                signal = self.create_signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=0.8,
                    reason=f"Golden Cross: MA{self.short_period}={short_ma:.2f} > MA{self.long_period}={long_ma:.2f}"
                )
        
        # Death Cross: Short MA crosses below Long MA
        elif prev_short >= prev_long and short_ma < long_ma:
            if self.has_position(symbol):
                signal = self.create_signal(
                    symbol=symbol,
                    signal_type=SignalType.CLOSE_LONG,
                    price=price,
                    confidence=0.8,
                    reason=f"Death Cross: MA{self.short_period}={short_ma:.2f} < MA{self.long_period}={long_ma:.2f}"
                )
        
        return signal
    
    def on_bar(self, bar: Bar) -> Optional[TradingSignal]:
        """
        Process bar (use close price for MA calculation)
        
        Args:
            bar: OHLCV bar
        
        Returns:
            Trading signal or None
        """
        # Convert bar to quote for processing
        quote = Quote(
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            last=bar.close,
            high=bar.high,
            low=bar.low,
            open=bar.open,
            volume=bar.volume
        )
        
        return self.on_quote(quote)
    
    def get_indicator_values(self, symbol: str) -> dict:
        """
        Get current indicator values for a symbol
        
        Args:
            symbol: Symbol
        
        Returns:
            Dict with MA values
        """
        prices = self.get_price_history(symbol)
        
        return {
            'short_ma': self.calculate_sma(prices, self.short_period),
            'long_ma': self.calculate_sma(prices, self.long_period),
            'price': prices[-1] if prices else None,
            'data_points': len(prices)
        }

