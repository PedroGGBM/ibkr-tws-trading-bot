"""
Logging utilities for IBKR TWS Trading Bot

Provides structured logging with:
- File rotation
- Console output
- Different log levels for components
- Trade-specific logging

@author: Pedro Gronda Garrigues
"""

import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler
from typing import Optional
from datetime import datetime


class BotLogger:
    """Custom logger for trading bot w/ structured output"""
    
    _instances = {}
    
    def __new__(cls, name: str = "TradingBot"):
        """Singleton pattern to avoid duplicate loggers"""
        if name not in cls._instances:
            instance = super().__new__(cls)
            cls._instances[name] = instance
        return cls._instances[name]
    
    def __init__(self, name: str = "TradingBot"):
        if hasattr(self, '_initialized'):
            return
        
        self._initialized = True
        self.name = name
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers.clear()
        
        # create logs directory
        self.log_dir = Path("logs")
        self.log_dir.mkdir(exist_ok=True)
        
        # setup formatters
        self._setup_formatters()
        self._setup_handlers()
    
    def _setup_formatters(self):
        """Setup log formatters"""
        
        # format for files
        self.file_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # simpler format for console (cause ain't nobody got time to read above on terminal)
        self.console_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)-8s | %(message)s',
            datefmt='%H:%M:%S'
        )
    
    def _setup_handlers(self):
        """Setup log handlers"""
        
        # console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(self.console_formatter)
        self.logger.addHandler(console_handler)
        
        # general log file handler (rotating)
        general_log = self.log_dir / f"{self.name.lower()}.log"
        file_handler = RotatingFileHandler(
            general_log,
            maxBytes=10485760,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(self.file_formatter)
        self.logger.addHandler(file_handler)
        
        # trade-specific log file
        trade_log = self.log_dir / f"trades_{datetime.now().strftime('%Y%m%d')}.log"
        self.trade_handler = RotatingFileHandler(
            trade_log,
            maxBytes=10485760,
            backupCount=10
        )
        self.trade_handler.setLevel(logging.INFO)
        self.trade_handler.setFormatter(self.file_formatter)
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self.logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self.logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message"""
        self.logger.critical(message, **kwargs)
    
    def trade(self, message: str, **kwargs):
        """Log trade-specific message"""
        
        # add to both general log and trade log
        self.logger.info(f"[TRADE] {message}", **kwargs)
        trade_logger = logging.getLogger(f"{self.name}.trades")
        trade_logger.addHandler(self.trade_handler)
        trade_logger.info(message, **kwargs)
    
    def order(self, order_id: int, action: str, symbol: str, quantity: int, 
              price: Optional[float] = None, **kwargs):
        """Log order info"""
        
        price_str = f"@ ${price:.2f}" if price else "MKT"
        message = f"Order {order_id}: {action} {quantity} {symbol} {price_str}"
        self.trade(message, **kwargs)
    
    def position(self, symbol: str, position: int, avg_cost: float, 
                 current_price: float, pnl: float, **kwargs):
        """Log position information"""
        
        message = (f"Position {symbol}: {position} shares @ avg ${avg_cost:.2f}, "
                  f"current ${current_price:.2f}, P&L: ${pnl:.2f}")
        self.trade(message, **kwargs)
    
    def set_level(self, level: str):
        """Set logging level"""
        
        level_map = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        self.logger.setLevel(level_map.get(level.upper(), logging.INFO))


# global logger instance
logger = BotLogger("TradingBot")

def get_logger(name: str = "TradingBot") -> BotLogger:
    """Get or create a logger instance"""
    return BotLogger(name)
