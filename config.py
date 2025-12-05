"""
Configuration management for IBKR TWS Trading Bot

This module handles all config settings including:
 - IBKR connection params
 - Market data proivder settings
 - Trading parameters and risk limits
 - Logging configuration

@author: Pedro Gronda Garrigues
"""

# imports
import os
from dataclasses import dataclass
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# load env variables
load_dotenv()

@dataclass
class IBKRConfig:
    """IBKR TWS/Gateway connection config"""

    # connection settings
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1

    # accoutn settings
    account_id: Optional[str] = None

    # market data settings
    use_delayed_data: bool = True # free delayed data (15-20ms delay)

    @classmethod
    def from_env(cls) -> 'IBKRConfig':
        """Load config from environment variables"""
        return cls(
            host=os.getenv("IBKR_HOST", "127.0.0.1"),
            port=int(os.getenv("IBKR_PORT", "7497")),
            client_id=int(os.getenv("IBKR_CLIENT_ID", "1")),
            account_id=os.getenv("IBKR_ACCOUNT_ID"),
            use_delayed_data=os.getenv("IBKR_USE_DELAYED_DATA", "true").lower() == "true"
        )

@dataclass
class MarketDataConfig:
    """Market data provider configuration
    
    Supports multiple providers as alts to IBKR paid subscriptions:
    - IBKR historical data (free)
    - Polygon.io (free tier: 5 API calls/min)
    - Alpha Vantage (free tier: 5 API calls/min, 500/day)
    - Yahoo Finance (free, no API key needed)

    These calls are subject to change!
    """
    
    # primary provider: 'ibkr', 'polygon', 'alphavantage', 'yahoo'
    primary_provider: str = "ibkr"
    
    # falbback providers in order of pref
    fallback_providers: list = None
    
    # API keys external providers
    polygon_api_key: Optional[str] = None
    alphavantage_api_key: Optional[str] = None
    
    def __post_init__(self):
        if self.fallback_providers is None:
            self.fallback_providers = ['yahoo', 'ibkr']
    
    @classmethod
    def from_env(cls) -> 'MarketDataConfig':
        """Load configuration from env vars"""
        fallback = os.getenv("MARKET_DATA_FALLBACK", "yahoo,ibkr").split(",")
        return cls(
            primary_provider=os.getenv("MARKET_DATA_PROVIDER", "ibkr"),
            fallback_providers=fallback,
            polygon_api_key=os.getenv("POLYGON_API_KEY"),
            alphavantage_api_key=os.getenv("ALPHAVANTAGE_API_KEY")
        )


@dataclass
class TradingConfig:
    """Trading and risk management config"""
    
    # simple risk management metrics
    max_position_size: float = 10000.0  # max position size in USD
    max_positions: int = 5              # max num of concurrent positions
    max_daily_loss: float = 500.0       #  max daily loss in USD
    max_order_value: float = 5000.0     # max single order value
    
    # trading params
    enable_trading: bool = False  # safety -> require explicit enable
    paper_trading: bool = True    # use paper trading by default
    
    # order defaults
    default_order_type: str = "LMT"  # LMT, MKT, STP, etc.
    
    @classmethod
    def from_env(cls) -> 'TradingConfig':
        """Load config from env vars"""
        return cls(
            max_position_size=float(os.getenv("MAX_POSITION_SIZE", "10000.0")),
            max_positions=int(os.getenv("MAX_POSITIONS", "5")),
            max_daily_loss=float(os.getenv("MAX_DAILY_LOSS", "500.0")),
            max_order_value=float(os.getenv("MAX_ORDER_VALUE", "5000.0")),
            enable_trading=os.getenv("ENABLE_TRADING", "false").lower() == "true",
            paper_trading=os.getenv("PAPER_TRADING", "true").lower() == "true",
            default_order_type=os.getenv("DEFAULT_ORDER_TYPE", "LMT")
        )


@dataclass
class LoggingConfig:
    """Logging config"""
    
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    log_dir: Path = Path("logs")
    log_to_file: bool = True
    log_to_console: bool = True
    
    # rotation settings
    max_bytes: int = 10485760  # 10MB
    backup_count: int = 5
    
    @classmethod
    def from_env(cls) -> 'LoggingConfig':
        """Load config from env vars"""
        return cls(
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            log_dir=Path(os.getenv("LOG_DIR", "logs")),
            log_to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
            log_to_console=os.getenv("LOG_TO_CONSOLE", "true").lower() == "true"
        )


class Config:
    """Main config class that aggregates all config sections"""
    
    def __init__(self):
        self.ibkr = IBKRConfig.from_env()
        self.market_data = MarketDataConfig.from_env()
        self.trading = TradingConfig.from_env()
        self.logging = LoggingConfig.from_env()
    
    def validate(self) -> bool:
        """Validate config settings"""
        errors = []
        
        # validate IBKR connection
        if self.ibkr.port not in [7496, 7497, 4001, 4002]:
            errors.append(f"ERROR: Invalid IBKR port: {self.ibkr.port}. Use 7497 (paper) or 7496 (live)")
        
        # validate market data
        valid_providers = ['ibkr', 'polygon', 'alphavantage', 'yahoo']
        if self.market_data.primary_provider not in valid_providers:
            errors.append(f"ERROR: Invalid market data provider: {self.market_data.primary_provider}")
        
        if self.market_data.primary_provider == 'polygon' and not self.market_data.polygon_api_key:
            errors.append("ERROR: Polygon API key required when using Polygon as provider")
        
        if self.market_data.primary_provider == 'alphavantage' and not self.market_data.alphavantage_api_key:
            errors.append("ERROR: Alpha Vantage API key required when using Alpha Vantage as provider")
        
        # validate trading config
        if self.trading.max_position_size <= 0:
            errors.append("ERROR: max_position_size must be positive")
        
        if self.trading.max_positions <= 0:
            errors.append("ERROR: max_positions must be positive")
        
        if errors:
            for error in errors:
                print(f"Configuration Error(s): {error}")
            return False
        
        return True
    
    def print_summary(self):
        """Print config summary"""
        print("\n" + "="*60)
        print("IBKR TWS Trading Bot - Configuration Summary (!!!)")
        print("="*60)
        print(f"\n[IBKR Connection]")
        print(f"  Host: {self.ibkr.host}:{self.ibkr.port}")
        print(f"  Client ID: {self.ibkr.client_id}")
        print(f"  Mode: {'PAPER TRADING' if self.trading.paper_trading else 'LIVE TRADING'}")
        print(f"  Delayed Data: {self.ibkr.use_delayed_data}")
        
        print(f"\n[Market Data]")
        print(f"  Primary Provider: {self.market_data.primary_provider}")
        print(f"  Fallback Providers: {', '.join(self.market_data.fallback_providers)}")
        
        print(f"\n[Trading Parameters]")
        print(f"  Trading Enabled: {self.trading.enable_trading}")
        print(f"  Max Position Size: ${self.trading.max_position_size:,.2f}")
        print(f"  Max Positions: {self.trading.max_positions}")
        print(f"  Max Daily Loss: ${self.trading.max_daily_loss:,.2f}")
        
        print(f"\n[Logging]")
        print(f"  Level: {self.logging.log_level}")
        print(f"  Directory: {self.logging.log_dir}")
        print("="*60 + "\n")

# global config instance
config = Config()
