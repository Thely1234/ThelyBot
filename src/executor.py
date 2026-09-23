"""Transaction executor.

Builds, signs and broadcasts real transactions through public DEX routers.
Every outgoing transaction targets either a whitelisted public router
contract or the bot's own trading address. No other recipient is possible.

Dry-run mode logs the exact transaction plan without sending anything.
"""

import time

from eth_account import Account
from web3 import Web3

from src import settings
from src.connections import NonceTracker
from src.logging_setup import setup_logger
from src.market import MarketData

logger = setup_logger("Executor")

_MAX_UINT_SQRT = settings.MAX_UINT256


class TradeExecutor:
    def __init__(self, market: MarketData, account, nonce_tracker: NonceTracker) -> None:
        self.market = market
        self.w3 = market.w3
        self.network_name = market.network_name
        self.network = market.network
        self.account = account
        self.address = Web3.to_checksum_address(account.address)
        self.nonces = nonce_tracker

    def _gas_price_wei(self) -> int:
        cap_gwei = self.network["max_gwei"]
        cap_wei = int(cap_gwei * (10 ** 9))
        base = int(self.w3.eth.gas_price)
        price = int(base * settings.get_gas_price_multiplier())
        if price > cap_wei:
            raise RuntimeError(
                "Gas price {} gwei exceeds cap {} gwei (network {}). Trade skipped.".format(
                    price / 1e9, cap_gwei, self.network_name
                )
            )
        return price

    def _token(self, symbol: str) -> dict:
        return self.market.token_by_symbol(symbol)

    def _spendable_wei(self, token: dict, router_address: str) -> int:
        contract = self.market.token_contract(token)
        return int(
            contract.functions.allowance(self.address, router_address).call()
        )

    def _nonce(self, reserve: bool) -> int:
        if reserve:
            return self.nonces.consume(self.w3, self.address, self.network_name)
        return self.nonces.get_next(self.w3, self.address, self.network_name)

    def _approval_action(self, token: dict, router_address: str, reserve: bool):
        needed = _MAX_UINT_SQRT
        current_allowance = self._spendable_wei(token, router_address)
        if current_allowance >= needed:
            return None
        nonce = self._nonce(reserve)
        gas_price = self._gas_price_wei()
        contract = self.market.token_contract(token)
        tx = contract.functions.approve(
            Web3.to_checksum_address(router_address), needed
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "chainId": self.network["chain_id"],
                "gasPrice": gas_price,
            }
        )
        gas_used = int(self.w3.eth.estimate_gas(tx) * settings.get_gas_limit_multiplier())
        return {
            "type": "approve",
            "token": token["symbol"],
            "router": router_address,
            "tx": {**tx, "gas": gas_used},
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
        }

    def _swap_action(self, dex_name: str, token_in: dict, token_out: dict,
                     amount_in_wei: int, min_out_wei: int, reserve: bool):
        nonce = self._nonce(reserve)
        gas_price = self._gas_price_wei()
        router = self.market.router_contract(dex_name)
        path = [
            Web3.to_checksum_address(token_in["address"]),
            Web3.to_checksum_address(token_out["address"]),
        ]
        tx = router.functions.swapExactTokensForTokens(
            amount_in_wei,
            min_out_wei,
            path,
            self.address,
            int(time.time()) + 120,
        ).build_transaction(
            {
                "from": self.address,
                "nonce": nonce,
                "chainId": self.network["chain_id"],
                "gasPrice": gas_price,
            }
        )
        gas_used = int(self.w3.eth.estimate_gas(tx) * settings.get_gas_limit_multiplier())
        return {
            "type": "swap",
            "dex": dex_name,
            "symbol_in": token_in["symbol"],
            "symbol_out": token_out["symbol"],
            "amount_in_wei": amount_in_wei,
            "min_out_wei": min_out_wei,
            "tx": {**tx, "gas": gas_used},
            "gas_used": gas_used,
            "gas_price_wei": gas_price,
        }

    def prepare(self, candidate: dict, reserve_nonce: bool = False):
        """Build the full trade plan (approvals + leg1 + leg2) with real gas
        estimates. Returns None when the plan cannot be built (e.g. revert).

        reserve_nonce=False only peeks at the next nonce without consuming it,
        so failed analysis never corrupts the in-process nonce counter."""
        token_in = self._token(candidate["token_in"])
        token_out = self._token(candidate["token_out"])
        router_buy = self.market.dexes[candidate["dex_buy"]]["router"]
        router_sell = self.market.dexes[candidate["dex_sell"]]["router"]

        actions = []
        approve_buy = self._approval_action(token_in, router_buy, reserve_nonce)
        if approve_buy:
            actions.append(approve_buy)
        approve_sell = self._approval_action(token_out, router_sell, reserve_nonce)
        if approve_sell:
            actions.append(approve_sell)

        leg1 = self._swap_action(
            candidate["dex_buy"], token_in, token_out,
            candidate["amount_in_wei"], candidate["leg1_min_wei"], reserve_nonce,
        )
        actions.append(leg1)

        leg2 = self._swap_action(
            candidate["dex_sell"], token_out, token_in,
            leg1["min_out_wei"], candidate["leg2_min_wei"], reserve_nonce,
        )
        actions.append(leg2)

        total_gas = sum(a["gas_used"] for a in actions)
        total_wei = total_gas * leg1["gas_price_wei"]
        native_symbol = self.network["native_symbol"]
        native_units = float(self.w3.from_wei(total_wei, "ether"))
        gas_cost_usd = native_units * self.market.price_feed.price(native_symbol)

        plan = {
            "network": self.network_name,
            "candidate": candidate,
            "actions": actions,
            "total_gas_used": total_gas,
            "gas_cost_usd": gas_cost_usd,
        }
        return plan

    def execute(self, plan: dict, dry_run: bool = True) -> dict:
        results = []
        for action in plan["actions"]:
            tx = dict(action["tx"])
            if dry_run:
                results.append(
                    {
                        "type": action["type"],
                        "symbol": action.get("symbol_in") or action.get("token"),
                        "mode": "DRY-RUN",
                        "to": tx["to"],
                        "gas": tx.get("gas"),
                        "gas_price_wei": tx.get("gasPrice"),
                    }
                )
                continue
            signed = self.account.sign_transaction(tx)
            tx_hash = self.w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_id = Web3.to_hex(tx_hash)
            results.append(
                {
                    "type": action["type"],
                    "symbol": action.get("symbol_in") or action.get("token"),
                    "mode": "BROADCAST",
                    "tx_hash": tx_id,
                    "explorer": "{}{}".format(self.network["explorer"], tx_id),
                }
            )
            logger.info(
                "{} {} broadcast: {}".format(action["type"], action.get("symbol_in") or action.get("token"), tx_id)
            )
            time.sleep(1.0)
        return {"results": results}