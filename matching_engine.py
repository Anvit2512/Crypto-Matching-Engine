import uuid
import time
from collections import deque
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
import logging

# Set precision for Decimal calculations
getcontext().prec = 18

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Enums/Constants ---
class OrderSide:
    BUY = 'buy'
    SELL = 'sell'

class OrderType:
    MARKET = 'market'
    LIMIT = 'limit'
    IOC = 'ioc' # Immediate-Or-Cancel
    FOK = 'fok' # Fill-Or-Kill

# --- Data Classes ---

@dataclass
class Order:
    order_id: str
    symbol: str
    side: str
    order_type: str
    quantity: Decimal
    price: Decimal = Decimal('0.0')
    timestamp: float = field(default_factory=time.time)
    filled_quantity: Decimal = Decimal('0.0')
    is_live: bool = True

    @property
    def remaining_quantity(self) -> Decimal:
        return self.quantity - self.filled_quantity

    def __repr__(self):
        return (f"Order({self.order_id[:8]}.., {self.symbol}, {self.side}, "
                f"{self.order_type}, Qty={self.quantity}, Px={self.price}, "
                f"RemQty={self.remaining_quantity}, Live={self.is_live})")

@dataclass
class Trade:
    trade_id: str
    symbol: str
    price: Decimal
    quantity: Decimal
    aggressor_side: str
    maker_order_id: str
    taker_order_id: str
    timestamp: float = field(default_factory=time.time)

    def __repr__(self):
        return (f"Trade({self.trade_id}, {self.symbol}, Px={self.price}, "
                f"Qty={self.quantity}, Aggr={self.aggressor_side}, "
                f"Maker={self.maker_order_id[:8]}.., Taker={self.taker_order_id[:8]}..)")

# --- Matching Engine Core ---

class MatchingEngine:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids = {} # {price: {order_id: Order}}
        self.asks = {} # {price: {order_id: Order}}
        self.all_orders = {} # {order_id: Order} for audit
        self.last_trade_id = 0
        self.trades_history = deque()
        self.bbo = {'bid_price': Decimal('0.0'), 'bid_quantity': Decimal('0.0'),
                    'ask_price': Decimal('inf'), 'ask_quantity': Decimal('0.0')}
        logger.info(f"Matching Engine initialized for {self.symbol}")

    def _generate_trade_id(self):
        self.last_trade_id += 1
        return f"TRADE-{self.symbol}-{self.last_trade_id}"

    def _update_bbo(self):
        if self.bids:
            best_bid_price = max(self.bids.keys())
            best_bid_quantity = sum(o.remaining_quantity for o in self.bids[best_bid_price].values() if o.is_live)
            self.bbo['bid_price'] = best_bid_price
            self.bbo['bid_quantity'] = best_bid_quantity
        else:
            self.bbo['bid_price'] = Decimal('0.0')
            self.bbo['bid_quantity'] = Decimal('0.0')

        if self.asks:
            best_ask_price = min(self.asks.keys())
            best_ask_quantity = sum(o.remaining_quantity for o in self.asks[best_ask_price].values() if o.is_live)
            self.bbo['ask_price'] = best_ask_price
            self.bbo['ask_quantity'] = best_ask_quantity
        else:
            self.bbo['ask_price'] = Decimal('inf')
            self.bbo['ask_quantity'] = Decimal('0.0')
        logger.debug(f"BBO Updated: {self.bbo}")

    def get_bbo(self):
        self._update_bbo()
        return self.bbo

    def get_order_book_depth(self, levels: int = 10):
        bids_depth = []
        for price in sorted(self.bids.keys(), reverse=True)[:levels]:
            qty = sum(o.remaining_quantity for o in self.bids[price].values() if o.is_live)
            if qty > 0:
                bids_depth.append([price, qty])

        asks_depth = []
        for price in sorted(self.asks.keys())[:levels]:
            qty = sum(o.remaining_quantity for o in self.asks[price].values() if o.is_live)
            if qty > 0:
                asks_depth.append([price, qty])

        return {"timestamp": time.time(), "symbol": self.symbol, "bids": bids_depth, "asks": asks_depth}

    def add_order_to_book(self, order: Order):
        book = self.bids if order.side == OrderSide.BUY else self.asks
        if order.price not in book:
            book[order.price] = {}
        book[order.price][order.order_id] = order
        order.is_live = True
        logger.info(f"Order {order.order_id[:8]}.. added to book at price {order.price} with {order.remaining_quantity} qty remaining.")

    def remove_order_from_book(self, order: Order):
        book = self.bids if order.side == OrderSide.BUY else self.asks
        if order.price in book and order.order_id in book[order.price]:
            del book[order.price][order.order_id]
            if not book[order.price]:
                del book[order.price]
            order.is_live = False
            logger.info(f"Resting order {order.order_id[:8]}.. fully filled and removed.")

    def submit_order(self, symbol: str, order_type: str, side: str, quantity: str, price: str = '0.0') -> list[Trade]:
        if symbol != self.symbol:
            raise ValueError(f"Order symbol mismatch: Expected {self.symbol}, got {symbol}")

        dec_quantity = Decimal(quantity)
        dec_price = Decimal(price)

        if dec_quantity <= 0:
            raise ValueError(f"Invalid quantity {quantity}")

        new_order = Order(order_id=str(uuid.uuid4()), symbol=symbol, side=side, order_type=order_type,
                          quantity=dec_quantity, price=dec_price)
        self.all_orders[new_order.order_id] = new_order
        
        executed_trades = self._process_order_internal(new_order)
        
        if new_order.remaining_quantity > 0:
            if new_order.order_type == OrderType.LIMIT:
                self.add_order_to_book(new_order)
            else:
                new_order.is_live = False
                logger.info(f"{order_type.upper()} order {new_order.order_id[:8]}.. not fully filled. Remainder cancelled.")

        self._update_bbo()
        return executed_trades

    def _process_order_internal(self, incoming_order: Order) -> list[Trade]:
        trades = []
        is_buy = incoming_order.side == OrderSide.BUY
        resting_book = self.asks if is_buy else self.bids

        # *** CRITICAL FIX: Correct sorting logic for price priority ***
        # For BUY orders, match against ASKS from LOWEST price up (ascending)
        # For SELL orders, match against BIDS from HIGHEST price down (descending)
        sorted_prices = sorted(resting_book.keys(), reverse=not is_buy)

        if incoming_order.order_type == OrderType.FOK:
            fillable_qty = Decimal('0')
            for price_level in sorted_prices:
                marketable = (is_buy and price_level <= incoming_order.price) or \
                             (not is_buy and price_level >= incoming_order.price)
                if marketable:
                    fillable_qty += sum(o.remaining_quantity for o in resting_book[price_level].values())
            if fillable_qty < incoming_order.quantity:
                logger.info(f"FOK order {incoming_order.order_id[:8]}.. cannot be fully filled. Cancelling.")
                incoming_order.is_live = False
                return []

        for price_level in list(sorted_prices):
            if incoming_order.remaining_quantity <= 0: break
            if price_level not in resting_book: continue

            if incoming_order.order_type != OrderType.MARKET:
                if (is_buy and price_level > incoming_order.price) or \
                   (not is_buy and price_level < incoming_order.price):
                    break

            orders_at_level = sorted(resting_book[price_level].values(), key=lambda o: o.timestamp)
            for resting_order in orders_at_level:
                if incoming_order.remaining_quantity <= 0: break
                if resting_order.remaining_quantity <= 0: continue

                fill_qty = min(incoming_order.remaining_quantity, resting_order.remaining_quantity)
                if fill_qty > 0:
                    trade = Trade(trade_id=self._generate_trade_id(), symbol=self.symbol, price=price_level,
                                  quantity=fill_qty, aggressor_side=incoming_order.side,
                                  maker_order_id=resting_order.order_id, taker_order_id=incoming_order.order_id)
                    trades.append(trade)
                    self.trades_history.append(trade)
                    
                    incoming_order.filled_quantity += fill_qty
                    resting_order.filled_quantity += fill_qty
                    logger.info(f"Filled {fill_qty} at {price_level} for {incoming_order.order_id[:8]}.. (taker) and {resting_order.order_id[:8]}.. (maker)")

                    if resting_order.remaining_quantity <= 0:
                        self.remove_order_from_book(resting_order)
        return trades

# --- Main execution / Example Usage ---
if __name__ == "__main__":
    engine = MatchingEngine("BTC-USDT")

    logger.info("\n--- Submitting initial ASK orders (SELL side) ---")
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.SELL, "1.0", "30100.0")  # O1
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.SELL, "0.5", "30050.0")  # O2
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.SELL, "2.0", "30100.0")  # O3

    logger.info("\n--- Submitting initial BID orders (BUY side) ---")
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.BUY, "1.0", "29900.0")   # O4
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.BUY, "0.75", "29950.0") # O5
    engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.BUY, "0.25", "29950.0") # O6

    logger.info("\n--- Current BBO and Order Book ---")
    print("BBO:", engine.get_bbo())
    print("Order Book Depth (L2):", engine.get_order_book_depth(5))

    logger.info("\n--- Test Case 1: Marketable BUY Limit Order (should cross) ---")
    trades_1 = engine.submit_order("BTC-USDT", OrderType.LIMIT, OrderSide.BUY, "1.2", "30070.0") # O7
    print("Trades from marketable BUY Limit:", trades_1)
    print("BBO After Trades:", engine.get_bbo())
    print("Order Book Depth (L2) After Trades:", engine.get_order_book_depth(5))

    logger.info("\n--- Test Case 2: Submitting a MARKET BUY Order ---")
    trades_2 = engine.submit_order("BTC-USDT", OrderType.MARKET, OrderSide.BUY, "1.5") # O8
    print("Trades from MARKET BUY:", trades_2)
    print("BBO After Market Buy:", engine.get_bbo())
    print("Order Book Depth (L2) After Market Buy:", engine.get_order_book_depth(5))
    
    logger.info("\n--- Test Case 3: Submitting an IOC BUY Order (partial fill possible) ---")
    trades_3 = engine.submit_order("BTC-USDT", OrderType.IOC, OrderSide.BUY, "3.0", "30150.0") # O9
    print("Trades from IOC BUY:", trades_3)
    print("BBO After IOC Buy:", engine.get_bbo())
    print("Order Book Depth (L2) After IOC Buy:", engine.get_order_book_depth(5))

    logger.info("\n--- Test Case 4: Submitting an FOK SELL Order (should fail if not enough bids) ---")
    trades_4 = engine.submit_order("BTC-USDT", OrderType.FOK, OrderSide.SELL, "3.0", "29800.0") # O10
    print("Trades from FOK SELL (expect empty):", trades_4)
    print("BBO After FOK Fail:", engine.get_bbo())
    print("Order Book Depth (L2) After FOK Fail:", engine.get_order_book_depth(5))
    
    logger.info("\n--- Test Case 5: Submitting an FOK SELL Order (should succeed if enough bids) ---")
    trades_5 = engine.submit_order("BTC-USDT", OrderType.FOK, OrderSide.SELL, "1.5", "29800.0") # O11
    print("Trades from FOK SELL (expect success):", trades_5)
    print("BBO After FOK Success:", engine.get_bbo())
    print("Order Book Depth (L2) After FOK Success:", engine.get_order_book_depth(5))
    
    logger.info("\n--- All Recorded Trades ---")
    for trade in engine.trades_history:
        print(trade)