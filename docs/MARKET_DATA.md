# Market Data Options Guide

This guide explains all available market data options for the IBKR TWS Trading Bot, with a focus on **FREE alternatives** for development and testing.

## Overview

Several options for market data — from free to paid:

| Provider | Cost | Real-time | API Key | Rate Limit | Best For |
|----------|------|-----------|---------|------------|----------|
| **Yahoo Finance** | FREE | No (15-20 min delay) | No | None | Development & Testing |
| **IBKR Delayed** | FREE | No (15-20 min delay) | No | None | Development & Testing |
| **IBKR Paper Trading** | FREE | Simulated | No | None | Strategy Testing |
| **Polygon.io** | FREE tier | Yes | Yes | 5 calls/min | Light Production |
| **Alpha Vantage** | FREE tier | Yes | Yes | 5 calls/min | Light Usage |
| **IBKR Real-time** | $15.0-$20.0/mo | Yes | No | None | Production Trading |

## Recommended setup for development

### Best free setup: Yahoo Finance

No cost, no API keys.

```bash
# in .env
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_FALLBACK=yahoo,ibkr
```

Why Yahoo:
- -> completely free
- -> no API key
- -> no rate limits (reasonable use)
- -> reliable, historical data included
- -> good for strategy dev

What you get:
- Real-time quotes (15-20 min delayed)
- Historical OHLCV data
- Intraday data (1-minute intervals)
- Volume data
- Stock splits and dividends

## Free market data options

### 1. Yahoo Finance (recommended)

#### Setup

No setup — just set:

```bash
MARKET_DATA_PROVIDER=yahoo
```

#### Usage Example

```python
from src.market_data.yahoo_provider import YahooFinanceProvider

provider = YahooFinanceProvider()
provider.connect()

# get current quote
quote = provider.get_quote("AAPL")
print(f"AAPL: ${quote.last:.2f}")

# get historical data
bars = provider.get_historical_bars("AAPL", period="1d", interval="5m")
print(f"Got {len(bars)} 5-minute bars for today")
```

#### Limitations

- delayed data => 15–20 min behind real-time
- no true streaming => poll for updates
- unofficial API => could change (rarely does)

### 2. IBKR delayed data (free)

Delayed market data free with any IBKR account.

#### Setup

```bash
# in .env
MARKET_DATA_PROVIDER=ibkr
IBKR_USE_DELAYED_DATA=true
```

#### Enable in TWS

1. Open TWS/Gateway
2. **Account → Market Data Subscriptions**
3. **US Equity and Options Add-On Streaming Bundle** => **Delayed (Free)**

#### Advantages

- -> official IBKR data, same source as paid (just delayed)
- -> works with trading out of the box

#### Limitations

- -> 15–20 min delay, needs TWS/Gateway connected

### 3. IBKR paper trading (free)

Paper trading => simulated data, good for testing.

#### Setup

```bash
# in .env
IBKR_PORT=7497                    # paper trading port
PAPER_TRADING=true
IBKR_USE_DELAYED_DATA=true
```

#### Get paper account

1. [IBKR Account Management](https://www.interactivebrokers.com/) → **Settings → Paper Trading**
2. Create paper account (instant, free)
3. Use paper username/password in TWS

What you get:
- simulated env, full API, historical data
- test strategies with no risk

## Paid options (optional)

### IBKR real-time market data

For production you’ll want real-time eventually.

#### Pricing (as of 2024)

- US Securities Snapshot => $1.50/mo
- US Equity and Options Bundle => $4.50/mo
- Free if => $30+ commissions/month

#### Subscribe

1. IBKR Account Management → **Account → Market Data Subscriptions**
2. **US Equity and Options Add-On Streaming Bundle** => **Real-time**

#### Configuration

```bash
# in .env
MARKET_DATA_PROVIDER=ibkr
IBKR_USE_DELAYED_DATA=false       # use real-time
```

### Polygon.io

Good for production bots, has free tier.

#### Free tier

- 5 calls/min, real-time + historical, WebSocket

#### Setup

1. [polygon.io](https://polygon.io/) => sign up, get API key
2. Then:

```bash
# in .env
MARKET_DATA_PROVIDER=polygon
POLYGON_API_KEY=your_api_key_here
```

#### Implementation

You’d add a Polygon provider (not in base bot):

```python
# src/market_data/polygon_provider.py
from polygon import RESTClient
from src.market_data.base_provider import MarketDataProvider

class PolygonProvider(MarketDataProvider):
    def __init__(self, api_key):
        super().__init__("Polygon")
        self.client = RESTClient(api_key)
    
    # implement required methods...
```

### Alpha Vantage

Another free option, decent API.

#### Free tier

- 5 calls/min, 500/day, real-time + historical

#### Setup

1. API key at [alphavantage.co](https://www.alphavantage.co/)
2. Then:

```bash
# in .env
MARKET_DATA_PROVIDER=alphavantage
ALPHAVANTAGE_API_KEY=your_api_key_here
```

## Multi-provider strategy

Multiple providers => redundancy.

```bash
# primary => Yahoo (free, reliable)
MARKET_DATA_PROVIDER=yahoo

# fallbacks => IBKR, then Polygon
MARKET_DATA_FALLBACK=ibkr,polygon
```

Bot will: try primary => on fail try IBKR => then Polygon; logs switches.

## Choosing the right provider

### Strategy development
-> Yahoo Finance. Free, no setup, good for testing logic.

### Paper trading
-> IBKR delayed + paper account. Full workflow, same as live, no risk.

### Backtesting
-> Yahoo. Lots of history, free, decent quality.

### Production (small scale)
-> Polygon free tier. Real-time, 5 calls/min enough for small setups.

### Production (active trading)
-> IBKR real-time. Best latency, direct from broker, most reliable.

## Implementation example

### Using multiple providers

```python
from src.market_data.market_data_manager import MarketDataManager
from src.market_data.yahoo_provider import YahooFinanceProvider
from src.market_data.ibkr_provider import IBKRMarketDataProvider

# create providers
yahoo = YahooFinanceProvider()
ibkr = IBKRMarketDataProvider(ibkr_client)

# manager with fallback
manager = MarketDataManager(
    primary_provider=yahoo,
    fallback_providers=[ibkr]
)

manager.connect()

# get quote => Yahoo first, failover to IBKR if needed
quote = manager.get_quote("AAPL")
```

### Provider-specific features

```python
# yahoo => historical data
bars = yahoo_provider.get_historical_bars(
    symbol="AAPL",
    period="1mo",     # 1 month
    interval="1d"     # daily bars
)

# ibkr => streaming quotes
ibkr_provider.subscribe_quotes(
    symbols=["AAPL", "MSFT"],
    callback=on_quote_update
)
```

## Performance considerations

### Delayed vs real-time

For most strategies delayed is fine in dev.

Works with delayed:
- -> swing/position trading, MA crossovers, momentum, fundamental

Needs real-time:
- -> HFT, market making, arbitrage, scalping

### Rate limits

Yahoo: no official limit. Don’t abuse lol (>2000 req/hr can throttle). Caching helps.

Free APIs (Polygon, Alpha Vantage): respect limits, cache a lot, maybe upgrade for prod.

IBKR: no strict limit; don’t spam (50+ msg/s). Prefer snapshot where possible.

## Troubleshooting

### Yahoo issues

"No data available" => symbol may be delisted/invalid.
```python
# check symbol validity
import yfinance as yf
ticker = yf.Ticker("AAPL")
print(ticker.info)  # should return data
```

Slow responses => use caching.
```python
# already in market_data_manager
quotes = manager.get_quotes(symbols, use_cache=True)
```

### IBKR data issues

"No market data permissions" => subscribe to delayed in TWS.

"Market data farm disconnected" => usually informational, reconnects on its own.

### API rate limits

"Rate limit exceeded" => add backoff:
```python
import time

def get_quote_with_retry(symbol, max_retries=3):
    for attempt in range(max_retries):
        try:
            return provider.get_quote(symbol)
        except RateLimitError:
            if attempt < max_retries - 1:
                time.sleep(60)  # wait 1 min
            else:
                raise
```

## Data quality comparison

| Feature | Yahoo | IBKR Delayed | IBKR Real-time | Polygon |
|---------|-------|--------------|----------------|---------|
| Accuracy | Good | Excellent | Excellent | Excellent |
| Latency | 15-20 min | 15-20 min | < 1 sec | < 1 sec |
| Historical | Excellent | Good | Good | Excellent |
| Splits/Dividends | Yes | Yes | Yes | Yes |
| Pre/Post Market | Limited | Yes | Yes | Yes |
| Options | No | Yes | Yes | No (Free) |

## Best practices

1. Start free => Yahoo first.
2. Test thoroughly => paper + IBKR delayed.
3. Monitor => track provider reliability.
4. Use fallbacks => multiple providers.
5. Cache a lot => fewer API calls.
6. Upgrade when ready => real-time for prod.

## Additional resources

- [Yahoo Finance Library](https://github.com/ranaroussi/yfinance)
- [Polygon.io API Docs](https://polygon.io/docs)
- [Alpha Vantage Docs](https://www.alphavantage.co/documentation/)
- [IBKR Market Data Info](https://www.interactivebrokers.com/en/index.php?f=14193)

---

Goal in dev => test strategy logic, not make money yet. Delayed free data is enough. Once it’s proven, then real-time.

Enjoy :)

