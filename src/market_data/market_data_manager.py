"""
Market Data Manager

Manages multiple market data providers with automatic failover.
This allows seamless switching between IBKR, Yahoo Finance, Polygon, etc.

@author: Pedro Gronda Garrigues
"""

from typing import Dict, List, Optional, Type
from datetime import datetime

from src.market_data.base_provider import MarketDataProvider, Quote, Bar
from src.market_data.yahoo_provider import YahooFinanceProvider
from src.market_data.ibkr_provider import IBKRMarketDataProvider
from src.utils.logger import get_logger


class MarketDataManager:
    """
    Market data manager with multi-provider support and automatic failover
    
    Features:
    - Primary provider with automatic fallback
    - Provider health monitoring
    - Unified interface across all providers
    - Caching to reduce API calls
    """
    
    def __init__(self, primary_provider: MarketDataProvider,
                 fallback_providers: Optional[List[MarketDataProvider]] = None):
        """
        Initialize market data manager
        
        Args:
            primary_provider: Primary data provider
            fallback_providers: List of fallback providers (in order of preference)
        """
        self.primary_provider = primary_provider
        self.fallback_providers = fallback_providers or []
        self.all_providers = [primary_provider] + self.fallback_providers
        
        self.logger = get_logger("MarketDataManager")
        
        # quote cache
        self._quote_cache: Dict[str, Quote] = {}
        self._cache_timeout = 5  # seconds
        
        # provider health tracking
        self._provider_failures: Dict[str, int] = {}
        self._max_failures = 3
        
        # current active provider
        self.active_provider = primary_provider
        
        self.logger.info(f"Initialized with primary: {primary_provider.name}, "
                        f"fallbacks: {[p.name for p in fallback_providers]}")
    
    def connect(self) -> bool:
        """Connect to all providers"""
        success = False
        
        for provider in self.all_providers:
            try:
                if provider.connect():
                    self.logger.info(f"Connected to {provider.name}")
                    success = True
                else:
                    self.logger.warning(f"Failed to connect to {provider.name}")
            except Exception as e:
                self.logger.error(f"Error connecting to {provider.name}: {e}")
        
        return success
    
    def disconnect(self):
        """Disconnect from all providers"""
        for provider in self.all_providers:
            try:
                provider.disconnect()
            except Exception as e:
                self.logger.error(f"Error disconnecting from {provider.name}: {e}")
    
    def _get_cached_quote(self, symbol: str) -> Optional[Quote]:
        """Get quote from cache if still valid"""
        if symbol in self._quote_cache:
            quote = self._quote_cache[symbol]
            age = (datetime.now() - quote.timestamp).total_seconds()
            
            if age < self._cache_timeout:
                self.logger.debug(f"Using cached quote for {symbol} (age: {age:.1f}s)")
                return quote
        
        return None
    
    def _update_cache(self, symbol: str, quote: Quote):
        """Update quote cache"""
        self._quote_cache[symbol] = quote
    
    def _try_provider(self, provider: MarketDataProvider, 
                     operation: callable) -> Optional[any]:
        """
        Try an operation with a provider, track failures
        
        Args:
            provider: Provider to use
            operation: Function to execute
        
        Returns:
            Operation result or None on failure
        """
        try:
            result = operation(provider)
            
            # reset failure count on success
            if provider.name in self._provider_failures:
                self._provider_failures[provider.name] = 0
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error with {provider.name}: {e}")
            
            # track failure
            self._provider_failures[provider.name] = \
                self._provider_failures.get(provider.name, 0) + 1
            
            return None
    
    def _get_working_provider(self) -> Optional[MarketDataProvider]:
        """Get first working provider"""
        # try primary first
        if (self.primary_provider.is_connected and 
            self._provider_failures.get(self.primary_provider.name, 0) < self._max_failures):
            return self.primary_provider
        
        # try fallbacks
        for provider in self.fallback_providers:
            if (provider.is_connected and 
                self._provider_failures.get(provider.name, 0) < self._max_failures):
                
                if provider != self.active_provider:
                    self.logger.warning(f"Switching to fallback provider: {provider.name}")
                    self.active_provider = provider
                
                return provider
        
        self.logger.error("No working providers available")
        return None
    
    def get_quote(self, symbol: str, use_cache: bool = True) -> Optional[Quote]:
        """
        Get current quote for a symbol
        
        Args:
            symbol: Ticker symbol
            use_cache: Whether to use cached data
        
        Returns:
            Quote object or None
        """
        # check cache first
        if use_cache:
            cached = self._get_cached_quote(symbol)
            if cached:
                return cached
        
        # try primary provider
        provider = self._get_working_provider()
        if not provider:
            return None
        
        quote = self._try_provider(provider, lambda p: p.get_quote(symbol))
        
        # try fallbacks if primary failed
        if quote is None and provider == self.primary_provider:
            for fallback in self.fallback_providers:
                if not fallback.is_connected:
                    continue
                
                self.logger.info(f"Trying fallback provider: {fallback.name}")
                quote = self._try_provider(fallback, lambda p: p.get_quote(symbol))
                
                if quote:
                    self.active_provider = fallback
                    break
        
        # update cache
        if quote:
            self._update_cache(symbol, quote)
        
        return quote
    
    def get_quotes(self, symbols: List[str], use_cache: bool = True) -> Dict[str, Quote]:
        """Get quotes for multiple symbols"""
        quotes = {}
        
        # try to get from cache first
        uncached_symbols = []
        
        if use_cache:
            for symbol in symbols:
                cached = self._get_cached_quote(symbol)
                if cached:
                    quotes[symbol] = cached
                else:
                    uncached_symbols.append(symbol)
        else:
            uncached_symbols = symbols
        
        if not uncached_symbols:
            return quotes
        
        # get uncached quotes from provider
        provider = self._get_working_provider()
        if not provider:
            return quotes
        
        new_quotes = self._try_provider(
            provider, 
            lambda p: p.get_quotes(uncached_symbols)
        )
        
        # try fallbacks if needed
        if new_quotes is None and provider == self.primary_provider:
            for fallback in self.fallback_providers:
                if not fallback.is_connected:
                    continue
                
                self.logger.info(f"Trying fallback provider: {fallback.name}")
                new_quotes = self._try_provider(
                    fallback,
                    lambda p: p.get_quotes(uncached_symbols)
                )
                
                if new_quotes:
                    self.active_provider = fallback
                    break
        
        # update cache and results
        if new_quotes:
            for symbol, quote in new_quotes.items():
                self._update_cache(symbol, quote)
                quotes[symbol] = quote
        
        return quotes
    
    def get_historical_bars(self, symbol: str, period: str = "1d",
                           interval: str = "1m", limit: int = 100) -> List[Bar]:
        """Get historical OHLCV bars"""
        provider = self._get_working_provider()
        if not provider:
            return []
        
        bars = self._try_provider(
            provider,
            lambda p: p.get_historical_bars(symbol, period, interval, limit)
        )
        
        # try fallbacks
        if (bars is None or len(bars) == 0) and provider == self.primary_provider:
            for fallback in self.fallback_providers:
                if not fallback.is_connected:
                    continue
                
                self.logger.info(f"Trying fallback for historical data: {fallback.name}")
                bars = self._try_provider(
                    fallback,
                    lambda p: p.get_historical_bars(symbol, period, interval, limit)
                )
                
                if bars and len(bars) > 0:
                    break
        
        return bars or []
    
    def subscribe_quotes(self, symbols: List[str], callback):
        """Subscribe to real-time quote updates"""
        provider = self._get_working_provider()
        if provider:
            provider.subscribe_quotes(symbols, callback)
    
    def unsubscribe_quotes(self, symbols: List[str]):
        """Unsubscribe from quote updates"""
        provider = self._get_working_provider()
        if provider:
            provider.unsubscribe_quotes(symbols)
    
    def clear_cache(self):
        """Clear quote cache"""
        self._quote_cache.clear()
        self.logger.debug("Cleared quote cache")
    
    def get_provider_status(self) -> Dict:
        """Get status of all providers"""
        status = {
            'active_provider': self.active_provider.name if self.active_provider else None,
            'providers': {}
        }
        
        for provider in self.all_providers:
            status['providers'][provider.name] = {
                'connected': provider.is_connected,
                'failures': self._provider_failures.get(provider.name, 0)
            }
        
        return status

