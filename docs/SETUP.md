# Complete Setup Guide

Setup for the IBKR TWS Trading Bot from scratch: accounts, software, config.

## Prerequisites

### Required
- Python 3.8+
- Interactive Brokers account (or create one)
- Basic Python + terminal

### Optional
- Git, code editor (VS Code, PyCharm, etc.)

## Step-by-step setup

### Step 1: IBKR account

#### 1.1 Create account

No account yet:
1. [Interactive Brokers](https://www.interactivebrokers.com/) → "Open Account"
2. Complete registration (approval often 1–2 business days)

#### 1.2 Paper trading

No need to fund the account to start :)

1. [IBKR Account Management](https://www.interactivebrokers.com/) → **Settings → Paper Trading**
2. "Create Paper Trading Account" => save credentials
3. Instant, free.

### Step 2: Install TWS or IB Gateway

TWS or IB Gateway required. Gateway preferred for bots.

#### 2.1 Download

- **IB Gateway** (recommended for bots): [IB Gateway](https://www.interactivebrokers.com/en/trading/ibgateway-stable.php) — lightweight, no GUI
- **TWS**: [TWS](https://www.interactivebrokers.com/en/trading/tws.php) — full platform

#### 2.2 Install

**Linux:**
```bash
# download installer (replace with latest if needed)
wget https://download2.interactivebrokers.com/installers/ibgateway/stable-standalone/ibgateway-stable-standalone-linux-x64.sh

# make executable, run
chmod +x ibgateway-stable-standalone-linux-x64.sh
./ibgateway-stable-standalone-linux-x64.sh
```

**macOS:** DMG => Applications => launch.

**Windows:** EXE => run installer.

### Step 3: Configure TWS/Gateway

#### 3.1 Launch

Paper: use paper username/password, select "Paper Trading".

#### 3.2 Enable API

1. TWS/Gateway → **Edit → Global Configuration → API → Settings**
2. Set:
   - Enable ActiveX and Socket Clients
   - Socket port: 7497 (paper) or 7496 (live)
   - Master API client ID: blank or 0
   - Read-Only API: off (we need to place orders)
   - Download open orders on connection: off
   - Trusted IPs: 127.0.0.1
3. OK, Apply.

#### 3.3 Market data (free delayed)

TWS → **Account → Market Data Subscriptions** → "US Equity and Options Add-On Streaming Bundle" => **Delayed (Free)** or **Snapshot (Free)**. Subscribe.

### Step 4: Install bot

#### 4.1 Download

Git: `git clone <repository-url>` then `cd ibkr-tws-bot`. Or ZIP => extract => cd into folder.

#### 4.2 Virtual environment

**Linux/macOS:**
```bash
# create and activate
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```powershell
python -m venv venv
venv\Scripts\activate
```

Prompt should show `(venv)`.

#### 4.3 Dependencies

```bash
# upgrade pip, then install
pip install --upgrade pip
pip install -r requirements.txt
```

Adds: `ibapi`, `yfinance`, `python-dotenv`, `pandas`, `numpy`.

### Step 5: Configuration

#### 5.1 Create .env

```bash
cp .env.example .env
# or: touch .env
```

#### 5.2 Edit .env

```bash
# =============================================================================
# ibkr connection
# =============================================================================

IBKR_HOST=127.0.0.1

# port: 7497 paper, 7496 live
IBKR_PORT=7497

# client ID (unique per bot if multiple)
IBKR_CLIENT_ID=1

# account ID optional, auto-detected
IBKR_ACCOUNT_ID=

# free delayed data
IBKR_USE_DELAYED_DATA=true

# =============================================================================
# market data
# =============================================================================

MARKET_DATA_PROVIDER=yahoo
MARKET_DATA_FALLBACK=yahoo,ibkr

# only if using Polygon / Alpha Vantage
POLYGON_API_KEY=
ALPHAVANTAGE_API_KEY=

# =============================================================================
# trading - safety first
# =============================================================================

# set false until you're ready to trade
ENABLE_TRADING=false

PAPER_TRADING=true

# risk limits
MAX_POSITION_SIZE=10000.0      # max $10k per position
MAX_POSITIONS=5                # max 5 positions
MAX_DAILY_LOSS=500.0          # stop if lose $500/day
MAX_ORDER_VALUE=5000.0        # max $5k per order

DEFAULT_ORDER_TYPE=LMT        # lmt = limit, mkt = market

# =============================================================================
# logging
# =============================================================================

LOG_LEVEL=INFO
LOG_DIR=logs
LOG_TO_FILE=true
LOG_TO_CONSOLE=true
```

### Step 6: Verify installation

#### 6.1 Test IBKR connection

`test_connection.py`:

```python
from src.connection.ibkr_client import IBKRClient
from src.utils.logger import get_logger

logger = get_logger("Test")

# create client (7497 = paper)
client = IBKRClient(
    host="127.0.0.1",
    port=7497,
    client_id=1,
    use_delayed_data=True
)

if client.connect_and_run():
    logger.info("Connected to IBKR")
    logger.info(f"Account: {client.account_summary}")
    client.disconnect_gracefully()
else:
    logger.error("Connection failed")
```

Run: `python test_connection.py`. Expect "Connected. Next valid order ID" and account info.

#### 6.2 Test market data

`test_market_data.py`:

```python
from src.market_data.yahoo_provider import YahooFinanceProvider
from src.utils.logger import get_logger

logger = get_logger("Test")
provider = YahooFinanceProvider()
provider.connect()
quote = provider.get_quote("AAPL")

if quote:
    logger.info(f"AAPL: last=${quote.last:.2f} bid={quote.bid} ask={quote.ask}")
else:
    logger.error("No quote")
```

Run: `python test_market_data.py`.

### Step 7: First run

#### 7.1 Start TWS/Gateway

TWS or Gateway running, paper account logged in, API on port 7497.

#### 7.2 Run in monitor mode (no trading)

```bash
# in .env: ENABLE_TRADING=false
python main.py
```

Expected:
```
============================================================
IBKR TWS Trading Bot - Configuration Summary
============================================================

[IBKR Connection]
  Host: 127.0.0.1:7497
  Client ID: 1
  Mode: PAPER TRADING
  Delayed Data: True

[Market Data]
  Primary Provider: yahoo
  Fallback Providers: yahoo, ibkr

[Trading Parameters]
  Trading Enabled: False
  Max Position Size: $10,000.00
  Max Positions: 5
  Max Daily Loss: $500.00

============================================================

INFO | Connecting to IBKR...
INFO | Successfully connected to IBKR
INFO | Yahoo Finance provider ready (no auth required)
INFO | Bot started! Update interval: 5.0s
INFO | Monitoring 3 symbols: ['AAPL', 'MSFT', 'GOOGL']
```

#### 7.3 Logs

`tail -f logs/tradingbot.log`

#### 7.4 Stop

`Ctrl+C`.

### Step 8: Enable paper trading

When monitoring looks good:

#### 8.1 .env

```bash
# enable trading, stay paper
ENABLE_TRADING=true
PAPER_TRADING=true
```

#### 8.2 Port

`IBKR_PORT=7497` for paper.

#### 8.3 Run

`python main.py`. Bot will connect, get data, generate signals, place orders (paper only).

#### 8.4 Positions

TWS Portfolio tab or `logs/trades_YYYYMMDD.log`.

## Troubleshooting

### Connection refused (127.0.0.1:7497)

-> TWS/Gateway running? Port: paper 7497 (TWS) or 4002 (Gateway), live 7496/4001. API enabled in TWS? Firewall?

### Connection closed right after connect

-> **Edit → Global Configuration → API → Settings**: enable ActiveX/Socket, add 127.0.0.1 to trusted IPs. Restart TWS/Gateway.

### No market data

-> `MARKET_DATA_PROVIDER=yahoo` or TWS **Account → Market Data Subscriptions** (delayed), or `IBKR_USE_DELAYED_DATA=true`.

### ModuleNotFoundError: ibapi

```bash
# activate venv first
source venv/bin/activate      # linux/macOS
source venv/bin/activate.fish # use fish if you're cool
venv\Scripts\activate         # windows (L)

pip install -r requirements.txt
```

### Permission denied (Linux/macOS)

```bash
# own files, then
sudo chown -R $USER:$USER .
chmod +x *.py
```

## Next steps

1. **Code** — read `main.py`, strategy examples, market data providers.
2. **Config** — risk limits, symbols, log level.
3. **Strategy** — `docs/STRATEGY_DEVELOPMENT.md`, examples, your own logic.
4. **Test** — monitor mode for a while, then paper trade; check risk limits.
5. **Live** (when ready) — small size first, monitor, scale up.

## Learning resources

- [IBKR API](https://interactivebrokers.github.io/tws-api/)
- [Python IBAPI](https://www.interactivebrokers.com/en/software/api/apiguide/python/python.htm)
- [Yahoo Finance (yfinance)](https://github.com/ranaroussi/yfinance)

## Setup checklist

- [ ] IBKR account
- [ ] Paper account
- [ ] TWS/Gateway installed, API enabled
- [ ] Python 3.8+, venv, deps
- [ ] `.env` configured
- [ ] Connection + market data tests pass
- [ ] Monitor mode + paper trading tried
- [ ] Risk limits understood

---

Ready :D

