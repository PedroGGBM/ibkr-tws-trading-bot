# IBKR TWS Trading Bot

University of St Andrews FinTech Society, Artificial Intelligence Division

A well-architected trading bot for Interactive Brokers TWS/Gateway with free market data alternatives for development and testing

## Key Features

### Architecture (enforceable)
- _Modular Design_: Clean separation of concerns with different modules for connections, market data, strategies, and risk management
- _Error Handling_: Error handling and automatic recovery
- _Logging_: Structured logging with file rotation and trade-specific logs
- _Configuration Management_: Environment-based config with validation
- _Type Hints_: Full type annotations for better code quality

*Note: This is what will make collaboration between the team intuitive and easy (hopefully)

### Free Market Data Options
**Don't need expensive market data subscriptions to develop/test the bot :)**

1. **Yahoo Finance** (Recommended for dev)
   - Completely FREE - no API key needed
   - Real-time quotes (15-20 min delayed)
   - Historical data
   - No rate limits for reasonable use

2. **IBKR Delayed Data** (FREE)
   - 15-20 minute delayed market data
   - Works with paper trading account
   - No subscription required
3. **IBKR Paper Trading Account** (FREE)
   - Simulated trading environment
   - Test strategies risk-free
   - Full API access

### 🛡️ Risk Management
- Position size limits
- Maximum concurrent positions
- Daily loss limits
- Order value validation
- Portfolio exposure tracking
- Emergency stop conditions (*)

### 📊 Strategy Framework
- Abstract base class for easy strategy development
- Built-in performance tracking
- Signal generation and validation (alpha signals)
- Position tracking
- Included example strategies (developed by @pedroggbm):
  - Moving Average Crossover
  - Momentum Strategy

### 🔌 Multi-Provider Market Data
- Intuitive provider switching
- Automatic failover
- Quote caching
- Provider health monitoring (*)

## Project Structure

```
ibkr-tws-bot/
├── config.py                      # config management
├── main.py                        # main entry point
├── requirements.txt               # Python dependencies
├── .env.example                   # env vars template
│
├── src/
│   ├── bot.py                     # main bot orchestrator
│   │
│   ├── connection/                # IBKR connection modules
│   │   └── ibkr_client.py         # enhanced IBKR client (beyond basic entry point)
│   │
│   ├── market_data/               # market data providers
│   │   ├── base_provider.py       # provider interface
│   │   ├── market_data_manager.py # multi-provider manager
│   │   ├── yahoo_provider.py      # Yahoo Finance (FREE)
│   │   └── ibkr_provider.py       # IBKR market data (*)
│   │
│   ├── strategies/                # trading strategies
│   │   ├── base_strategy.py       # strategy base class
│   │   ├── moving_average_strategy.py
│   │   └── momentum_strategy.py
│   │
│   ├── risk/                      # risk management
│   │   └── risk_manager.py        # position & risk controls
│   │
│   └── utils/                     # utils
│       └── logger.py              # logging system
│
├── docs/                          # documentation
│   ├── SETUP.md                   # setup guide
│   ├── MARKET_DATA.md             # market data options
│   └── STRATEGY_DEVELOPMENT.md    # strategy guide
│
└── logs/                          # log files (auto-created)
```

## Quick Start

### 1. Prerequisites

- **Python 3.8+**
- **IBKR Account** (Paper Trading is FREE!)
- **TWS or IB Gateway** installed and running

### 2. Installation

```bash
# clone repo
cd ibkr-tws-trading-bot

# create virtual env
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# instal dependencies
pip install -r requirements.txt
```

### 3. Setup IBKR TWS/Gateway

1. **Download TWS or IB Gateway**: https://www.interactivebrokers.com/en/trading/tws.php

2. **Enable API Access**:
   - Open TWS/Gateway
   - Go to: **Edit → Global Configuration → API → Settings**
   -  \ Enable ActiveX and Socket Clients
   -  \ Read-Only API
   -  \ Port: 7497 (paper trading) or 7496 (live)
   -  \ Trusted IP: 127.0.0.1 (!!! -> for now local)
   -  \ **Important**: Uncheck "Download open orders on connection" (can cause issues)

3. **Get Paper Trading Account** (if don't have one):
   - Log into IBKR Account Management
   - Go to: Settings → Paper Trading
   - Create paper trading account (instant, free)

### 4. Configuration

Copy example env file:

```bash
cp .env.example .env
```

Edit `.env` with own settings:

```bash
# IBKR connection
IBKR_HOST=127.0.0.1
IBKR_PORT=7497                    # paper trading
IBKR_CLIENT_ID=1
IBKR_USE_DELAYED_DATA=true        # FREE delayed data

# market data (FREE options)
MARKET_DATA_PROVIDER=yahoo        # use Yahoo Finance (FREE)
MARKET_DATA_FALLBACK=yahoo,ibkr   # fallbacks (for data provider manager)

# trading (SAFETY FEATURES)
ENABLE_TRADING=false              # set to true to enable actual trading (!!! DANGER)
PAPER_TRADING=true                # always use paper trading for testing!
## position config for testing
MAX_POSITION_SIZE=10000.0
MAX_POSITIONS=5
MAX_DAILY_LOSS=500.0

# logging
LOG_LEVEL=INFO
```

### 5. Run the Bot

```bash
python main.py
```

## Using FREE Market Data

### Option 1: Yahoo Finance (Recommended)

**No setup required** -> just set in `.env`:

```bash
MARKET_DATA_PROVIDER=yahoo
```

**Pros:**
- Completely free
- No API key needed
- No rate limits (reasonable use)
- Good for development

**Cons:**
- 15-20 min delayed
- No true real-time streaming (rip)

### Option 2: IBKR Delayed Data (FREE)

IBKR's free delayed data:

```bash
MARKET_DATA_PROVIDER=ibkr
IBKR_USE_DELAYED_DATA=true
```

**Pros:**
- Free with IBKR account
- Direct from IBKR
- Works with paper trading

**Cons:**
- 15-20 min delayed

### Option 3: Hybrid Approach

Use both for redundancy:

```bash
MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_FALLBACK=yahoo,ibkr
```

The bot will automatically switch providers if one fails (or so that is the idea)

## Example Usage

### Running with Different Strategies

Edit `main.py` to config strategies (very elementary still):

```python
from src.strategies.moving_average_strategy import MovingAverageStrategy
from src.strategies.momentum_strategy import MomentumStrategy

symbols = ["AAPL", "MSFT", "GOOGL", "TSLA"]

strategies = [
    # MA Crossover
    MovingAverageStrategy(symbols=symbols, short_period=20, long_period=50),
    
    # Momentum
    MomentumStrategy(symbols=symbols, period=14, buy_threshold=2.0),
]
```

### Monitor Mode (No Trading)

Safe mode to test w/out placing orders:

```bash
# .env
ENABLE_TRADING=false
```

The bot will:
- Connect to IBKR
- Receive market data
- Generate signals
- !!! NOT place any orders

### Paper Trading Mode

Test with simulated money (paper trading for IBKR):

```bash
# .env
ENABLE_TRADING=true
PAPER_TRADING=true
IBKR_PORT=7497
```

### Live Trading Mode (!!!)

**Only when ready (please)**

```bash
# .env
ENABLE_TRADING=true
PAPER_TRADING=false
IBKR_PORT=7496
```

## Creating Own Strategy

See `docs/STRATEGY_DEVELOPMENT.md` for detailed guide.(please)

Quick example:

```python
from src.strategies.base_strategy import BaseStrategy, SignalType, TradingSignal
from src.market_data.base_provider import Quote

class MyStrategy(BaseStrategy):
    def __init__(self, symbols):
        super().__init__("MyStrategy", symbols)
    
    def on_quote(self, quote: Quote):
        # strategy logic here!!
        price = quote.last or quote.mid_price
        
        # example -> buy if price drops 2%
        if self.should_buy(price):
            return self.create_signal(
                symbol=quote.symbol,
                signal_type=SignalType.BUY,
                price=price,
                reason="Price dropped 2%"
            )
        
        return None
```

## Risk Management

The bot includes very elementary risk management.

The idea is to extend this further on with Markowitz portfolio optimization and with it Monte Carlo simulation, etc, for better risk management/further signals; for now they are limited to:

- **Position Limits**: Max position size and # of positions
- **Daily Loss Limit**: Automatic stop if daily loss exceeds limit
- **Order Validation**: All orders validated before execution
- **Emergency Stop**: Automatic shutdown on critical conditions

Configure in `.env`:

```bash
MAX_POSITION_SIZE=10000.0      # max $10k per position (for testing)
MAX_POSITIONS=5                # max 5 concurrent positions
MAX_DAILY_LOSS=500.0           # stop if lose $500 in a day (for testing)
MAX_ORDER_VALUE=5000.0         # max $5k per order
```

## Logging

Logs are automatically created in `logs/`:

- `tradingbot.log` - general bot activity
- `trades_YYYYMMDD.log` - trade-specific logs

View logs in real-time:

```bash
tail -f logs/tradingbot.log
```

## Troubleshooting

### "Connection refused" Error

- ✅ Check TWS/Gateway is running
- ✅ Verify port number (7497 for paper, 7496 for live)
- ✅ Enable API in TWS settings
- ✅ Add 127.0.0.1 to trusted IPs

### "Market data not available" Error

- ✅ Use delayed data: `IBKR_USE_DELAYED_DATA=true`
- ✅ Or switch to Yahoo Finance: `MARKET_DATA_PROVIDER=yahoo`

### "No valid order ID" Error

- ✅ Wait a few seconds after connecting
- ✅ Restart TWS/Gateway
- ✅ Check client ID is unique

## Additional Resources

- [IBKR API Documentation](https://interactivebrokers.github.io/tws-api/)
- [Yahoo Finance Python](https://github.com/ranaroussi/yfinance)
- [Setup Guide](docs/SETUP.md)
- [Market Data Options](docs/MARKET_DATA.md)
- [Strategy Development](docs/STRATEGY_DEVELOPMENT.md)

## Disclaimer

**This software is for educational purposes only, particuarly for the FinTech Society of the University of St Andrews**

- Trading involves risk of loss
- Past performance does not guarantee future results
- Test thoroughly with paper trading before going live
- Use at your own risk (!!!)
- The authors (listed below) are not responsible for any financial losses

## 📄 License

See [LICENSE](LICENSE) file.

## 👤 Author

Pedro Gronda Garrigues

... (add yall's names here!)