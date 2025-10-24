⚡ Crypto Matching Engine (Python, REG NMS–Inspired)

A high-performance cryptocurrency matching engine implementing REG NMS–style price–time priority and internal order protection.
Includes a built-in REST API, WebSocket market data & trade streams, and a simple HTML dashboard frontend.

✨ Features

Price–Time Priority (FIFO) within each price level

Internal Trade-Through Protection — marketable orders sweep the book from best price outward

Supports core order types:

🟢 market

🟡 limit

🔵 ioc (Immediate-Or-Cancel)

🔴 fok (Fill-Or-Kill)

Real-time BBO (Best Bid & Offer) and Top-10 Depth feed via WebSocket

Real-time Trade Execution Stream

REST API for order submission

Structured logging and unit tests

Optional HTML/CSS frontend for visualization

⚙️ Quick Start
# 1. Create environment
python -m venv .venv
#    Windows: .venv\Scripts\activate
#    Linux/Mac: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the matching engine API
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

📡 API Endpoints
🔹 Submit Order — POST /orders

Example request:

{
  "symbol": "BTC-USDT",
  "order_type": "limit",
  "side": "buy",
  "quantity": "0.5",
  "price": "60000"
}


Example response:

{
  "order_id": "f11c2460-de0b-46cc-9500-4f585ab36a9d",
  "resting": false,
  "trades": [
    {
      "trade_id": "c7281732-4207-4e3b-9cbe-7ffbc7e34042",
      "price": "60000",
      "quantity": "0.5",
      "aggressor_side": "buy"
    }
  ]
}

🔹 Market Data — WS /ws/marketdata?symbol=BTC-USDT

Real-time Top-10 Depth updates.

{
  "timestamp": "2025-10-24T04:41:51.774Z",
  "symbol": "BTC-USDT",
  "bids": [["59990","2.5"], ["59980","1.0"]],
  "asks": [["60010","1.2"], ["60020","0.8"]]
}

🔹 Trades — WS /ws/trades?symbol=BTC-USDT

Real-time trade execution feed.

{
  "timestamp": "2025-10-24T04:41:51.774Z",
  "symbol": "BTC-USDT",
  "trade_id": "16ad2226-0e17-4ef3-8c1f-618b94df5446",
  "price": "60100",
  "quantity": "0.5",
  "aggressor_side": "buy",
  "maker_order_id": "cc56e375-0486-4349-bd79-aa7ce00490f8",
  "taker_order_id": "1471c8e2-c8f7-4a72-a2c2-53bed4f02c5a"
}

🧩 Example Tests

1️⃣ Limit + Market Fill

# Add resting ask
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"1","price":"60000"}'

# Cross with market buy
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"market","side":"buy","quantity":"1"}'


2️⃣ IOC Partial Fill

# Sell 0.5 available
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"0.5","price":"60100"}'

# IOC buy 2.0 — partial fill + cancel remainder
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"ioc","side":"buy","quantity":"2.0","price":"60100"}'


3️⃣ FOK All-or-Nothing

# Seed liquidity
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"2","price":"59990"}'
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"limit","side":"sell","quantity":"3","price":"60000"}'

# FOK buy 5.0 @60000 → fills all
curl -X POST localhost:8000/orders -H "Content-Type: application/json" \
-d '{"symbol":"BTC-USDT","order_type":"fok","side":"buy","quantity":"5.0","price":"60000"}'

🧠 Design Overview

Order Book

Bid side → max-heap by price

Ask side → min-heap by price

Each price level stores a FIFO deque of orders.

Matching Logic

Marketable orders sweep the book from best price outward.

FOK pre-validates full quantity before execution.

IOC executes partials and cancels the rest.

Matching emits trade events + market data updates.

Performance

O(log N) best-price lookups

Async broadcast channels for low-latency fan-out

Capable of >1000 orders/sec on a single core

🌐 Simple Frontend (HTML/CSS)

A lightweight dashboard (index.html) is included for visualization.

Features:

Real-time order book (bids/asks)

Trade tape

Live BBO display

Simple order form (market, limit, ioc, fok)

Usage:

Start the backend:

uvicorn app.main:app --reload


Open index.html in your browser.

Set Base URL = http://127.0.0.1:8000
 → click Connect Feeds.

🧩 Requirements
fastapi==0.115.2
uvicorn[standard]
pydantic==2.9.2
orjson==3.10.7
pytest==8.3.3
websockets==12.0

🧱 Folder Structure
crypto-matching-engine/
├── app/

│   └── main.py              # FastAPI server (REST + WS)

├── engine/

│   ├── matching_engine.py   # Matching logic

│   └── order_book.py        # Order book data structure

├── tests/

│   └── test_engine.py       # Unit tests

├── index.html               # Simple frontend UI

└── requirements.txt
