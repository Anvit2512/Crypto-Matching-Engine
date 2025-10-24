from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal, InvalidOperation
import orjson
from engine.models import Order
from engine.matching_engine import MatchingEngine

app = FastAPI(title="Crypto Matching Engine", version="0.1.0")
engine = MatchingEngine()

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # or ["http://127.0.0.1:5500", ...] if you prefer specific
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)

class OrderIn(BaseModel):
    symbol: str = Field(examples=["BTC-USDT"])
    order_type: str = Field(pattern="^(market|limit|ioc|fok)$")
    side: str = Field(pattern="^(buy|sell)$")
    quantity: str
    price: str | None = None

    model_config = ConfigDict(extra="forbid")

    def to_order(self) -> Order:
        try:
            qty = Decimal(self.quantity)
            if qty <= 0:
                raise ValueError("quantity must be positive")
        except (InvalidOperation, ValueError):
            raise HTTPException(status_code=422, detail="Invalid quantity")

        px = None
        if self.order_type in ("limit", "ioc", "fok"):
            if self.price is None:
                raise HTTPException(status_code=422, detail="price required for this order_type")
            try:
                px = Decimal(self.price)
                if px <= 0:
                    raise ValueError("price must be positive")
            except (InvalidOperation, ValueError):
                raise HTTPException(status_code=422, detail="Invalid price")

        return Order(
            symbol=self.symbol,
            order_type=self.order_type,  # type: ignore
            side=self.side,              # type: ignore
            quantity=qty,
            price=px,
        )

@app.post("/orders")
async def submit_order(o: OrderIn):
    order = o.to_order()
    trades, rested = engine.submit(order)
    def ser_decimal(x):
        return format(x, "f") if isinstance(x, Decimal) else x
    return {
        "order_id": order.order_id,
        "resting": rested is not None,
        "resting_order_id": rested.order_id if rested else None,
        "resting_qty": ser_decimal(rested.quantity) if rested else None,
        "trades": [
            {
                "trade_id": t.trade_id,
                "price": ser_decimal(t.price),
                "quantity": ser_decimal(t.quantity),
                "aggressor_side": t.aggressor_side,
                "maker_order_id": t.maker_order_id,
                "taker_order_id": t.taker_order_id,
            } for t in trades
        ]
    }

@app.websocket("/ws/marketdata")
async def ws_marketdata(ws: WebSocket, symbol: str):
    await ws.accept()
    q = await engine.md_pub.subscribe(f"md:{symbol}")
    try:
        await ws.send_text(orjson.dumps(engine.snapshot(symbol)).decode())
        while True:
            msg = await q.get()
            await ws.send_text(orjson.dumps(msg).decode())
    except WebSocketDisconnect:
        pass
    finally:
        await engine.md_pub.unsubscribe(f"md:{symbol}", q)

@app.websocket("/ws/trades")
async def ws_trades(ws: WebSocket, symbol: str):
    await ws.accept()
    q = await engine.trades_pub.subscribe(f"trades:{symbol}")
    try:
        while True:
            msg = await q.get()
            await ws.send_text(orjson.dumps(msg).decode())
    except WebSocketDisconnect:
        pass
    finally:
        await engine.trades_pub.unsubscribe(f"trades:{symbol}", q)
