"""
Main Trading Bot Orchestrator

Coordinates all components:
- IBKR connection
- Market data providers
- Trading strategies
- Risk management
- Order execution

@author: Pedro Gronda Garrigues
"""

import time
import signal
import sys
from typing import List, Optional
from datetime import datetime
from threading import Event

from ibapi.contract import Contract
from ibapi.order import Order

from config import config
from src.connection.ibkr_client import IBKRClient
from src.market_data.market_data_manager import MarketDataManager
from src.market_data.yahoo_provider import YahooFinanceProvider
from src.market_data.ibkr_provider import IBKRMarketDataProvider
from src.market_data.base_provider import Quote
from src.strategies.base_strategy import BaseStrategy, TradingSignal, SignalType
from src.risk.risk_manager import RiskManager, RiskLimits
from src.utils.logger import get_logger


class TradingBot:
    """
    Main trading bot that orchestrates all components
    
    Features:
    - Multi-provider market data with failover
    - Risk management and validation
    - Strategy execution
    - Position tracking
    - Graceful shutdown
    """
    
    def __init__(self, strategies: List[BaseStrategy]):
        """
        Init trading bot
        
        Args:
            strategies: List of trading strategies to run
        """

        self.logger = get_logger("TradingBot")
        self.strategies = strategies
        
        # validate config
        if not config.validate():
            raise ValueError("Invalid configuration")
        
        config.print_summary()
        
        # init components
        self.ibkr_client: Optional[IBKRClient] = None
        self.market_data_manager: Optional[MarketDataManager] = None
        self.risk_manager: Optional[RiskManager] = None
        
        # state management
        self.is_running = False
        self.shutdown_event = Event()
        
        # setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.logger.info(f"Trading bot initialized with {len(strategies)} strategies")
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
       
        self.logger.info(f"Received signal {signum}, initiating shutdown...")
        self.shutdown()
    
    def initialize(self) -> bool:
        """
        Init all bot components
        
        Returns:
            True if initialization successful
        """
        
        try:
            # 1. Connect to IBKR
            self.logger.info("Connecting to IBKR...")
            self.ibkr_client = IBKRClient(
                host=config.ibkr.host,
                port=config.ibkr.port,
                client_id=config.ibkr.client_id,
                use_delayed_data=config.ibkr.use_delayed_data
            ) # primary client
            
            if not self.ibkr_client.connect_and_run():
                self.logger.error("Failed to connect to IBKR")
                return False
            
            # 2. Init market data providers
            self.logger.info("Initializing market data providers...")
            
            # create providers based on config (in env)
            primary_provider = None
            fallback_providers = []
            
            if config.market_data.primary_provider == 'ibkr':
                primary_provider = IBKRMarketDataProvider(self.ibkr_client)
            elif config.market_data.primary_provider == 'yahoo':
                primary_provider = YahooFinanceProvider()
            
            # add fallback providers
            for provider_name in config.market_data.fallback_providers:
                if provider_name == 'yahoo' and config.market_data.primary_provider != 'yahoo':
                    fallback_providers.append(YahooFinanceProvider())
                elif provider_name == 'ibkr' and config.market_data.primary_provider != 'ibkr':
                    fallback_providers.append(IBKRMarketDataProvider(self.ibkr_client))
            
            if not primary_provider:
                self.logger.error("No valid market data provider configured")
                return False
            
            self.market_data_manager = MarketDataManager(primary_provider, fallback_providers)
            
            if not self.market_data_manager.connect():
                self.logger.error("Failed to connect to market data providers")
                return False
            
            # 3. Init basic risk manager
            self.logger.info("Initializing risk manager...")
            risk_limits = RiskLimits(
                max_position_size=config.trading.max_position_size,
                max_positions=config.trading.max_positions,
                max_daily_loss=config.trading.max_daily_loss,
                max_order_value=config.trading.max_order_value
            )
            self.risk_manager = RiskManager(risk_limits)
            
            # 4. Request init positions
            self.logger.info("Requesting current positions...")
            self.ibkr_client.request_positions()
            time.sleep(1)  # wait for position updates
            
            # update risk manager with current positions
            for symbol, pos_data in self.ibkr_client.get_all_positions().items():
                self.risk_manager.update_position(
                    symbol=symbol,
                    quantity=int(pos_data['position']),
                    avg_price=pos_data['avg_cost'],
                    current_price=pos_data['avg_cost']  # will be updated by market data
                )
            
            # 5. Start strategies
            for strategy in self.strategies:
                strategy.start()
            
            self.logger.info("Bot initialization complete!")
            return True
            
        except Exception as e:
            self.logger.error(f"Initialization failed: {e}", exc_info=True)
            return False
    
    def _create_contract(self, symbol: str) -> Contract:
        """Create stock contract for a symbol"""
        
        contract = Contract()
        contract.symbol = symbol
        contract.secType = "STK"
        contract.exchange = "SMART"  # default exchange (adapts to order)
        contract.currency = "USD"
        return contract
    
    def _create_order(self, signal: TradingSignal) -> Order:
        """
        Create order from trading signal
        
        Args:
            signal: Trading signal
        
        Returns:
            Order object
        """

        order = Order()
        
        # determine action
        if signal.signal_type == SignalType.BUY:
            order.action = "BUY"
        elif signal.signal_type in [SignalType.SELL, SignalType.CLOSE_LONG]:
            order.action = "SELL"
        elif signal.signal_type == SignalType.CLOSE_SHORT:
            order.action = "BUY"
        else:
            raise ValueError(f"Invalid signal type: {signal.signal_type}")
        
        # set quantity
        if signal.quantity > 0:
            order.totalQuantity = signal.quantity
        else:
            # use "risk manager" to calculate position size
            order.totalQuantity = self.risk_manager.calculate_position_size(
                signal.symbol, signal.price
            )
        
        # set order type
        order.orderType = config.trading.default_order_type
        
        if order.orderType == "LMT":
            order.lmtPrice = signal.price
        
        # set to day order
        order.tif = "DAY"
        
        return order
    
    def execute_signal(self, signal: TradingSignal):
        """
        Execute a trading signal with risk validation
        
        Args:
            signal: Trading signal to execute
        """

        if not config.trading.enable_trading:
            self.logger.warning(f"Trading disabled - signal ignored: {signal}")
            return
        
        # validate signal with risk manager
        is_valid, reason = self.risk_manager.validate_signal(signal, signal.price)
        
        if not is_valid:
            self.logger.warning(f"Signal rejected by risk manager: {reason}")
            return
        
        # create order
        try:
            contract = self._create_contract(signal.symbol)
            order = self._create_order(signal)
            
            # place order
            order_id = self.ibkr_client.place_order(contract, order)
            
            self.logger.info(f"Order placed: {order_id} - {signal}")
            
        except Exception as e:
            self.logger.error(f"Failed to execute signal: {e}", exc_info=True)
    
    def process_quote(self, quote: Quote):
        """
        Process quote through all strategies
        
        Args:
            quote: Market quote
        """

        # update risk manager with current price
        self.risk_manager.update_prices({quote.symbol: quote.last or quote.mid_price})
        
        # process through each strategy
        for strategy in self.strategies:
            if not strategy.is_active:
                continue
            
            try:
                signal = strategy.on_quote(quote)
                
                if signal:
                    self.execute_signal(signal)
                    
            except Exception as e:
                self.logger.error(f"Error in strategy {strategy.name}: {e}", exc_info=True)
    
    def run(self, update_interval: float = 5.0):
        """
        Main bot loop
        
        Args:
            update_interval: Seconds between market data updates
        """

        if not config.trading.enable_trading:
            self.logger.warning("!!! TRADING IS DISABLED - Bot running in monitor mode only")
        
        self.is_running = True
        self.logger.info(f"Bot started! Update interval: {update_interval}s")
        
        # collect all symbols from strategies
        all_symbols = set()
        for strategy in self.strategies:
            all_symbols.update(strategy.symbols)
        
        all_symbols = list(all_symbols)
        self.logger.info(f"Monitoring {len(all_symbols)} symbols: {all_symbols}")
        
        try:
            while self.is_running and not self.shutdown_event.is_set():
                loop_start = time.time()
                
                # check emergency stop conditions
                if self.risk_manager.check_emergency_stop():
                    self.logger.critical("Emergency stop triggered - shutting down")
                    break
                
                # get quotes for all symbols
                quotes = self.market_data_manager.get_quotes(all_symbols, use_cache=False)
                
                # process each quote
                for symbol, quote in quotes.items():
                    self.process_quote(quote)
                
                # log status periodically
                if int(time.time()) % 60 == 0:  # every min
                    self._log_status()
                
                # sleep for remaining time in interval
                elapsed = time.time() - loop_start
                sleep_time = max(0, update_interval - elapsed)
                
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
        except KeyboardInterrupt:
            self.logger.info("Keyboard interrupt received")
        except Exception as e:
            self.logger.error(f"Error in main loop: {e}", exc_info=True)
        finally:
            self.shutdown()
    
    def _log_status(self):
        """Log current bot status"""
        
        portfolio = self.risk_manager.get_portfolio_summary()
        
        self.logger.info("=" * 60)
        self.logger.info(f"Status Update - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"Positions: {portfolio['total_positions']}/{self.risk_manager.limits.max_positions}")
        self.logger.info(f"Total Exposure: ${portfolio['total_exposure']:,.2f}")
        self.logger.info(f"Unrealized P&L: ${portfolio['unrealized_pnl']:,.2f}")
        self.logger.info(f"Daily P&L: ${portfolio['daily_pnl']:,.2f}")
        self.logger.info(f"Daily Trades: {portfolio['daily_trades']}")
        
        # strategy performance
        for strategy in self.strategies:
            perf = strategy.get_performance_summary()
            self.logger.info(f"{strategy.name}: Trades={perf['total_trades']}, "
                           f"Win Rate={perf['win_rate']:.1f}%, "
                           f"P&L=${perf['total_pnl']:.2f}")
        
        self.logger.info("=" * 60)
    
    def shutdown(self):
        """Gracefully shutdown bot"""
        
        if not self.is_running:
            return
        
        self.logger.info("STATUS: Shutting down bot...")
        self.is_running = False
        self.shutdown_event.set()
        
        # stop strategies
        for strategy in self.strategies:
            strategy.stop()
        
        # print final status
        self._log_status()
        
        # disconnect from market data
        if self.market_data_manager:
            self.market_data_manager.disconnect()
        
        # disconnect from IBKR
        if self.ibkr_client:
            self.ibkr_client.disconnect_gracefully()
        
        self.logger.info("BOT EXIT: Bot shutdown complete")

