"""Arbitrage scan loop.

For every enabled chain the bot:
1. connects to the whitelisted RPC node,
2. reads real token/native balances of the trading address,
3. computes real on-chain quotes (getAmountsOut) across local DEXs,
4. proposes round-trip candidates that beat the profit floor,
5. subtracts real estimated gas costs and only then (live mode) sends
   the signed transactions.

The only profit numbers ever presented come from on-chain quotes.
"""

import time

from src import settings
from src.connections import NonceTracker, get_web3
from src.executor import TradeExecutor
from src.logging_setup import setup_logger
from src.market import MarketData

logger = setup_logger("Bot")


class Bot:
    def __init__(self, account, price_feed, chains: list, dry_run: bool) -> None:
        self.account = account
        self.address = account.address
        self.price_feed = price_feed
        self.chains = chains
        self.dry_run = dry_run
        self.nonces = NonceTracker()
        self.scans = 0
        self.opportunities = 0
        self.executed = 0

    def _trade_input_amount(self, market: MarketData, held_token: dict, balance_human: float) -> int:
        price = self.price_feed.price(held_token["symbol"])
        if price <= 0:
            return 0
        trade_size_human = settings.get_trade_size_usd() / price
        cap_human = balance_human * (settings.get_max_trade_percent() / 100.0)
        chosen = min(trade_size_human, cap_human, balance_human)
        if chosen <= 0:
            return 0
        return market.raw_amount(held_token, chosen)

    def _scan_chain(self, network_name: str) -> dict:
        w3 = get_web3(network_name)
        market = MarketData(network_name, w3, self.price_feed)
        native_balance = market.get_native_balance(self.address)
        min_gas = self.network_min_gas(network_name)
        if native_balance < min_gas:
            logger.warning(
                "{}: native balance {:.6f} below minimum {}. Skipping chain.".format(
                    network_name, native_balance, min_gas
                )
            )
            return {"network": network_name, "skipped_native": True}

        balances = market.get_token_balances(self.address)
        held = []
        for symbol, human in balances.items():
            token = market.token_by_symbol(symbol)
            value_usd = self.price_feed.usd_value(symbol, human)
            if value_usd >= settings.get_min_token_balance_usd():
                held.append((token, human, value_usd))

        if not held:
            logger.info("{}: no tradable token balances above threshold".format(network_name))
            return {"network": network_name, "no_balances": True}

        best = None
        for token, balance_human, _value in held:
            amount_in_wei = self._trade_input_amount(market, token, balance_human)
            if amount_in_wei <= 0:
                continue
            candidates = market.find_round_trips(
                token, amount_in_wei, settings.get_slippage_tolerance()
            )
            for cand in candidates:
                net_pct = (cand["net_human"] / cand["amount_in_human"]) * 100.0
                if cand["net_usd"] < settings.get_min_profit_usd():
                    continue
                if net_pct < settings.get_min_profit_percent():
                    continue
                if best is None or cand["net_usd"] > best["net_usd"]:
                    cand["net_percent"] = net_pct
                    best = cand

        if best is None:
            return {"network": network_name, "no_opportunity": True}

        self.opportunities += 1
        executor = TradeExecutor(market, self.account, self.nonces)
        plan = executor.prepare(best, reserve_nonce=False)
        if plan is None:
            logger.warning("{}: plan could not be built".format(network_name))
            return {"network": network_name, "plan_failed": True}

        net_after_gas = best["net_usd"] - plan["gas_cost_usd"]
        logger.info(
            "{}: {}->{} via {}->{} | gross ${:.4f} | gas ${:.4f} | net ${:.4f}".format(
                network_name,
                best["token_in"],
                best["token_out"],
                best["dex_buy"],
                best["dex_sell"],
                best["net_usd"],
                plan["gas_cost_usd"],
                net_after_gas,
            )
        )

        if net_after_gas < settings.get_min_profit_usd():
            logger.info("{}: opportunity rejected after gas costs".format(network_name))
            return {"network": network_name, "rejected_after_gas": True}

        if self.dry_run:
            logger.warning("DRY-RUN: would execute the following plan (no tx sent):")
            for action in plan["actions"]:
                logger.warning(
                    "  - {} to={} gas={} gas_price_wei={}".format(
                        action["type"], action["tx"]["to"], action["tx"].get("gas"),
                        action["tx"].get("gasPrice"),
                    )
                )
            return {
                "network": network_name,
                "dry_run_plan": plan,
                "net_after_gas": net_after_gas,
            }

        live_plan = executor.prepare(best, reserve_nonce=True)
        if live_plan is None:
            self.nonces.reset(self.address, network_name)
            return {"network": network_name, "plan_failed_live": True}

        net_after_gas_live = best["net_usd"] - live_plan["gas_cost_usd"]
        if net_after_gas_live < settings.get_min_profit_usd():
            self.nonces.reset(self.address, network_name)
            logger.info("{}: opportunity slipped below floor during preparation".format(network_name))
            return {"network": network_name, "slipped": True}

        try:
            result = executor.execute(live_plan, dry_run=False)
            self.executed += 1
            return {
                "network": network_name,
                "executed": True,
                "net_after_gas": net_after_gas_live,
                "result": result,
            }
        except Exception as exc:
            self.nonces.reset(self.address, network_name)
            logger.error("{}: execution failed: {}".format(network_name, exc))
            return {"network": network_name, "execution_error": str(exc)}

    def run_once(self) -> dict:
        summary = {"scans": 0, "opportunities": self.opportunities, "executed": self.executed}
        for network_name in self.chains:
            try:
                self.scans += 1
                summary["scans"] += 1
                result = self._scan_chain(network_name)
                status = [k for k in result if k not in ("network", "net_after_gas") and result[k]]
                logger.info("chain {} -> {}".format(network_name, status or "ok"))
            except Exception as exc:
                logger.error("chain {} errored: {}".format(network_name, exc))
        summary["opportunities"] = self.opportunities
        summary["executed"] = self.executed
        return summary

    def run_forever(self, max_scans: int = None) -> None:
        interval = settings.get_scan_interval()
        logger.info(
            "Bot started | chains={} | dry_run={} | address={} | interval={}s".format(
                ",".join(self.chains), self.dry_run, self.address, interval
            )
        )
        scan_count = 0
        while max_scans is None or scan_count < max_scans:
            summary = self.run_once()
            scan_count += 1
            if summary["executed"] > 0:
                logger.warning(
                    "Round {}: executed {} trade(s).".format(scan_count, summary["executed"])
                )
            time.sleep(interval)

    @staticmethod
    def network_min_gas(network_name: str) -> float:
        return settings.NETWORKS[network_name]["min_gas_balance"]