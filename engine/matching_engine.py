from __future__ import annotations
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from collections import defaultdict
import uuid, datetime, decimal, asyncio

from .models import Order, Trade
from .order_book import OrderBook

class Broadcaster:
    # Simple fan-out broadcaster using in-memory async queues (API layer binds to these).
    def __init__(self):
        self._subs = defaultdict(set)  # topic -> set(asyncio.Queue)
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
            try:
                q.put_nowait(message)
            except Exception:
                pass

class MatchingEngine:
    def __init__(self):
        self.books: Dict[str, OrderBook] = {}
        self.trades_pub = Broadcaster()
        self.md_pub = Broadcaster()

    def _book(self, symbol: str) -> OrderBook:
        if symbol not in self.books:
            self.books[symbol] = OrderBook(symbol)
        return self.books[symbol]

    def _crossable(self, taker: Order, maker_price: Decimal) -> bool:
        if taker.order_type == "market":
            return True
        if taker.side == "buy":
            return taker.price is not None and taker.price >= maker_price
        else:
            return taker.price is not None and taker.price <= maker_price

    def _eligible_side(self, side: str, book: OrderBook):
        return (book.asks if side == "buy" else book.bids)

    def _best_maker_price(self, side: str, book: OrderBook) -> Optional[Decimal]:
        return book.best_ask() if side == "buy" else book.best_bid()

    def _sweep_available(self, taker: Order, book: OrderBook) -> Decimal:
        # Return total available quantity to fill within taker's limit (for FOK).
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
        def ser(x):
            if isinstance(x, decimal.Decimal):
                return format(x, 'f')
            return x
        md_msg = {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": symbol,
            "bids": [[ser(p), ser(q)] for p,q in depth.bids],
            "asks": [[ser(p), ser(q)] for p,q in depth.asks],
        }
        asyncio.create_task(self.md_pub.publish(f"md:{symbol}", md_msg))

    def _emit_trade(self, t: Trade):
        def ser(x):
            if isinstance(x, decimal.Decimal):
                return format(x, 'f')
            return x
        msg = {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": t.symbol,
            "trade_id": t.trade_id,
            "price": ser(t.price),
            "quantity": ser(t.quantity),
            "aggressor_side": t.aggressor_side,
            "maker_order_id": t.maker_order_id,
            "taker_order_id": t.taker_order_id,
        }
        asyncio.create_task(self.trades_pub.publish(f"trades:{t.symbol}", msg))

    def submit(self, order: Order) -> Tuple[List[Trade], Optional[Order]]:
        # Process an incoming order. Returns (trades, resting_order_if_any).
        book = self._book(order.symbol)
        trades: List[Trade] = []
        remaining = order.quantity

        if order.order_type == "fok":
            avail = self._sweep_available(order, book)
            if avail < remaining:
                return ([], None)

        maker_side = self._eligible_side(order.side, book)

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
            t = Trade(
                symbol=order.symbol,
                trade_id=str(uuid.uuid4()),
                price=exec_price,
                quantity=trade_qty,
                aggressor_side=order.side,
                maker_order_id=head.order_id,
                taker_order_id=order.order_id,
            )
            trades.append(t)
            self._emit_trade(t)

        rested = None
        if remaining > 0:
            if order.order_type in ("ioc", "market"):
                rested = None
            elif order.order_type == "fok":
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

    def cancel(self, symbol: str, order_id: str) -> bool:
        b = self._book(symbol)
        ok = b.bids.remove_order(order_id) or b.asks.remove_order(order_id)
        if ok:
            self._emit_md(symbol)
        return ok

    def snapshot(self, symbol: str) -> dict:
        b = self._book(symbol)
        d = b.depth(10)
        def ser(x):
            if isinstance(x, decimal.Decimal):
                return format(x, 'f')
            return x
        return {
            "timestamp": datetime.datetime.utcnow().isoformat(timespec="microseconds") + "Z",
            "symbol": symbol,
            "bids": [[ser(p), ser(q)] for p,q in d.bids],
            "asks": [[ser(p), ser(q)] for p,q in d.asks],
        }
