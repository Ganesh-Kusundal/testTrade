import re
import os

with open("/Users/apple/Downloads/testTrade/scalpr/api/main.py", "r") as f:
    content = f.read()

# 1. Add os import
content = content.replace("import asyncio", "import asyncio\nimport os")

# 2. Imports
content = content.replace(
    "from scalpr.oms.paper_oms import PaperOms",
    "from scalpr.brokers.dhan.gateway import DhanGateway\nfrom scalpr.market_data.dhan_feed import DhanMarketFeed"
)

# 3. Setup global instances
old_setup = """# Global Paper OMS
paper_oms = PaperOms(initial_balance=Decimal("1000000.00"))

# Global Strategy Executor
strategy_executor = StrategyExecutor()"""

new_setup = """# Live Dhan Configuration
CLIENT_ID = os.getenv("DHAN_CLIENT_ID", "mock_client")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN", "mock_token")

# Global Broker Gateway
broker_gateway = DhanGateway(client_id=CLIENT_ID, access_token=ACCESS_TOKEN)

# Basic Order Tracker for /api/orders
tracked_orders = []

# Global Market Feed
dhan_feed = DhanMarketFeed(client_id=CLIENT_ID, access_token=ACCESS_TOKEN)

# Global Strategy Executor
strategy_executor = StrategyExecutor()"""
content = content.replace(old_setup, new_setup)

# 4. Strategy initialization
content = content.replace("ScalprAmtStrategy(paper_oms,", "ScalprAmtStrategy(broker_gateway,")

# 5. Add feed callback and simulated tick pumper instead of tick_simulation_loop
old_loop = """async def tick_simulation_loop() -> None:
    \"\"\"Simulates raw market feed ticks and triggers execution logic in background.\"\"\"
    while True:
        try:
            for symbol in CURRENT_PRICES:
                old_price = CURRENT_PRICES[symbol]
                change = Decimal(str(random.uniform(-0.001, 0.001))) * old_price  # noqa: S311
                new_price = round(old_price + change, 2)
                CURRENT_PRICES[symbol] = new_price

                # Update Paper OMS last price
                paper_oms.set_last_price(symbol, new_price)

                # Construct domain Tick object
                dt_now = datetime.now(timezone.utc)
                tick = Tick(
                    symbol=symbol,
                    ltp=new_price,
                    bid=new_price - Decimal("0.05"),
                    ask=new_price + Decimal("0.05"),
                    delta_volume=random.randint(10, 500),  # noqa: S311
                    cumulative_volume=random.randint(1000, 50000),  # noqa: S311
                    exchange_timestamp=dt_now
                )

                # Route to registered strategies
                strategy_executor.on_tick(tick)

                # Stream tick events to subscribers
                quote_data = get_quote_data(symbol)
                await manager.broadcast_to_subscribers(symbol, quote_data)

            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in tick simulation loop")
            await asyncio.sleep(1.0)"""

new_loop = """def feed_on_tick_callback(tick: Tick) -> None:
    # Update latest prices
    CURRENT_PRICES[tick.symbol] = tick.ltp

    # Route to registered strategies
    strategy_executor.on_tick(tick)

    # Broadcast to websocket
    quote_data = get_quote_data(tick.symbol)
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(manager.broadcast_to_subscribers(tick.symbol, quote_data))
    except RuntimeError:
        pass

dhan_feed.on_tick(feed_on_tick_callback)

async def tick_simulation_loop() -> None:
    \"\"\"Pumps raw market ticks into DhanMarketFeed to simulate actual WebSocket data.\"\"\"
    while True:
        try:
            for symbol in CURRENT_PRICES:
                old_price = float(CURRENT_PRICES[symbol])
                change = random.uniform(-0.001, 0.001) * old_price  # noqa: S311
                new_price = round(old_price + change, 2)

                raw_msg = {
                    "symbol": symbol,
                    "ltp": new_price,
                    "bid": new_price - 0.05,
                    "ask": new_price + 0.05,
                    "volume": random.randint(1000, 50000),  # noqa: S311
                    "timestamp": datetime.now(timezone.utc).timestamp()
                }
                
                # Push into the queue (which is processed by _process_queue_loop and invokes feed_on_tick_callback)
                await dhan_feed.put_tick(raw_msg)

            await asyncio.sleep(1.0)
        except asyncio.CancelledError:
            break
        except Exception:
            logger.exception("Error in tick simulation loop")
            await asyncio.sleep(1.0)"""
content = content.replace(old_loop, new_loop)

# 6. Startup event
content = content.replace("task = asyncio.create_task(tick_simulation_loop())", "dhan_feed.connect()\n    task = asyncio.create_task(tick_simulation_loop())")

# 7. Endpoints
old_positions = """def get_positions() -> list[dict[str, Any]]:
    positions = paper_oms.get_positions()"""
new_positions = """def get_positions() -> list[dict[str, Any]]:
    try:
        positions = broker_gateway.get_positions()
    except Exception as exc:
        logger.error(f"Failed to fetch positions: {exc}")
        positions = []"""
content = content.replace(old_positions, new_positions)

old_orders = """def get_orders() -> list[dict[str, Any]]:
    orders = paper_oms.orders_dict.values()"""
new_orders = """def get_orders() -> list[dict[str, Any]]:
    orders = tracked_orders"""
content = content.replace(old_orders, new_orders)

old_portfolio = """def get_portfolio() -> dict[str, Any]:
    return {
        "balance": str(paper_oms.balance),
        "peak_balance": str(paper_oms.peak_balance),
        "daily_pnl": str(paper_oms.daily_pnl),
        "drawdown": str(paper_oms.drawdown),
    }"""
new_portfolio = """def get_portfolio() -> dict[str, Any]:
    try:
        margins = broker_gateway.get_margins()
        avail = margins.get("available_margin", Decimal("1000000.00"))
    except Exception:
        avail = Decimal("1000000.00")
        
    try:
        positions = broker_gateway.get_positions()
        daily_pnl = sum((pos.realised_pnl + pos.unrealised_pnl for pos in positions), Decimal("0"))
    except Exception:
        daily_pnl = Decimal("0")
        
    return {
        "balance": str(avail),
        "peak_balance": str(avail),
        "daily_pnl": str(daily_pnl),
        "drawdown": "0.0",
    }"""
content = content.replace(old_portfolio, new_portfolio)

# 8. Set price on paper OMS in replay websocket
content = content.replace("paper_oms.set_last_price", "# Replay price setting bypassed for live broker: ")

with open("/Users/apple/Downloads/testTrade/scalpr/api/main.py", "w") as f:
    f.write(content)

