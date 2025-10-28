# from __future__ import annotations
# from decimal import Decimal
# from typing import Dict, List, Optional, Tuple
# from collections import defaultdict
# import uuid, datetime, decimal, asyncio

# from .models import Order, Trade
# from .order_book import OrderBook

# class Broadcaster:
#     # Simple fan-out broadcaster using in-memory async queues (API layer binds to these).
#     def __init__(self):
#         self._subs = defaultdict(set)  # topic -> set(asyncio.Queue)
#         self._lock = asyncio.Lock()

#     async def subscribe(self, topic: str):
#         q = asyncio.Queue(maxsize=1000)
#         async with self._lock:
#             self._subs[topic].add(q)
#         return q

#     async def unsubscribe(self, topic: str, q):
#         async with self._lock:
#             self._subs[topic].discard(q)

#     async def publish(self, topic: str, message: dict):
#         for q in list(self._subs.get(topic, [])):
#             try:
#                 q.put_nowait(message)
#             except Exception:
#                 pass

# class MatchingEngine:
#     def __init__(self):
#         self.books: Dict[str, OrderBook] = {}
#         self.trades_pub = Broadcaster()
#         self.md_pub = Broadcaster()

#     def _book(self, symbol: str) -> OrderBook:
#         if symbol not in self.books:
#             self.books[symbol] = OrderBook(symbol)
#         return self.books[symbol]

#     def _crossable(self, taker: Order, maker_price: Decimal) -> bool:
#         if taker.order_type == "market":
#             return True
#         if taker.side == "buy":
#             return taker.price is not None and taker.price >= maker_price
#         else:
#             return taker.price is not None and taker.price <= maker_price

#     def _eligible_side(self, side: str, book: OrderBook):
#         return (book.asks if side == "buy" else book.bids)

#     def _best_maker_price(self, side: str, book: OrderBook) -> Optional[Decimal]:
#         return book.best_ask() if side == "buy" else book.best_bid()

#     def _sweep_available(self, taker: Order, book: OrderBook) -> Decimal:
#         # Return total available quantity to fill within taker's limit (for FOK).
#         maker = self._eligible_side(taker.side, book)
#         total = Decimal("0")
#         prices = sorted(maker.levels.keys(), reverse=(maker.side=="buy"))
#         for p in prices:
#             qty_at = maker.qty_at_price.get(p, Decimal("0"))
#             if qty_at <= 0:
#                 continue
#             if self._crossable(taker, p):
#                 total += qty_at
#             else:
#                 break
#         return total

#     def _emit_md(self, symbol: str):
#         book = self._book(symbol)
#         depth = book.depth(10)
#         def ser(x):
#             if isinstance(x, decimal.Decimal):
#                 return format(x, 'f')
#             return x
#         md_msg = {
#             "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
#             "symbol": symbol,
#             "bids": [[ser(p), ser(q)] for p,q in depth.bids],
#             "asks": [[ser(p), ser(q)] for p,q in depth.asks],
#         }
#         asyncio.create_task(self.md_pub.publish(f"md:{symbol}", md_msg))

#     def _emit_trade(self, t: Trade):
#         def ser(x):
#             if isinstance(x, decimal.Decimal):
#                 return format(x, 'f')
#             return x
#         msg = {
#             "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
#             "symbol": t.symbol,
#             "trade_id": t.trade_id,
#             "price": ser(t.price),
#             "quantity": ser(t.quantity),
#             "aggressor_side": t.aggressor_side,
#             "maker_order_id": t.maker_order_id,
#             "taker_order_id": t.taker_order_id,
#         }
#         asyncio.create_task(self.trades_pub.publish(f"trades:{t.symbol}", msg))

#     def submit(self, order: Order) -> Tuple[List[Trade], Optional[Order]]:
#         # Process an incoming order. Returns (trades, resting_order_if_any).
#         book = self._book(order.symbol)
#         trades: List[Trade] = []
#         remaining = order.quantity

#         if order.order_type == "fok":
#             avail = self._sweep_available(order, book)
#             if avail < remaining:
#                 return ([], None)

#         maker_side = self._eligible_side(order.side, book)

#         while remaining > 0:
#             best = self._best_maker_price(order.side, book)
#             if best is None or not self._crossable(order, best):
#                 break
#             head = maker_side.pop_best_order()
#             if head is None:
#                 break
#             trade_qty = min(remaining, head.quantity)
#             exec_price = best
#             head.quantity -= trade_qty
#             remaining -= trade_qty
#             maker_side.reduce_head(exec_price, trade_qty)
#             t = Trade(
#                 symbol=order.symbol,
#                 trade_id=str(uuid.uuid4()),
#                 price=exec_price,
#                 quantity=trade_qty,
#                 aggressor_side=order.side,
#                 maker_order_id=head.order_id,
#                 taker_order_id=order.order_id,
#             )
#             trades.append(t)
#             self._emit_trade(t)

#         rested = None
#         if remaining > 0:
#             if order.order_type in ("ioc", "market"):
#                 rested = None
#             elif order.order_type == "fok":
#                 rested = None
#             else:
#                 o2 = order.clone_shallow(quantity=remaining)
#                 if o2.side == "buy":
#                     book.bids.add(o2)
#                 else:
#                     book.asks.add(o2)
#                 rested = o2

#         self._emit_md(order.symbol)
#         return (trades, rested)

#     def cancel(self, symbol: str, order_id: str) -> bool:
#         b = self._book(symbol)
#         ok = b.bids.remove_order(order_id) or b.asks.remove_order(order_id)
#         if ok:
#             self._emit_md(symbol)
#         return ok

#     def snapshot(self, symbol: str) -> dict:
#         b = self._book(symbol)
#         d = b.depth(10)
#         def ser(x):
#             if isinstance(x, decimal.Decimal):
#                 return format(x, 'f')
#             return x
#         return {
#             "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
#             "symbol": symbol,
#             "bids": [[ser(p), ser(q)] for p,q in d.bids],
#             "asks": [[ser(p), ser(q)] for p,q in d.asks],
#         }


# engine/matching_engine.py
from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import uuid, datetime, decimal, asyncio, json, os

from .models import Order, Trade
from .order_book import OrderBook

def ser_decimal(x):
    if isinstance(x, decimal.Decimal):
        return format(x, "f")
    return x

class Broadcaster:
    """Fan-out broadcaster using in-memory async queues."""
    def __init__(self):
        self._subs = defaultdict(set)
        self._lock = asyncio.Lock()

    async def subscribe(self, topic: str):
        q = asyncio.Queue(maxsize=1000)
        async with self._lock:
            self._subs[topic].add(q)
        return q

    async def unsubscribe(self, topic: str, q):
        async with self._lock:
            self._subs[topic].discard(q)

    async def publish(self, topic: str, message: dict):
        for q in list(self._subs.get(topic, [])):
            try: q.put_nowait(message)
            except Exception: pass


class MatchingEngine:
    """
    Extended engine with:
    - stop_market, stop_limit, take_profit triggers
    - JSON persistence (per symbol)
    - fee model
    - per-symbol lock for concurrency
    """
    def __init__(self, maker_fee_bps: int = 10, taker_fee_bps: int = 20, state_dir: str = "state"):
        self.books: Dict[str, OrderBook] = {}
        self.triggers: Dict[str, List[Order]] = defaultdict(list)  # pending trigger orders (not on book)
        self.trades_pub = Broadcaster()
        self.md_pub = Broadcaster()
        self.locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.maker_fee = Decimal(maker_fee_bps) / Decimal(10_000)
        self.taker_fee = Decimal(taker_fee_bps) / Decimal(10_000)
        self.state_dir = state_dir
        os.makedirs(self.state_dir, exist_ok=True)

    def _book(self, symbol: str) -> OrderBook:
        if symbol not in self.books:
            self.books[symbol] = OrderBook(symbol)
        return self.books[symbol]

    def _eligible_side(self, side: str, book: OrderBook):
        return (book.asks if side == "buy" else book.bids)

    def _best_maker_price(self, side: str, book: OrderBook) -> Optional[Decimal]:
        return book.best_ask() if side == "buy" else book.best_bid()

    def _crossable(self, taker: Order, maker_price: Decimal) -> bool:
        if taker.order_type == "market":
            return True
        if taker.side == "buy":
            return taker.price is not None and taker.price >= maker_price
        else:
            return taker.price is not None and taker.price <= maker_price

    def _sweep_available(self, taker: Order, book: OrderBook) -> Decimal:
        maker = self._eligible_side(taker.side, book)
        total = Decimal("0")
        prices = sorted(maker.levels.keys(), reverse=(maker.side=="buy"))
        for p in prices:
            qty_at = maker.qty_at_price.get(p, Decimal("0"))
            if qty_at <= 0:
                continue
            if self._crossable(taker, p):
                total += qty_at
            else:
                break
        return total

    def _emit_md(self, symbol: str):
        book = self._book(symbol)
        depth = book.depth(10)
        md_msg = {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": symbol,
            "bids": [[ser_decimal(p), ser_decimal(q)] for p,q in depth.bids],
            "asks": [[ser_decimal(p), ser_decimal(q)] for p,q in depth.asks],
        }
        asyncio.create_task(self.md_pub.publish(f"md:{symbol}", md_msg))

    def _emit_trade(self, t: Trade):
        msg = {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": t.symbol,
            "trade_id": t.trade_id,
            "price": ser_decimal(t.price),
            "quantity": ser_decimal(t.quantity),
            "aggressor_side": t.aggressor_side,
            "maker_order_id": t.maker_order_id,
            "taker_order_id": t.taker_order_id,
            "maker_fee": ser_decimal(t.maker_fee),
            "taker_fee": ser_decimal(t.taker_fee),
        }
        asyncio.create_task(self.trades_pub.publish(f"trades:{t.symbol}", msg))

    # ---------- Trigger logic (stop / take-profit) ----------

    def _trigger_condition(self, o: Order, last_price: Decimal) -> bool:
        if o.trigger_price is None:
            return False
        # stop_market & stop_limit: activate when price moves against you (protective)
        if o.order_type in ("stop_market", "stop_limit"):
            if o.side == "buy":
                return last_price >= o.trigger_price
            else:
                return last_price <= o.trigger_price
        # take_profit: activate when price hits favorable target
        if o.order_type == "take_profit":
            if o.side == "sell":
                return last_price >= o.trigger_price
            else:
                return last_price <= o.trigger_price
        return False

    def _activate_trigger(self, o: Order) -> Order:
        # Convert to child live order:
        if o.order_type == "stop_market" or o.order_type == "take_profit":
            return Order(
                symbol=o.symbol, order_type="market", side=o.side,
                quantity=o.quantity, price=None
            )
        elif o.order_type == "stop_limit":
            if o.price is None:
                # default to trigger price if no limit provided
                child_px = o.trigger_price
            else:
                child_px = o.price
            return Order(
                symbol=o.symbol, order_type="limit", side=o.side,
                quantity=o.quantity, price=child_px
            )
        return o  # should not happen

    async def _check_and_fire_triggers(self, symbol: str, last_price: Decimal):
        # Called on each trade to activate eligible triggers
        remaining = []
        for o in self.triggers.get(symbol, []):
            if self._trigger_condition(o, last_price):
                child = self._activate_trigger(o)
                # Submit child order immediately (await!)
                await self.submit(child)
            else:
                remaining.append(o)
        self.triggers[symbol] = remaining


    # ---------- Public operations ----------


    async def submit(self, order: Order) -> Tuple[List[Trade], Optional[Order]]:
        """
        Process an incoming order (or activated child).
        Advanced types:
        - stop_market/stop_limit/take_profit -> store in triggers (not live) until triggered.
        Returns (trades, resting_order_if_any)
        """
        # Trigger orders do not hit the book immediately
        if order.order_type in ("stop_market", "stop_limit", "take_profit"):
            self.triggers[order.symbol].append(order)
            # No MD emit (no book change)
            return ([], None)

        trades: List[Trade] = []
        remaining = order.quantity
        book = self._book(order.symbol)
        maker_side = self._eligible_side(order.side, book)

        async with self.locks[order.symbol]:

            # FOK precheck
            if order.order_type == "fok":
                avail = self._sweep_available(order, book)
                if avail < remaining:
                    self._emit_md(order.symbol)
                    return ([], None)

            # Sweep best->next under price-time
            while remaining > 0:
                best = self._best_maker_price(order.side, book)
                if best is None or not self._crossable(order, best):
                    break
                head = maker_side.pop_best_order()
                if head is None:
                    break
                trade_qty = min(remaining, head.quantity)
                exec_price = best
                head.quantity -= trade_qty
                remaining -= trade_qty
                maker_side.reduce_head(exec_price, trade_qty)

                # Fees
                maker_fee = (trade_qty * exec_price) * self.maker_fee
                taker_fee = (trade_qty * exec_price) * self.taker_fee

                t = Trade(
                    symbol=order.symbol,
                    trade_id=str(uuid.uuid4()),
                    price=exec_price,
                    quantity=trade_qty,
                    aggressor_side=order.side,
                    maker_order_id=head.order_id,
                    taker_order_id=order.order_id,
                    maker_fee=maker_fee,
                    taker_fee=taker_fee,
                )
                trades.append(t)
                self._emit_trade(t)  # uses create_task internally

                # Trigger activation check on each trade (await!)
                await self._check_and_fire_triggers(order.symbol, exec_price)

            rested = None
            if remaining > 0:
                if order.order_type in ("ioc", "market", "fok"):
                    rested = None
                else:
                    o2 = order.clone_shallow(quantity=remaining)
                    if o2.side == "buy":
                        book.bids.add(o2)
                    else:
                        book.asks.add(o2)
                    rested = o2

            self._emit_md(order.symbol)
            return (trades, rested)

    async def cancel(self, symbol: str, order_id: str) -> bool:
        async with self.locks[symbol]:
            b = self._book(symbol)
            ok = b.bids.remove_order(order_id) or b.asks.remove_order(order_id)
            if not ok:
                # maybe it is a trigger order
                lst = self.triggers.get(symbol, [])
                n = len(lst)
                lst = [o for o in lst if o.order_id != order_id]
                ok = (len(lst) != n)
                self.triggers[symbol] = lst
            if ok:
                self._emit_md(symbol)
            return ok


    def snapshot(self, symbol: str) -> dict:
        b = self._book(symbol)
        d = b.depth(10)
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": symbol,
            "bids": [[ser_decimal(p), ser_decimal(q)] for p,q in d.bids],
            "asks": [[ser_decimal(p), ser_decimal(q)] for p,q in d.asks],
        }

    # ---------- Persistence (per symbol) ----------

    def _state_path(self, symbol: str) -> str:
        return os.path.join(self.state_dir, f"orderbook_{symbol}.json")

    def save_state(self, symbol: str) -> bool:
        b = self._book(symbol)
        data = {
            "symbol": symbol,
            "bids": [[str(p), [o.to_json() for o in list(b.bids.levels[p])]] for p in b.bids.levels],
            "asks": [[str(p), [o.to_json() for o in list(b.asks.levels[p])]] for p in b.asks.levels],
            "triggers": [o.to_json() for o in self.triggers.get(symbol, [])]
        }
        with open(self._state_path(symbol), "w", encoding="utf-8") as f:
            json.dump(data, f)
        return True

    async def load_state(self, symbol: str) -> bool:
        path = self._state_path(symbol)
        if not os.path.exists(path):
            return False
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # reset
        async with self.locks[symbol]:
            self.books[symbol] = OrderBook(symbol)
            self.triggers[symbol] = []
            b = self._book(symbol)
            for _, orders in data.get("bids", []):
                for od in orders:
                    o = Order.from_json(od)
                    b.bids.add(o)
            for _, orders in data.get("asks", []):
                for od in orders:
                    o = Order.from_json(od)
                    b.asks.add(o)
            self.triggers[symbol] = [Order.from_json(od) for od in data.get("triggers", [])]
            self._emit_md(symbol)
            return True
