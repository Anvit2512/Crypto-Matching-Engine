# from __future__ import annotations
# from dataclasses import dataclass, field
# from decimal import Decimal, getcontext
# from typing import Optional, List, Literal
# import uuid, time

# getcontext().prec = 28

# Side = Literal["buy", "sell"]
# OrderType = Literal["market", "limit", "ioc", "fok"]

# def now_ns() -> int:
#     return time.time_ns()

# def gen_id() -> str:
#     return str(uuid.uuid4())

# @dataclass
# class Order:
#     symbol: str
#     order_type: OrderType
#     side: Side
#     quantity: Decimal
#     price: Optional[Decimal] = None
#     order_id: str = field(default_factory=gen_id)
#     ts_ns: int = field(default_factory=now_ns)

#     def clone_shallow(self, **overrides) -> "Order":
#         data = self.__dict__.copy()
#         data.update(overrides)
#         return Order(**data)

# @dataclass
# class Trade:
#     symbol: str
#     trade_id: str
#     price: Decimal
#     quantity: Decimal
#     aggressor_side: Side
#     maker_order_id: str
#     taker_order_id: str
#     ts_ns: int = field(default_factory=now_ns)

# @dataclass
# class BBO:
#     symbol: str
#     best_bid: Optional[Decimal]
#     best_bid_qty: Decimal
#     best_ask: Optional[Decimal]
#     best_ask_qty: Decimal
#     ts_ns: int = field(default_factory=now_ns)

# @dataclass
# class DepthSnapshot:
#     symbol: str
#     bids: List[tuple]
#     asks: List[tuple]
#     ts_ns: int = field(default_factory=now_ns)


# engine/models.py
from __future__ import annotations
from dataclasses import dataclass, field, asdict
from decimal import Decimal, getcontext
from typing import Optional, List, Literal, Dict, Any
import uuid, time

# Higher precision for crypto
getcontext().prec = 28

Side = Literal["buy", "sell"]
# Extended order types with bonus features
OrderType = Literal[
    "market", "limit", "ioc", "fok",
    "stop_market", "stop_limit", "take_profit"
]

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
    price: Optional[Decimal] = None  # required for limit / ioc / fok / stop_limit
    # Bonus trigger fields (for stop/take-profit):
    trigger_price: Optional[Decimal] = None  # required for stop_market/stop_limit/take_profit
    # Bookkeeping
    order_id: str = field(default_factory=gen_id)
    ts_ns: int = field(default_factory=now_ns)

    def clone_shallow(self, **overrides) -> "Order":
        data = self.__dict__.copy()
        data.update(overrides)
        return Order(**data)

    def to_json(self) -> Dict[str, Any]:
        def sd(x):
            return None if x is None else str(x)
        return {
            "symbol": self.symbol,
            "order_type": self.order_type,
            "side": self.side,
            "quantity": str(self.quantity),
            "price": sd(self.price),
            "trigger_price": sd(self.trigger_price),
            "order_id": self.order_id,
            "ts_ns": self.ts_ns,
        }

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "Order":
        def dec(x): return None if x in (None, "", "null") else Decimal(str(x))
        return Order(
            symbol=d["symbol"],
            order_type=d["order_type"],
            side=d["side"],
            quantity=Decimal(str(d["quantity"])),
            price=dec(d.get("price")),
            trigger_price=dec(d.get("trigger_price")),
            order_id=d["order_id"],
            ts_ns=int(d.get("ts_ns") or now_ns()),
        )

@dataclass
class Trade:
    symbol: str
    trade_id: str
    price: Decimal
    quantity: Decimal
    aggressor_side: Side
    maker_order_id: str
    taker_order_id: str
    # Bonus: fee model
    maker_fee: Decimal = Decimal("0")
    taker_fee: Decimal = Decimal("0")
    ts_ns: int = field(default_factory=now_ns)

    def to_json(self):
        return {
            "symbol": self.symbol,
            "trade_id": self.trade_id,
            "price": str(self.price),
            "quantity": str(self.quantity),
            "aggressor_side": self.aggressor_side,
            "maker_order_id": self.maker_order_id,
            "taker_order_id": self.taker_order_id,
            "maker_fee": str(self.maker_fee),
            "taker_fee": str(self.taker_fee),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(self.ts_ns/1e9)),
        }

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
    bids: List[tuple]  # (price, qty) desc
    asks: List[tuple]  # (price, qty) asc
    ts_ns: int = field(default_factory=now_ns)
