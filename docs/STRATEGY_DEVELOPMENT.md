# Strategy Development Guide

This guide will teach you how to create your own trading strategies for the IBKR TWS Trading Bot.

## Table of Contents

1. [Strategy Basics](#strategy-basics)
2. [Creating Your First Strategy](#creating-your-first-strategy)
3. [Strategy Lifecycle](#strategy-lifecycle)
4. [Signal Generation](#signal-generation)
5. [Using Indicators](#using-indicators)
6. [Testing Strategies](#testing-strategies)
7. [Best Practices](#best-practices)
8. [Example Strategies](#example-strategies)

## Strategy basics

### What is a trading strategy?

Class that:
- inherits from `BaseStrategy`
- processes market data (quotes or bars)
- generates signals (BUY, SELL, HOLD)
- tracks performance and positions

### Architecture

```
BaseStrategy (abstract)
    => YourStrategy (concrete)
    => market data -> signals -> bot executes
```

## Creating your first strategy

### Step 1: create strategy file

New file in `src/strategies/`:

```bash
touch src/strategies/my_strategy.py
```

### Step 2: basic template

```python
from typing import Optional, List
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.market_data.base_provider import Quote, Bar


class MyStrategy(BaseStrategy):
    """
    My custom trading strategy
    
    Strategy Logic:
    - Buy when [your condition]
    - Sell when [your condition]
    """
    
    def __init__(self, symbols: List[str], **kwargs):
        """
        Initialize strategy
        
        Args:
            symbols: List of symbols to trade
            **kwargs: Strategy-specific parameters
        """
        super().__init__("MyStrategy", symbols)
        
        # your parameters
        self.param1 = kwargs.get('param1', 10)
        self.param2 = kwargs.get('param2', 0.02)
        
        self.logger.info(f"Initialized with param1={self.param1}, param2={self.param2}")
    
    def on_quote(self, quote: Quote) -> Optional[TradingSignal]:
        """
        Process a quote and generate signal
        
        This is called every time new market data arrives
        """
        if not self.is_active:
            return None
        
        symbol = quote.symbol
        price = quote.last or quote.mid_price
        
        if price is None:
            return None
        
        # add price to history
        self.add_price(symbol, price)
        
        # your strategy logic here
        
        return None  # or return a TradingSignal
    
    def on_bar(self, bar: Bar) -> Optional[TradingSignal]:
        """
        Process a bar (OHLCV data)
        
        For bar-based strategies, implement this
        """
        # convert bar to quote and process
        quote = Quote(
            symbol=bar.symbol,
            timestamp=bar.timestamp,
            last=bar.close,
            open=bar.open,
            high=bar.high,
            low=bar.low,
            volume=bar.volume
        )
        
        return self.on_quote(quote)
```

### Step 3: implement strategy logic

Simple price breakout example:

```python
class BreakoutStrategy(BaseStrategy):
    """
    Simple breakout strategy
    
    BUY when price breaks above recent high
    SELL when price breaks below recent low
    """
    
    def __init__(self, symbols: List[str], lookback: int = 20, 
                 breakout_pct: float = 0.02):
        super().__init__(f"Breakout_{lookback}", symbols)
        
        self.lookback = lookback
        self.breakout_pct = breakout_pct
    
    def on_quote(self, quote: Quote) -> Optional[TradingSignal]:
        if not self.is_active:
            return None
        
        symbol = quote.symbol
        price = quote.last or quote.mid_price
        
        if price is None:
            return None
        
        # add to history
        self.add_price(symbol, price)
        
        # get price history
        prices = self.get_price_history(symbol)
        
        # need enough data
        if len(prices) < self.lookback:
            return None
        
        # recent high/low
        recent_prices = prices[-self.lookback:]
        recent_high = max(recent_prices)
        recent_low = min(recent_prices)
        
        signal = None
        
        # upside breakout
        if price > recent_high * (1 + self.breakout_pct):
            if not self.has_position(symbol):
                signal = self.create_signal(
                    symbol=symbol,
                    signal_type=SignalType.BUY,
                    price=price,
                    confidence=0.8,
                    reason=f"Upside breakout: ${price:.2f} > ${recent_high:.2f}"
                )
        
        # downside breakout
        elif price < recent_low * (1 - self.breakout_pct):
            if self.has_position(symbol):
                signal = self.create_signal(
                    symbol=symbol,
                    signal_type=SignalType.CLOSE_LONG,
                    price=price,
                    confidence=0.8,
                    reason=f"Downside breakout: ${price:.2f} < ${recent_low:.2f}"
                )
        
        return signal
```

### Step 4: use your strategy

In `main.py`:

```python
from src.strategies.my_strategy import BreakoutStrategy

strategies = [
    BreakoutStrategy(
        symbols=["AAPL", "MSFT"],
        lookback=20,
        breakout_pct=0.02  # 2%
    )
]

bot = TradingBot(strategies)
```

## Strategy lifecycle

### 1. Initialization

```python
def __init__(self, symbols, **params):
    super().__init__("StrategyName", symbols)
    # init params, indicators, state
```

### 2. Start

```python
strategy.start()  # called by bot
# is_active => True, starts processing
```

### 3. Data processing

```python
def on_quote(self, quote):
    # per quote => process, maybe return signal
    return None  # or TradingSignal
```

### 4. Signal generation

```python
signal = self.create_signal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    price=150.00,
    quantity=10,  # optional
    confidence=0.85,
    reason="My condition met"
)
return signal
```

### 5. Position updates

```python
def on_position_update(self, symbol, quantity, avg_price):
    # position changed => update state (bot calls this)
```

### 6. Fill notifications

```python
def on_fill(self, symbol, quantity, price):
    # order filled => update tracking (bot calls this)
```

### 7. Stop

```python
strategy.stop()  # bot or user
# is_active => False, stops processing
```

## Signal generation

### Signal types

```python
from src.strategies.base_strategy import SignalType

# available signal types
SignalType.BUY          # open long
SignalType.SELL         # open short (if allowed)
SignalType.CLOSE_LONG   # close long
SignalType.CLOSE_SHORT  # close short
SignalType.HOLD         # no-op
```

### Creating signals

```python
# basic
signal = self.create_signal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    price=150.00,
    reason="Price breakout"
)

# with quantity
signal = self.create_signal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    price=150.00,
    quantity=10,  # specific size
    reason="Strong signal"
)

# with confidence
signal = self.create_signal(
    symbol="AAPL",
    signal_type=SignalType.BUY,
    price=150.00,
    confidence=0.9,  # 90%
    reason="Very strong signal"
)
```

### Signal validation

Risk manager validates automatically:
- Position size limits
- Number of positions
- Daily loss limits
- Order value limits

Invalid => rejected.

## Using indicators

### Price history

```python
# add price to history
self.add_price(symbol, price)

# get history / last N
prices = self.get_price_history(symbol)
last_20 = self.get_price_history(symbol, length=20)
```

### Simple moving average

```python
import statistics

def calculate_sma(self, prices, period):
    if len(prices) < period:
        return None
    return statistics.mean(prices[-period:])

# usage
sma_20 = self.calculate_sma(prices, 20)
```

### Exponential moving average

```python
def calculate_ema(self, prices, period):
    if len(prices) < period:
        return None
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    
    for price in prices[1:]:
        ema = (price * multiplier) + (ema * (1 - multiplier))
    
    return ema
```

### RSI (relative strength index)

```python
def calculate_rsi(self, prices, period=14):
    if len(prices) < period + 1:
        return None
    
    # price changes
    changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
    
    # gains vs losses
    gains = [max(0, change) for change in changes]
    losses = [abs(min(0, change)) for change in changes]
    
    avg_gain = statistics.mean(gains[-period:])
    avg_loss = statistics.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi
```

### Bollinger bands

```python
def calculate_bollinger_bands(self, prices, period=20, num_std=2):
    if len(prices) < period:
        return None, None, None
    
    sma = statistics.mean(prices[-period:])
    std = statistics.stdev(prices[-period:])
    
    upper_band = sma + (num_std * std)
    lower_band = sma - (num_std * std)
    
    return upper_band, sma, lower_band
```

### MACD

```python
def calculate_macd(self, prices, fast=12, slow=26, signal=9):
    if len(prices) < slow:
        return None, None, None
    
    ema_fast = self.calculate_ema(prices, fast)
    ema_slow = self.calculate_ema(prices, slow)
    
    macd_line = ema_fast - ema_slow
    
    # would need MACD history for signal line (simplified here)
    return macd_line, None, None
```

## Testing strategies

### Monitor mode

No orders, just signals:

```bash
# in .env
ENABLE_TRADING=false
```

```python
# main.py
bot = TradingBot([YourStrategy(symbols)])
bot.initialize()
bot.run()
```

Watch logs for signals.

### Paper trading

Simulated orders:

```bash
# in .env
ENABLE_TRADING=true
PAPER_TRADING=true
IBKR_PORT=7497
```

### Backtesting (manual)

Historical data:

```python
from src.market_data.yahoo_provider import YahooFinanceProvider

# get history
provider = YahooFinanceProvider()
provider.connect()
bars = provider.get_historical_bars("AAPL", period="1mo", interval="1d")

# run strategy over bars
strategy = YourStrategy(["AAPL"])
strategy.start()

for bar in bars:
    signal = strategy.on_bar(bar)
    if signal:
        print(f"Signal: {signal}")

print(strategy.get_performance_summary())
```

## Best practices

### 1. Keep it simple

```python
# good => simple, clear
if price > sma_50:
    return buy_signal()

# bad => too many conditions
if (price > sma_50 and rsi < 70 and macd > signal 
    and volume > avg_volume * 1.5 and day_of_week != 5):
    return buy_signal()
```

### 2. Handle missing data

```python
# good => check None
price = quote.last or quote.mid_price
if price is None:
    return None

# bad => assumes data exists
price = quote.last  # could be None
signal = self.calculate(price)  # crash
```

### 3. Validate parameters

```python
def __init__(self, symbols, period=14):
    super().__init__("Strategy", symbols)
    
    # validate
    if period < 2:
        raise ValueError("Period must be at least 2")
    if not symbols:
        raise ValueError("Must provide symbols")
    
    self.period = period
```

### 4. Use logging

```python
# important events
self.logger.info(f"MA crossover detected for {symbol}")

# debug
self.logger.debug(f"SMA: {sma:.2f}, Price: {price:.2f}")

# errors
self.logger.error(f"Failed to calculate indicator: {e}")
```

### 5. Track state properly

```python
# good => track previous
self.prev_sma = {}

def on_quote(self, quote):
    current_sma = self.calculate_sma(prices, 20)
    prev_sma = self.prev_sma.get(symbol)
    
    # crossover?
    if prev_sma and current_sma > prev_sma:
        signal = buy_signal()
    
    self.prev_sma[symbol] = current_sma

# bad => no state, can't detect crossover
def on_quote(self, quote):
    sma = self.calculate_sma(prices, 20)
    if sma > ???:
        signal = buy_signal()
```

### 6. Don't overtrade

```python
# good => check position first
if not self.has_position(symbol):
    return buy_signal()

# bad => might already be long
return buy_signal()
```

## Example strategies

### Mean reversion strategy

```python
class MeanReversionStrategy(BaseStrategy):
    """Buy when price is below SMA, sell when above"""
    
    def __init__(self, symbols, period=20, threshold=0.02):
        super().__init__(f"MeanReversion_{period}", symbols)
        self.period = period
        self.threshold = threshold
    
    def on_quote(self, quote):
        if not self.is_active:
            return None
        
        symbol = quote.symbol
        price = quote.last or quote.mid_price
        if not price:
            return None
        
        self.add_price(symbol, price)
        prices = self.get_price_history(symbol)
        
        if len(prices) < self.period:
            return None
        
        sma = statistics.mean(prices[-self.period:])
        deviation = (price - sma) / sma
        
        # buy when below mean
        if deviation < -self.threshold and not self.has_position(symbol):
            return self.create_signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=price,
                reason=f"Below SMA by {abs(deviation):.1%}"
            )
        
        # sell when back above mean
        if deviation > 0 and self.has_position(symbol):
            return self.create_signal(
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=price,
                reason=f"Reverted to mean"
            )
        
        return None
```

### RSI strategy

```python
class RSIStrategy(BaseStrategy):
    """RSI-based strategy: buy oversold, sell overbought"""
    
    def __init__(self, symbols, period=14, oversold=30, overbought=70):
        super().__init__(f"RSI_{period}", symbols)
        self.period = period
        self.oversold = oversold
        self.overbought = overbought
    
    def calculate_rsi(self, prices):
        # ... (implementation from above)
        pass
    
    def on_quote(self, quote):
        if not self.is_active:
            return None
        
        symbol = quote.symbol
        price = quote.last or quote.mid_price
        if not price:
            return None
        
        self.add_price(symbol, price)
        prices = self.get_price_history(symbol)
        
        rsi = self.calculate_rsi(prices)
        if rsi is None:
            return None
        
        # buy when oversold
        if rsi < self.oversold and not self.has_position(symbol):
            return self.create_signal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                price=price,
                confidence=0.7,
                reason=f"RSI oversold: {rsi:.1f}"
            )
        
        # sell when overbought
        if rsi > self.overbought and self.has_position(symbol):
            return self.create_signal(
                symbol=symbol,
                signal_type=SignalType.CLOSE_LONG,
                price=price,
                confidence=0.7,
                reason=f"RSI overbought: {rsi:.1f}"
            )
        
        return None
```

## Next steps

1. Study the example strategies
2. Start with simple ones
3. Test in monitor mode
4. Paper trade for a while
5. Keep a journal, iterate
6. Improve from there

---

