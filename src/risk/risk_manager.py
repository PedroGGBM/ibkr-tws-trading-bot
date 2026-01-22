"""
Risk Management System

Implements comprehensive risk controls:
- Position sizing
- Maximum position limits
- Daily loss limits
- Order validation
- Portfolio exposure tracking

@author: Pedro Gronda Garrigues
"""

from typing import Dict, Optional, List
from datetime import datetime, date
from dataclasses import dataclass

from src.utils.logger import get_logger
from src.strategies.base_strategy import TradingSignal, SignalType


@dataclass
class RiskLimits:
    """Risk limit configuration"""
    max_position_size: float = 10000.0  # USD
    max_positions: int = 5
    max_daily_loss: float = 500.0  # USD
    max_order_value: float = 5000.0  # USD
    max_portfolio_exposure: float = 50000.0  # USD
    max_symbol_concentration: float = 0.30  # 30% max per symbol
    
    def __repr__(self):
        return (f"RiskLimits(max_pos=${self.max_position_size:,.0f}, "
                f"max_positions={self.max_positions}, "
                f"max_daily_loss=${self.max_daily_loss:,.0f})")


@dataclass
class Position:
    """Position tracking"""
    symbol: str
    quantity: int
    avg_price: float
    current_price: float
    timestamp: datetime
    
    @property
    def market_value(self) -> float:
        """Current market value"""
        return abs(self.quantity * self.current_price)
    
    @property
    def unrealized_pnl(self) -> float:
        """Unrealized profit/loss"""
        return self.quantity * (self.current_price - self.avg_price)
    
    @property
    def is_long(self) -> bool:
        """Is this a long position"""
        return self.quantity > 0
    
    @property
    def is_short(self) -> bool:
        """Is this a short position"""
        return self.quantity < 0
    
    def __repr__(self):
        direction = "LONG" if self.is_long else "SHORT"
        return (f"Position({direction} {abs(self.quantity)} {self.symbol} "
                f"@ ${self.avg_price:.2f}, MV=${self.market_value:.2f}, "
                f"PnL=${self.unrealized_pnl:.2f})")


class RiskManager:
    """
    Comprehensive risk management system
    
    Validates all trading decisions against risk parameters before execution.
    """
    
    def __init__(self, limits: RiskLimits):
        """
        Initialize risk manager
        
        Args:
            limits: Risk limits configuration
        """
        self.limits = limits
        self.logger = get_logger("RiskManager")
        
        # position tracking
        self.positions: Dict[str, Position] = {}
        
        # daily tracking
        self.daily_pnl: Dict[date, float] = {}
        self.daily_trades: Dict[date, int] = {}
        self.current_date = date.today()
        
        # order tracking
        self.pending_orders: Dict[int, TradingSignal] = {}
        
        self.logger.info(f"Risk manager initialized with {limits}")
    
    def _reset_daily_tracking_if_needed(self):
        """Reset daily counters on new day"""
        today = date.today()
        if today != self.current_date:
            self.current_date = today
            self.logger.info(f"New trading day: {today}")
    
    def update_position(self, symbol: str, quantity: int, avg_price: float,
                       current_price: float):
        """
        Update position information
        
        Args:
            symbol: Symbol
            quantity: Current quantity
            avg_price: Average entry price
            current_price: Current market price
        """
        if quantity == 0:
            # position closed
            if symbol in self.positions:
                old_pos = self.positions[symbol]
                self.logger.info(f"Position closed: {old_pos}")
                del self.positions[symbol]
        else:
            # position opened or updated
            position = Position(
                symbol=symbol,
                quantity=quantity,
                avg_price=avg_price,
                current_price=current_price,
                timestamp=datetime.now()
            )
            
            self.positions[symbol] = position
            self.logger.debug(f"Position updated: {position}")
    
    def update_prices(self, symbol_prices: Dict[str, float]):
        """
        Update current prices for all positions
        
        Args:
            symbol_prices: Dict mapping symbols to current prices
        """
        for symbol, price in symbol_prices.items():
            if symbol in self.positions:
                self.positions[symbol].current_price = price
    
    def get_total_exposure(self) -> float:
        """Get total portfolio exposure (sum of absolute position values)"""
        return sum(pos.market_value for pos in self.positions.values())
    
    def get_total_unrealized_pnl(self) -> float:
        """Get total unrealized P&L"""
        return sum(pos.unrealized_pnl for pos in self.positions.values())
    
    def get_daily_pnl(self) -> float:
        """Get today's P&L"""
        self._reset_daily_tracking_if_needed()
        return self.daily_pnl.get(self.current_date, 0.0)
    
    def record_realized_pnl(self, pnl: float):
        """
        Record realized P&L from a trade
        
        Args:
            pnl: Realized profit/loss
        """
        self._reset_daily_tracking_if_needed()
        
        current = self.daily_pnl.get(self.current_date, 0.0)
        self.daily_pnl[self.current_date] = current + pnl
        
        self.logger.info(f"Realized P&L: ${pnl:.2f}, Daily total: ${self.get_daily_pnl():.2f}")
    
    def validate_signal(self, signal: TradingSignal, current_price: float) -> tuple[bool, str]:
        """
        Validate a trading signal against risk limits
        
        Args:
            signal: Trading signal to validate
            current_price: Current market price
        
        Returns:
            (is_valid, reason)
        """
        self._reset_daily_tracking_if_needed()
        
        symbol = signal.symbol
        
        # check if trading is a BUY or SELL action
        if signal.signal_type not in [SignalType.BUY, SignalType.SELL]:
            # HOLD, CLOSE_LONG, CLOSE_SHORT don't need position checks
            if signal.signal_type in [SignalType.CLOSE_LONG, SignalType.CLOSE_SHORT]:
                # just verifye have the position to close
                if symbol not in self.positions:
                    return False, f"No position to close for {symbol}"
                
                position = self.positions[symbol]
                if signal.signal_type == SignalType.CLOSE_LONG and not position.is_long:
                    return False, f"Cannot close long position - currently short {symbol}"
                if signal.signal_type == SignalType.CLOSE_SHORT and not position.is_short:
                    return False, f"Cannot close short position - currently long {symbol}"
            
            return True, "OK"
        
        # calculate order value
        order_value = signal.quantity * current_price
        
        # check order value limit
        if order_value > self.limits.max_order_value:
            return False, (f"Order value ${order_value:.2f} exceeds limit "
                          f"${self.limits.max_order_value:.2f}")
        
        # check position limit (for new positions)
        is_new_position = symbol not in self.positions
        if is_new_position:
            if len(self.positions) >= self.limits.max_positions:
                return False, (f"Maximum positions ({self.limits.max_positions}) "
                              f"already open")
        
        # check position size limit
        if order_value > self.limits.max_position_size:
            return False, (f"Position size ${order_value:.2f} exceeds limit "
                          f"${self.limits.max_position_size:.2f}")
        
        # check portfolio exposure
        new_exposure = self.get_total_exposure() + order_value
        if new_exposure > self.limits.max_portfolio_exposure:
            return False, (f"Total exposure ${new_exposure:.2f} would exceed limit "
                          f"${self.limits.max_portfolio_exposure:.2f}")
        
        # check symbol concentration
        concentration = order_value / self.limits.max_portfolio_exposure
        if concentration > self.limits.max_symbol_concentration:
            return False, (f"Symbol concentration {concentration:.1%} exceeds limit "
                          f"{self.limits.max_symbol_concentration:.1%}")
        
        # check daily loss limit
        total_pnl = self.get_daily_pnl() + self.get_total_unrealized_pnl()
        if total_pnl < -self.limits.max_daily_loss:
            return False, (f"Daily loss limit reached: ${total_pnl:.2f} < "
                          f"-${self.limits.max_daily_loss:.2f}")
        
        return True, "OK"
    
    def calculate_position_size(self, symbol: str, price: float, 
                               risk_per_trade: float = 0.02) -> int:
        """
        Calculate appropriate position size based on risk parameters
        
        Args:
            symbol: Symbol to trade
            price: Current price
            risk_per_trade: Risk as fraction of max position size (default 2%)
        
        Returns:
            Recommended quantity
        """
        # calculate based on position size limit
        max_value = min(self.limits.max_position_size, self.limits.max_order_value)
        risk_adjusted_value = max_value * risk_per_trade
        
        quantity = int(risk_adjusted_value / price)
        
        # Ensure at least 1 share if price allows
        if quantity == 0 and price < max_value:
            quantity = 1
        
        self.logger.debug(f"Position sizing for {symbol}: {quantity} shares @ ${price:.2f} "
                         f"= ${quantity * price:.2f}")
        
        return quantity
    
    def get_portfolio_summary(self) -> Dict:
        """Get comprehensive portfolio summary"""
        self._reset_daily_tracking_if_needed()
        
        return {
            'total_positions': len(self.positions),
            'total_exposure': self.get_total_exposure(),
            'unrealized_pnl': self.get_total_unrealized_pnl(),
            'daily_pnl': self.get_daily_pnl(),
            'daily_trades': self.daily_trades.get(self.current_date, 0),
            'positions': {
                symbol: {
                    'quantity': pos.quantity,
                    'avg_price': pos.avg_price,
                    'current_price': pos.current_price,
                    'market_value': pos.market_value,
                    'unrealized_pnl': pos.unrealized_pnl
                }
                for symbol, pos in self.positions.items()
            },
            'risk_limits': {
                'max_position_size': self.limits.max_position_size,
                'max_positions': self.limits.max_positions,
                'max_daily_loss': self.limits.max_daily_loss,
                'positions_used': len(self.positions),
                'exposure_used': self.get_total_exposure(),
                'daily_loss_used': abs(min(0, self.get_daily_pnl()))
            }
        }
    
    def check_emergency_stop(self) -> bool:
        """
        Check if emergency stop conditions are met
        
        Returns:
            True if trading should be halted
        """
        # check daily loss limit
        if self.get_daily_pnl() < -self.limits.max_daily_loss:
            self.logger.critical("EMERGENCY STOP: Daily loss limit exceeded!")
            return True
        
        # check total exposure
        if self.get_total_exposure() > self.limits.max_portfolio_exposure:
            self.logger.critical("EMERGENCY STOP: Portfolio exposure limit exceeded!")
            return True
        
        return False

