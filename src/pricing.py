"""CoinGecko price feed (the only price API in use).

Host whitelist is enforced: any change to the base url is refused unless the
host is in settings.ALLOWED_HOSTS.
"""

import time
from urllib.parse import urlparse

import requests

from src import settings

_COINGECKO_BASE = "https://api.coingecko.com/api/v3"

SYMBOL_TO_COINGECKO_ID = {
    "ETH": "ethereum",
    "WETH": "ethereum",
    "BNB": "binancecoin",
    "WBNB": "binancecoin",
    "POL": "matic-network",
    "MATIC": "matic-network",
    "WMATIC": "matic-network",
    "USDC": "usd-coin",
    "USDT": "tether",
    "DAI": "dai",
    "WBTC": "wrapped-bitcoin",
    "BUSD": "binance-usd",
    "CAKE": "pancakeswap-token",
}

_CACHE_SECONDS = 120


class PriceFeed:
    def __init__(self) -> None:
        self._cache = {}
        self._cache_time = 0.0

    def _assert_allowed(self, url: str) -> None:
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in settings.ALLOWED_HOSTS:
            raise RuntimeError("Refusing non-whitelisted price host: {}".format(url))

    def refresh(self) -> dict:
        now = time.time()
        if self._cache and (now - self._cache_time) < _CACHE_SECONDS:
            return dict(self._cache)

        ids = ",".join(sorted(set(SYMBOL_TO_COINGECKO_ID.values())))
        url = "{}/simple/price".format(_COINGECKO_BASE)
        self._assert_allowed(url)
        response = requests.get(url, params={"ids": ids, "vs_currencies": "usd"}, timeout=10)
        response.raise_for_status()
        data = response.json()

        prices = {}
        for symbol, coin_id in SYMBOL_TO_COINGECKO_ID.items():
            entry = data.get(coin_id) or {}
            usd = entry.get("usd")
            if isinstance(usd, (int, float)):
                prices[symbol] = float(usd)

        if not prices:
            raise RuntimeError("CoinGecko returned no usable prices")

        self._cache = prices
        self._cache_time = now
        return dict(prices)

    def price(self, symbol: str) -> float:
        return float(self.refresh().get(symbol, 0.0))

    def usd_value(self, symbol: str, amount: float) -> float:
        return amount * self.price(symbol)