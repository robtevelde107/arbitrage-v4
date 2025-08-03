"""
Arbitrage scanning and execution service.

This module defines the ArbitrageService class responsible for monitoring
multiple cryptocurrency exchanges for price discrepancies and optionally
executing trades. It relies on the ccxt library for exchange APIs and
provides asynchronous methods for continuous operation. The service is
designed to be started and stopped dynamically per user and mode (sandbox
or live). In sandbox mode the system simulates trades by logging them
without hitting the exchanges, whereas in live mode it uses the provided
API keys to place real orders.

Note: Real trading involves significant risk. The implementation here
demonstrates the architecture and does not guarantee profitability or
protection against losses. Make sure to thoroughly test your strategy
before enabling live trading.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import ccxt.async_support as ccxt  # type: ignore

from .. import models, crud, schemas
from ..database import async_session_factory


logger = logging.getLogger(__name__)


class ArbitrageService:
    """Manage arbitrage bots for multiple users.

    Instances of this class maintain tasks running concurrently for each
    user and configuration. Each task periodically fetches ticker prices
    from the configured exchanges and evaluates potential arbitrage
    opportunities. When an opportunity exceeds the configured slippage
    tolerance it will execute a simulated or real trade depending on the
    mode.
    """

    def __init__(self):
        # Mapping of (user_id, config_id) to asyncio.Task
        self._tasks: Dict[Tuple[int, int], asyncio.Task] = {}
        # Subscribers for websocket broadcasts. Keys are user_id, values are
        # sets of WebSocket objects to send updates to.
        self._subscribers: Dict[int, set] = {}

    async def subscribe(self, user_id: int, websocket) -> None:
        """Register a websocket to receive updates for a user."""
        self._subscribers.setdefault(user_id, set()).add(websocket)

    async def unsubscribe(self, user_id: int, websocket) -> None:
        """Remove a websocket from receiving updates."""
        if user_id in self._subscribers and websocket in self._subscribers[user_id]:
            self._subscribers[user_id].remove(websocket)

    async def broadcast(self, user_id: int, message: dict) -> None:
        """Send a JSON message to all subscribed websockets for a user."""
        if user_id not in self._subscribers:
            return
        to_remove = []
        for ws in list(self._subscribers[user_id]):
            try:
                await ws.send_json(message)
            except Exception:
                to_remove.append(ws)
        for ws in to_remove:
            self._subscribers[user_id].discard(ws)

    async def start_bot(self, user: models.User, config: models.BotConfig) -> None:
        """Start an arbitrage bot for the given user and configuration."""
        key = (user.id, config.id)
        if key in self._tasks:
            logger.warning("Bot already running for user=%s config=%s", user.id, config.id)
            return
        task = asyncio.create_task(self._run_bot(user, config))
        self._tasks[key] = task

    async def stop_bot(self, user_id: int, config_id: int) -> None:
        """Stop an arbitrage bot if it is running."""
        key = (user_id, config_id)
        task = self._tasks.get(key)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            del self._tasks[key]

    async def _run_bot(self, user: models.User, config: models.BotConfig) -> None:
        """Internal coroutine that performs continuous scanning and trading."""
        exchanges = [ek for ek in user.exchange_keys if ek.is_enabled]
        if not exchanges:
            logger.warning("No enabled exchanges for user=%s", user.id)
            return
        # Initialise exchange clients
        clients: Dict[str, ccxt.Exchange] = {}
        for ek in exchanges:
            try:
                cls = getattr(ccxt, ek.exchange)
            except AttributeError:
                logger.error("Exchange %s not supported by ccxt", ek.exchange)
                continue
            client = cls({
                'apiKey': ek.api_key,
                'secret': ek.api_secret,
                'password': ek.api_password,
                'enableRateLimit': True,
            })
            clients[ek.exchange] = client
        if not clients:
            logger.warning("No valid clients initialised for user=%s", user.id)
            return
        coins = [c.strip().upper() for c in config.coins.split(',') if c.strip()]
        try:
            while True:
                await self._scan_and_trade(user, config, clients, coins)
                await asyncio.sleep(5)  # delay between scans
        except asyncio.CancelledError:
            logger.info("Arbitrage bot cancelled for user=%s config=%s", user.id, config.id)
        finally:
            # Cleanup clients
            for client in clients.values():
                await client.close()

    async def _scan_and_trade(
        self,
        user: models.User,
        config: models.BotConfig,
        clients: Dict[str, ccxt.Exchange],
        coins: List[str],
    ) -> None:
        """Scan the markets for arbitrage opportunities and perform trades."""
        # For each coin, fetch tickers concurrently
        tasks = {
            coin: [client.fetch_ticker(f"{coin}/USDT") for client in clients.values()] for coin in coins
        }
        results: Dict[str, List[Optional[dict]]] = {}
        for coin, futures in tasks.items():
            tickers: List[Optional[dict]] = []
            for fut in futures:
                try:
                    ticker = await fut
                except Exception as exc:
                    logger.error("Error fetching ticker: %s", exc)
                    ticker = None
                tickers.append(ticker)
            results[coin] = tickers

        # Evaluate arbitrage
        for coin, tickers in results.items():
            best_buy = None
            best_sell = None
            exchange_names = list(clients.keys())
            for i, ticker in enumerate(tickers):
                if not ticker:
                    continue
                price = ticker['ask'] if ticker['ask'] else ticker['last']
                if price is None:
                    continue
                name = exchange_names[i]
                if best_buy is None or price < best_buy[1]:
                    best_buy = (name, price)
                if best_sell is None or price > best_sell[1]:
                    best_sell = (name, price)
            if best_buy and best_sell and best_sell[1] > 0:
                spread = (best_sell[1] - best_buy[1]) / best_sell[1]
                message = {
                    'type': 'ticker',
                    'coin': coin,
                    'best_buy': {'exchange': best_buy[0], 'price': best_buy[1]},
                    'best_sell': {'exchange': best_sell[0], 'price': best_sell[1]},
                    'spread_percent': spread,
                }
                # Broadcast update
                await self.broadcast(user.id, message)
                # If spread greater than slippage tolerance => trade
                if spread > config.slippage_tolerance:
                    # Determine trade size
                    trade_size_usd = min(config.max_trade_size, config.budget)
                    amount = trade_size_usd / best_buy[1] if best_buy[1] > 0 else 0
                    # Simulate or execute trade
                    profit = (best_sell[1] - best_buy[1]) * amount if amount else 0
                    status = 'executed'
                    err = None
                    if config.mode == 'live':
                        # Execute real trades using ccxt create_order
                        try:
                            buy_client = clients[best_buy[0]]
                            sell_client = clients[best_sell[0]]
                            symbol = f"{coin}/USDT"
                            # Market buy
                            await buy_client.create_market_buy_order(symbol, amount)
                            # Market sell
                            await sell_client.create_market_sell_order(symbol, amount)
                        except Exception as e:
                            status = 'error'
                            err = str(e)
                            logger.error("Error executing live trade: %s", e)
                    # Log the trade
                    async with async_session_factory() as db:
                        await crud.create_trade_log(
                            db,
                            user_id=user.id,
                            coin=coin,
                            buy_exchange=best_buy[0],
                            sell_exchange=best_sell[0],
                            price_buy=best_buy[1],
                            price_sell=best_sell[1],
                            amount=amount,
                            profit=profit,
                            mode=config.mode,
                            status=status,
                            error_message=err,
                        )
                    # Update budget
                    if config.mode == 'live' and status == 'executed':
                        config.budget -= trade_size_usd
                    # Broadcast trade
                    trade_msg = {
                        'type': 'trade',
                        'coin': coin,
                        'buy': best_buy,
                        'sell': best_sell,
                        'amount': amount,
                        'profit': profit,
                        'mode': config.mode,
                        'status': status,
                        'error': err,
                    }
                    await self.broadcast(user.id, trade_msg)
