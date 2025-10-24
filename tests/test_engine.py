from decimal import Decimal
from engine.matching_engine import MatchingEngine
from engine.models import Order

SYM = "BTC-USDT"

def mk(side, qty, px=None, t="limit"):
    return Order(symbol=SYM, order_type=t, side=side, quantity=Decimal(str(qty)), price=Decimal(str(px)) if px else None)

def test_price_time_priority():
    eng = MatchingEngine()
    a = mk("sell", 1, 101)
    b = mk("sell", 1, 101)
    c = mk("buy",  2,  105)  # crosses
    eng.submit(a)
    eng.submit(b)
    trades, _ = eng.submit(c)
    assert len(trades) == 2
    assert trades[0].maker_order_id == a.order_id
    assert trades[1].maker_order_id == b.order_id
    assert trades[0].price == Decimal("101")

def test_partial_fill_and_rest():
    eng = MatchingEngine()
    eng.submit(mk("sell", 1.5, 100))
    buy = mk("buy", 3, 100)
    trades, rest = eng.submit(buy)
    assert len(trades) == 1
    assert trades[0].quantity == Decimal("1.5")
    assert rest is not None and rest.quantity == Decimal("1.5")

def test_ioc_cancels_remainder():
    eng = MatchingEngine()
    eng.submit(mk("sell", 1, 100))
    ioc = mk("buy", 2, 100, t="ioc")
    trades, rest = eng.submit(ioc)
    assert len(trades) == 1 and rest is None

def test_fok_requires_full():
    eng = MatchingEngine()
    eng.submit(mk("sell", 1, 100))
    fok = mk("buy", 2, 101, t="fok")
    trades, rest = eng.submit(fok)
    assert len(trades) == 0 and rest is None

    eng.submit(mk("sell", 1, 100))
    fok2 = mk("buy", 2, 101, t="fok")
    trades, rest = eng.submit(fok2)
    assert sum(t.quantity for t in trades) == Decimal("2") and rest is None
