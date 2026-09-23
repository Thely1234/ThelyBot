"""On-chain market data layer.

All quotes come from real smart contracts (Uniswap-V2 style routers) via
eth_call; nothing here is mocked or randomly generated.
"""

from web3 import Web3

from src import settings
from src.logging_setup import setup_logger

logger = setup_logger("Market")


class MarketData:
    def __init__(self, network_name: str, w3: Web3, price_feed) -> None:
        self.network_name = network_name
        self.w3 = w3
        self.price_feed = price_feed
        self.network = settings.NETWORKS[network_name]
        self.dexes = settings.DEXES[network_name]
        self.tokens = settings.TOKENS[network_name]
        self._token_contracts = {}
        self._router_contracts = {}

    def token_contract(self, token: dict):
        address = Web3.to_checksum_address(token["address"])
        if address not in self._token_contracts:
            self._token_contracts[address] = self.w3.eth.contract(
                address=address, abi=settings.ERC20_ABI
            )
        return self._token_contracts[address]

    def router_contract(self, dex_name: str):
        if dex_name not in self._router_contracts:
            address = Web3.to_checksum_address(self.dexes[dex_name]["router"])
            self._router_contracts[dex_name] = self.w3.eth.contract(
                address=address, abi=settings.ROUTER_V2_ABI
            )
        return self._router_contracts[dex_name]

    def token_by_symbol(self, symbol: str) -> dict:
        for token in self.tokens:
            if token["symbol"] == symbol:
                return token
        raise KeyError("Token {} not configured on {}".format(symbol, self.network_name))

    def human_amount(self, token: dict, raw_wei: int) -> float:
        return float(raw_wei) / (10 ** token["decimals"])

    def raw_amount(self, token: dict, human: float) -> int:
        return int(human * (10 ** token["decimals"]))

    def get_native_balance(self, address: str) -> float:
        wei = self.w3.eth.get_balance(Web3.to_checksum_address(address))
        return float(self.w3.from_wei(wei, "ether"))

    def get_token_balances(self, address: str) -> dict:
        checksum = Web3.to_checksum_address(address)
        balances = {}
        for token in self.tokens:
            try:
                raw = self.token_contract(token).functions.balanceOf(checksum).call()
                human = self.human_amount(token, raw)
                if human > 0:
                    balances[token["symbol"]] = human
            except Exception:
                continue
        return balances

    def quote(self, dex_name: str, token_in: dict, token_out: dict, amount_in_wei: int):
        """Return the exact amountOut (wei) the router would give, or None."""
        path = [
            Web3.to_checksum_address(token_in["address"]),
            Web3.to_checksum_address(token_out["address"]),
        ]
        try:
            amounts = self.router_contract(dex_name).functions.getAmountsOut(
                amount_in_wei, path
            ).call()
            if not amounts:
                return None
            return int(amounts[-1])
        except Exception:
            return None

    def find_round_trips(self, held_token: dict, amount_in_wei: int, slippage: float):
        """Compare the same swap path across local DEXs and return round-trip
        candidates. Leg 1 buys token_out on `dex_first`, leg 2 sells it back to
        token_in on `dex_second`. Slippage is applied to both legs."""
        candidates = []
        token_in = held_token
        dex_names = list(self.dexes.keys())

        for token_out in self.tokens:
            if token_out["symbol"] == token_in["symbol"]:
                continue
            for dex_buy in dex_names:
                for dex_sell in dex_names:
                    if dex_buy == dex_sell:
                        continue
                    out1 = self.quote(dex_buy, token_in, token_out, amount_in_wei)
                    if not out1:
                        continue
                    leg1_min = int(out1 * (1.0 - slippage))
                    out2 = self.quote(dex_sell, token_out, token_in, leg1_min)
                    if not out2:
                        continue
                    leg2_min = int(out2 * (1.0 - slippage))
                    net_wei = out2 - amount_in_wei
                    net_human = float(net_wei) / (10 ** token_in["decimals"])
                    price_in = self.price_feed.price(token_in["symbol"])
                    net_usd = net_human * price_in

                    candidates.append(
                        {
                            "network": self.network_name,
                            "token_in": token_in["symbol"],
                            "token_out": token_out["symbol"],
                            "amount_in_wei": amount_in_wei,
                            "amount_in_human": self.human_amount(token_in, amount_in_wei),
                            "dex_buy": dex_buy,
                            "dex_sell": dex_sell,
                            "leg1_out_wei": out1,
                            "leg1_min_wei": leg1_min,
                            "leg2_out_wei": out2,
                            "leg2_min_wei": leg2_min,
                            "net_human": net_human,
                            "net_usd": net_usd,
                        }
                    )
        return candidates