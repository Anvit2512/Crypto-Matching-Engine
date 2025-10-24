from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal, getcontext
from typing import Optional, List, Literal
import uuid, time

getcontext().prec = 28

Side = Literal["buy", "sell"]
OrderType = Literal["market", "limit", "ioc", "fok"]

def now_ns() -> int:
    return time.time_ns()

def gen_id() -> str:
    return str(uuid.uuid4())

@dataclass
class Order:
    symbol: str
    order_type: OrderType
    side: Side
    quantity: Decimal
    price: Optional[Decimal] = None
    order_id: str = field(default_factory=gen_id)
    ts_ns: int = field(default_factory=now_ns)

    def clone_shallow(self, **overrides) -> "Order":
        data = self.__dict__.copy()
        data.update(overrides)
        return Order(**data)

@dataclass
class Trade:
    symbol: str
    trade_id: str
    price: Decimal
    quantity: Decimal
    aggressor_side: Side
    maker_order_id: str
    taker_order_id: str
    ts_ns: int = field(default_factory=now_ns)

@dataclass
class BBO:
    symbol: str
    best_bid: Optional[Decimal]
    best_bid_qty: Decimal
    best_ask: Optional[Decimal]
    best_ask_qty: Decimal
    ts_ns: int = field(default_factory=now_ns)

@dataclass
class DepthSnapshot:
    symbol: str
    bids: List[tuple]
    asks: List[tuple]
    ts_ns: int = field(default_factory=now_ns)
