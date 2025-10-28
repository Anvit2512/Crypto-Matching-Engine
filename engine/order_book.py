# from __future__ import annotations
# from decimal import Decimal
# from collections import deque
# import heapq
# from typing import Deque, Dict, Optional, List, Tuple
# from .models import Order, BBO, DepthSnapshot

# class PriceLevelBook:
#     # Maintains FIFO queues per price level and a heap of active price levels.
#     # For bids: max-heap via negative prices. For asks: min-heap.
#     def __init__(self, side: str):
#         assert side in ("buy", "sell")
#         self.side = side
#         self.levels: Dict[Decimal, Deque[Order]] = {}
#         self.heap: List[Decimal] = []
#         self.qty_at_price: Dict[Decimal, Decimal] = {}

#     def _heap_key(self, price: Decimal) -> Decimal:
#         return price if self.side == "sell" else -price

#     def add(self, order: Order):
#         q = self.levels.get(order.price)
#         if q is None:
#             self.levels[order.price] = q = deque()
#             import math
#             heapq.heappush(self.heap, self._heap_key(order.price))
#             self.qty_at_price[order.price] = Decimal("0")
#         q.append(order)
#         self.qty_at_price[order.price] += order.quantity

#     def best_price(self) -> Optional[Decimal]:
#         while self.heap:
#             key = self.heap[0]
#             price = key if self.side == "sell" else -key
#             q = self.levels.get(price)
#             if q and self.qty_at_price.get(price, Decimal("0")) > 0:
#                 return price
#             heapq.heappop(self.heap)
#             self.levels.pop(price, None)
#             self.qty_at_price.pop(price, None)
#         return None

#     def pop_best_order(self) -> Optional[Order]:
#         price = self.best_price()
#         if price is None:
#             return None
#         q = self.levels[price]
#         while q:
#             o = q[0]
#             if o.quantity > 0:
#                 return o
#             q.popleft()
#         self.qty_at_price[price] = Decimal("0")
#         self.levels.pop(price, None)
#         # Remove corresponding heap top if matches
#         if self.heap:
#             if (self.side == "sell" and self.heap[0] == price) or (self.side == "buy" and self.heap[0] == -price):
#                 heapq.heappop(self.heap)
#         return self.pop_best_order()

#     def reduce_head(self, price: Decimal, qty: Decimal):
#         self.qty_at_price[price] -= qty
#         if self.qty_at_price[price] <= 0:
#             self.qty_at_price[price] = Decimal("0")

#     def remove_order(self, order_id: str) -> bool:
#         for price, q in list(self.levels.items()):
#             for o in list(q):
#                 if o.order_id == order_id:
#                     self.qty_at_price[price] -= o.quantity
#                     q.remove(o)
#                     return True
#         return False

#     def aggregate(self, depth: int) -> List[Tuple[Decimal, Decimal]]:
#         result = []
#         prices = list(self.levels.keys())
#         prices.sort(reverse=(self.side=="buy"))
#         for p in prices:
#             qty = self.qty_at_price.get(p, Decimal("0"))
#             if qty > 0:
#                 result.append((p, qty))
#                 if len(result) >= depth:
#                     break
#         return result


# class OrderBook:
#     def __init__(self, symbol: str):
#         self.symbol = symbol
#         self.bids = PriceLevelBook("buy")
#         self.asks = PriceLevelBook("sell")

#     def best_bid(self):
#         return self.bids.best_price()

#     def best_ask(self):
#         return self.asks.best_price()

#     def bbo(self) -> BBO:
#         bb = self.best_bid()
#         ba = self.best_ask()
#         bb_qty = self.bids.qty_at_price.get(bb, Decimal("0")) if bb is not None else Decimal("0")
#         ba_qty = self.asks.qty_at_price.get(ba, Decimal("0")) if ba is not None else Decimal("0")
#         return BBO(symbol=self.symbol, best_bid=bb, best_bid_qty=bb_qty, best_ask=ba, best_ask_qty=ba_qty)

#     def depth(self, d: int = 10) -> DepthSnapshot:
#         return DepthSnapshot(symbol=self.symbol, bids=self.bids.aggregate(d), asks=self.asks.aggregate(d))


# engine/order_book.py
from __future__ import annotations
from decimal import Decimal
from collections import deque
import heapq
from typing import Deque, Dict, Optional, List, Tuple
from .models import Order, BBO, DepthSnapshot

class PriceLevelBook:
    # Maintains FIFO queues per price level and a heap of active price levels.
    # For bids: max-heap via negative prices. For asks: min-heap.
    def __init__(self, side: str):
        assert side in ("buy", "sell")
        self.side = side
        self.levels: Dict[Decimal, Deque[Order]] = {}
        self.heap: List[Decimal] = []
        self.qty_at_price: Dict[Decimal, Decimal] = {}

    def _heap_key(self, price: Decimal) -> Decimal:
        return price if self.side == "sell" else -price

    def add(self, order: Order):
        q = self.levels.get(order.price)
        if q is None:
            self.levels[order.price] = q = deque()
            heapq.heappush(self.heap, self._heap_key(order.price))
            self.qty_at_price[order.price] = Decimal("0")
        q.append(order)
        self.qty_at_price[order.price] += order.quantity

    def best_price(self) -> Optional[Decimal]:
        while self.heap:
            key = self.heap[0]
            price = key if self.side == "sell" else -key
            q = self.levels.get(price)
            if q and self.qty_at_price.get(price, Decimal("0")) > 0:
                return price
            heapq.heappop(self.heap)
            self.levels.pop(price, None)
            self.qty_at_price.pop(price, None)
        return None

    def pop_best_order(self) -> Optional[Order]:
        price = self.best_price()
        if price is None:
            return None
        q = self.levels[price]
        while q:
            o = q[0]
            if o.quantity > 0:
                return o
            q.pop()
        self.qty_at_price[price] = Decimal("0")
        self.levels.pop(price, None)
        if self.heap and ((self.side=="sell" and self.heap[0]==price) or (self.side=="buy" and self.heap[0]==-price)):
            heapq.heappop(self.heap)
        return self.pop_best_order()

    def reduce_head(self, price: Decimal, qty: Decimal):
        self.qty_at_price[price] -= qty
        if self.qty_at_price[price] <= 0:
            self.qty_at_price[price] = Decimal("0")

    def remove_order(self, order_id: str) -> bool:
        for price, q in list(self.levels.items()):
            for o in list(q):
                if o.order_id == order_id:
                    self.qty_at_price[price] -= o.quantity
                    q.remove(o)
                    return True
        return False

    def aggregate(self, depth: int) -> List[Tuple[Decimal, Decimal]]:
        result = []
        prices = list(self.levels.keys())
        prices.sort(reverse=(self.side=="buy"))
        for p in prices:
            qty = self.qty_at_price.get(p, Decimal("0"))
            if qty > 0:
                result.append((p, qty))
                if len(result) >= depth:
                    break
        return result


class OrderBook:
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.bids = PriceLevelBook("buy")
        self.asks = PriceLevelBook("sell")

    def best_bid(self):
        return self.bids.best_price()

    def best_ask(self):
        return self.asks.best_price()

    def bbo(self) -> BBO:
        bb = self.best_bid()
        ba = self.best_ask()
        bb_qty = self.bids.qty_at_price.get(bb, Decimal("0")) if bb is not None else Decimal("0")
        ba_qty = self.asks.qty_at_price.get(ba, Decimal("0")) if ba is not None else Decimal("0")
        return BBO(symbol=self.symbol, best_bid=bb, best_bid_qty=bb_qty, best_ask=ba, best_ask_qty=ba_qty)

    def depth(self, d: int = 10) -> DepthSnapshot:
        return DepthSnapshot(symbol=self.symbol, bids=self.bids.aggregate(d), asks=self.asks.aggregate(d))
