"""
Momentum Trading Strategy

Trades based on price momentum and rate of change.

Strategy Logic:
- BUY when price momentum is strong and positive
- SELL when momentum reverses or weakens
- Uses Rate of Change (ROC) indicator

Parameters:
- period: Lookback period for momentum calculation (default: 14)
- buy_threshold: ROC threshold for buy signals (default: 2.0%)
- sell_threshold: ROC threshold for sell signals (default: -1.0%)

@author: Pedro Gronda Garrigues
"""

from typing import Optional, List

from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.market_data.base_provider import Quote, Bar


class MomentumStrategy(BaseStrategy):
    """
    Momentum Strategy using Rate of Change (ROC)
    
    Generates BUY signals when ROC exceeds buy threshold
    Generates SELL signals when ROC falls below sell threshold
    """
    
    def __init__(self, symbols: List[str], period: int = 14,
                 buy_threshold: float = 2.0, sell_threshold: float = -1.0):
        """
        Initialize strategy
        
        Args:
            symbols: List of symbols to trade
            period: Lookback period for ROC calculation
            buy_threshold: ROC % threshold for buy (e.g., 2.0 = 2%)
            sell_threshold: ROC % threshold for sell (e.g., -1.0 = -1%)
        """
        super().__init__(f"Momentum_{period}", symbols)
        
        self.period = period
        self.buy_threshold = buy_threshold
        self.sell_threshold = sell_threshold
        
        # Track previous ROC for trend detection
        self.prev_roc: dict[str, float] = {}
        
        self.logger.info(f"Momentum Strategy: period={period}, "
                        f"buy>{buy_threshold}%, sell<{sell_threshold}%")
    
    def calculate_roc(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate Rate of Change (ROC)
        
        ROC = ((current_price - price_n_periods_ago) / price_n_periods_ago) * 100
        
        Args:
            prices: List of prices
            period: Number of periods to look back
        
        Returns:
            ROC percentage or None if insufficient data
        """
        if len(prices) < period + 1:
            return None
        
        current_price = prices[-1]
        old_price = prices[-(period + 1)]
        
        if old_price == 0:
            return None
        
        roc = ((current_price - old_price) / old_price) * 100
        return roc
    
    def calculate_momentum(self, prices: List[float], period: int) -> Optional[float]:
        """
        Calculate momentum (simple price difference)
        
        Args:
            prices: List of prices
            period: Number of periods
        
        Returns:
            Momentum value or None
        """
        if len(prices) < period + 1:
            return None
        
        return prices[-1] - prices[-(period + 1)]
    
    def on_quote(self, quote: Quote) -> Optional[TradingSignal]:
        """
        Process quote and generate signal based on momentum
        
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
        
        # Need enough data for ROC calculation
        if len(prices) < self.period + 1:
            self.logger.debug(f"{symbol}: Need {self.period + 1} prices, have {len(prices)}")
            return None
        
        # Calculate ROC
        roc = self.calculate_roc(prices, self.period)
        
        if roc is None:
            return None
        
        # Get previous ROC
        prev_roc = self.prev_roc.get(symbol, 0.0)
        self.prev_roc[symbol] = roc
        
        # Generate signals based on ROC
        signal = None
        
        # Strong positive momentum - BUY signal
        if roc > self.buy_threshold and prev_roc <= self.buy_threshold:
            if not self.has_position(symbol):
                signal = self.create_signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=min(0.9, 0.7 + (roc / 100)),  # Higher confidence with stronger momentum
                    reason=f"Strong momentum: ROC={roc:.2f}% > {self.buy_threshold}%"
                )
        
        # Negative momentum - SELL signal
        elif roc < self.sell_threshold and self.has_position(symbol):
            signal = self.create_signal(
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=price,
                confidence=0.8,
                reason=f"Momentum reversal: ROC={roc:.2f}% < {self.sell_threshold}%"
            )
        
        # Momentum weakening significantly - exit signal
        elif self.has_position(symbol) and roc < 0.5 and prev_roc > 1.5:
            signal = self.create_signal(
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=price,
                confidence=0.7,
                reason=f"Momentum weakening: ROC={roc:.2f}% (was {prev_roc:.2f}%)"
            )
        
        return signal
    
    def on_bar(self, bar: Bar) -> Optional[TradingSignal]:
        """
        Process bar (use close price)
        
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
            Dict with momentum indicators
        """
        prices = self.get_price_history(symbol)
        
        roc = self.calculate_roc(prices, self.period)
        momentum = self.calculate_momentum(prices, self.period)
        
        return {
            'roc': roc,
            'momentum': momentum,
            'price': prices[-1] if prices else None,
            'prev_roc': self.prev_roc.get(symbol),
            'data_points': len(prices),
            'buy_threshold': self.buy_threshold,
            'sell_threshold': self.sell_threshold
        }

