"""
IBKR TWS Client - Production-ready connection manager

Features:
- Automatic reconnection
- Error handling and recovery
- Thread-safe operations
- Event-driven architecture
- Market data management
- Order management

@author: Pedro Gronda Garrigues
"""

import threading
import time
from typing import Dict, Callable, Optional, List
from datetime import datetime
from collections import defaultdict

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order
from ibapi.common import TickerId, OrderId

from src.utils.logger import get_logger


class IBKRClient(EWrapper, EClient):
    """
    Enhanced IBKR client (to original docs entry point)
    
    This class combines EWrapper (callbacks) and EClient (requests)
    to provide an interface to IBKR TWS/Gateway.

    Comments: 
     - I initially vibecoded this (not a good idea), and I miraculously made it work
     - However, I apologize for how ridiculously overkill it is 
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, 
                 client_id: int = 1, use_delayed_data: bool = True):
        EClient.__init__(self, self)
        
        self.host = host
        self.port = port
        self.client_id = client_id
        self.use_delayed_data = use_delayed_data
        
        # logger (refer to utils/logger.py)
        self.logger = get_logger("IBKRClient")
        
        # connection state
        self.connected_event = threading.Event()
        self.is_connected = False
        self.next_valid_order_id = None
        
        # data storage
        self.positions: Dict = {}
        self.orders: Dict[OrderId, Dict] = {}
        self.account_summary: Dict = {}
        self.market_data: Dict[TickerId, Dict] = defaultdict(dict)
        
        # request tracking
        self._next_req_id = 1
        self._req_id_lock = threading.Lock()
        
        # calbbacks for custom handling
        self.price_callbacks: Dict[TickerId, Callable] = {}
        self.order_callbacks: Dict[OrderId, Callable] = {}
        
        # thread for message processing
        self.msg_thread = None
    
    # ========================================================================
    # Connection Management
    # ========================================================================
    
    def connect_and_run(self) -> bool:
        """
        Connect to IBKR TWS/Gateway and start message processing thread
        
        Returns:
            bool: True if connection successful
        """
        try:
            self.logger.info(f"CONNECTION STATUS: Connecting to IBKR at {self.host}:{self.port}")
            self.connect(self.host, self.port, self.client_id)
            
            # start message processing thread
            self.msg_thread = threading.Thread(target=self.run, daemon=True)
            self.msg_thread.start()
            
            # wait for connection confirmation
            if self.connected_event.wait(timeout=10):
                self.logger.info("CONNECTION STATUS: Successfully connected to IBKR")
                
                # request delayed market data (if specified)
                if self.use_delayed_data:
                    self.reqMarketDataType(3)  # 3 = delayed data (free)
                    self.logger.info(" - NOTE: Using delayed market data (FREE)")
                else:
                    self.reqMarketDataType(1)  # 1 = real-time data (paid)
                    self.logger.info(" - NOTE: Using real-time market data (PAID)")
                
                return True
            else:
                self.logger.error("CONNECTION STATUS: Connection timeout")
                return False
                
        except Exception as e:
            self.logger.error(f"ERROR: Connection failed: {e}")
            return False
    
    def disconnect_gracefully(self):
        """Disconnect from IBKR with cleanup"""
        
        self.logger.info("CONNECTION STATUS: Disconnecting from IBKR")
        self.is_connected = False
        self.disconnect()
    
    # ========================================================================
    # EWrapper Callback Implementations - Connection Events
    # ========================================================================
    
    def connectAck(self):
        """Called when connection is acknowledged"""
        
        self.logger.debug("CONNECTION STATUS: Connection acknowledged")
    
    def nextValidId(self, orderId: OrderId):
        """
        Called when connection is established
        
        Provides the next valid order ID
        """
        
        super().nextValidId(orderId)
        self.next_valid_order_id = orderId
        self.is_connected = True
        self.connected_event.set()
        self.logger.info(f"STATUS: Connected. Next valid order ID: {orderId}")
    
    def connectionClosed(self):
        """Called when connection is closed"""
        
        self.logger.warning("CONNECTION STATUS: Connection closed")
        self.is_connected = False
        self.connected_event.clear()
    
    def error(self, reqId: TickerId, errorCode: int, errorString: str, 
              advancedOrderRejectJson: str = ""):
        """
        Error handler for categorizing errors and logs appropriately
        
        IBKR Error Codes:
        - 502, 503, 504      -> connection issues
        - 1100, 1101, 1102   -> connection status messages
        - 2104, 2106, 2158   -> market data farm connection
        - 2119               -> market data subscription error
        """

        # info messages (not actual errors; careful!)
        info_codes = {2104, 2106, 2158, 2119}
        # warning codes
        warning_codes = {1100, 1101, 1102, 2103, 2105}
        # connection error codes
        connection_codes = {502, 503, 504, 1100}
        
        if errorCode in info_codes:
            self.logger.info(f"STATUS: Info {errorCode}: {errorString}")
        elif errorCode in warning_codes:
            self.logger.warning(f"WARNING: Warning {errorCode}: {errorString}")
        elif errorCode in connection_codes:
            self.logger.error(f"CONNECTION ERROR: Connection error {errorCode}: {errorString}")
            self.is_connected = False
        else: # logger general fallback
            self.logger.error(f"ERROR: Error {errorCode} (ReqID: {reqId}): {errorString}")
    
    # ========================================================================
    # Market Data Callbacks
    # ========================================================================
    
    def tickPrice(self, reqId: TickerId, tickType: int, price: float,
                  attrib):
        """
        Price tick callback
        
        Tick Types:
        - 1: Bid
        - 2: Ask
        - 4: Last
        - 6: High
        - 7: Low
        - 9: Close
        """
        super().tickPrice(reqId, tickType, price, attrib)
        
        tick_names = {
            1: "bid", 2: "ask", 4: "last",
            6: "high", 7: "low", 9: "close"
        }
        
        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = price
            self.market_data[reqId]['timestamp'] = datetime.now()
            
            # trigger callback if registered
            if reqId in self.price_callbacks:
                self.price_callbacks[reqId](reqId, tick_names[tickType], price)
    
    def tickSize(self, reqId: TickerId, tickType: int, size: int):
        """
        Size tick callback
        
        Tick Types:
        - 0: Bid size
        - 3: Ask size
        - 5: Last size
        - 8: Volume
        """
        super().tickSize(reqId, tickType, size)
        
        tick_names = {0: "bid_size", 3: "ask_size", 5: "last_size", 8: "volume"}
        
        if tickType in tick_names:
            self.market_data[reqId][tick_names[tickType]] = size
    
    def tickString(self, reqId: TickerId, tickType: int, value: str):
        """String tick callback"""
        
        super().tickString(reqId, tickType, value)
        
        if tickType == 45:  # last timestamp
            self.market_data[reqId]['last_timestamp'] = value
    
    # ========================================================================
    # Position & Account Callbacks
    # ========================================================================
    
    def position(self, account: str, contract: Contract, position: float,
                 avgCost: float):
        """Position update callback"""
        
        super().position(account, contract, position, avgCost)
        
        symbol = contract.symbol
        self.positions[symbol] = {
            'account': account,
            'contract': contract,
            'position': position,
            'avg_cost': avgCost,
            'timestamp': datetime.now()
        }
        
        self.logger.debug(f"Position update: {symbol} - {position} @ {avgCost}")
    
    def positionEnd(self):
        """Called when all positions have been received"""
        
        super().positionEnd()
        self.logger.debug("Position updates complete")
    
    def accountSummary(self, reqId: int, account: str, tag: str, 
                       value: str, currency: str):
        """Account summary callback"""
        
        super().accountSummary(reqId, account, tag, value, currency)
        self.account_summary[tag] = {
            'value': value,
            'currency': currency,
            'timestamp': datetime.now()
        }
    
    def accountSummaryEnd(self, reqId: int):
        """Called when account summary is complete"""
        
        super().accountSummaryEnd(reqId)
        self.logger.debug("Account summary complete")
    
    # ========================================================================
    # Order Callbacks
    # ========================================================================
    
    def orderStatus(self, orderId: OrderId, status: str, filled: float,
                    remaining: float, avgFillPrice: float, permId: int,
                    parentId: int, lastFillPrice: float, clientId: int,
                    whyHeld: str, mktCapPrice: float):
        """Order status update callback"""
        
        super().orderStatus(orderId, status, filled, remaining, avgFillPrice,
                           permId, parentId, lastFillPrice, clientId,
                           whyHeld, mktCapPrice)
        
        if orderId not in self.orders:
            self.orders[orderId] = {}
        
        self.orders[orderId].update({
            'status': status,
            'filled': filled,
            'remaining': remaining,
            'avg_fill_price': avgFillPrice,
            'last_fill_price': lastFillPrice,
            'timestamp': datetime.now()
        })
        
        self.logger.info(f"Order {orderId} status: {status}, "
                        f"Filled: {filled}, Remaining: {remaining}")
        
        # trigger callback (if registered)
        if orderId in self.order_callbacks:
            self.order_callbacks[orderId](orderId, status, filled, avgFillPrice)
    
    def openOrder(self, orderId: OrderId, contract: Contract, order: Order,
                  orderState):
        """Open order callback"""
        
        super().openOrder(orderId, contract, order, orderState)
        
        if orderId not in self.orders:
            self.orders[orderId] = {}
        
        self.orders[orderId].update({
            'contract': contract,
            'order': order,
            'state': orderState
        })
    
    def execDetails(self, reqId: int, contract: Contract, execution):
        """Execution details callback"""
        
        super().execDetails(reqId, contract, execution)
        
        self.logger.trade(
            f"Execution: {execution.side} {execution.shares} {contract.symbol} "
            f"@ ${execution.price} (Order {execution.orderId})"
        )
    
    # ========================================================================
    # Helper Methods for Requests
    # ========================================================================
    
    def get_next_req_id(self) -> int:
        """Thread-safe request ID generation"""
        
        with self._req_id_lock:
            req_id = self._next_req_id
            self._next_req_id += 1
            return req_id
    
    def get_next_order_id(self) -> OrderId:
        """Get next valid order ID"""
        
        if self.next_valid_order_id is None:
            raise RuntimeError("RUNTIME ERROR: Not connected - no valid order ID available")
        
        order_id = self.next_valid_order_id
        self.next_valid_order_id += 1
        return order_id
    
    def request_market_data(self, contract: Contract, 
                           callback: Optional[Callable] = None) -> TickerId:
        """
        Request market data for a contract
        
        Args:
            contract: Contract to get data for
            callback: Optional callback function for price updates
        
        Returns:
            Request ID for tracking
        """
        req_id = self.get_next_req_id()
        
        if callback:
            self.price_callbacks[req_id] = callback
        
        self.reqMktData(req_id, contract, "", False, False, [])
        self.logger.debug(f"Requested market data for {contract.symbol} (ReqID: {req_id})")
        
        return req_id
    
    def cancel_market_data(self, req_id: TickerId):
        """Cancel market data subscription"""
        
        self.cancelMktData(req_id)
        
        if req_id in self.price_callbacks:
            del self.price_callbacks[req_id]
        
        self.logger.debug(f"Cancelled market data (ReqID: {req_id})")
    
    def request_positions(self):
        """Request all current positions"""
        
        self.reqPositions()
        self.logger.debug("Requested positions")
    
    def request_account_summary(self):
        """Request account summary"""
        
        req_id = self.get_next_req_id()
        tags = "NetLiquidation,TotalCashValue,BuyingPower,GrossPositionValue"
        self.reqAccountSummary(req_id, "All", tags)
        self.logger.debug("Requested account summary")
        return req_id
    
    def place_order(self, contract: Contract, order: Order,
                   callback: Optional[Callable] = None) -> OrderId:
        """
        Place an order
        
        Args:
            contract: Contract to trade
            order: Order details
            callback: Optional callback for order status updates
        
        Returns:
            Order ID
        """
        
        order_id = self.get_next_order_id()
        
        if callback:
            self.order_callbacks[order_id] = callback
        
        self.placeOrder(order_id, contract, order)
        
        self.logger.order(
            order_id, order.action, contract.symbol, 
            order.totalQuantity, order.lmtPrice if order.orderType == "LMT" else None
        )
        
        return order_id
    
    def cancel_order(self, order_id: OrderId):
        """Cancel an order"""
        
        self.cancelOrder(order_id)
        self.logger.info(f"Cancelled order {order_id}")
    
    def get_market_data(self, req_id: TickerId) -> Dict:
        """Get cached market data for a request ID"""
        
        return self.market_data.get(req_id, {})
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get position information for a symbol"""
        
        return self.positions.get(symbol)
    
    def get_all_positions(self) -> Dict:
        """Get all positions"""
        
        return self.positions.copy()
    
    def get_account_value(self, tag: str) -> Optional[str]:
        """Get account summary value by tag"""
        
        return self.account_summary.get(tag, {}).get('value')

