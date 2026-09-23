"""Web3 connection management and nonce tracking.

Only RPC urls whose host is present in settings.ALLOWED_HOSTS are accepted.
A url pointing anywhere else raises RuntimeError before any request is made.
"""

from urllib.parse import urlparse

from web3 import Web3

from src import settings

_RPC_TIMEOUT_SECONDS = 15


def assert_allowed_host(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("https",):
        raise RuntimeError("Only HTTPS RPC urls are allowed: {}".format(url))
    if parsed.hostname not in settings.ALLOWED_HOSTS:
        raise RuntimeError(
            "RPC host '{}' is not in the whitelist. Refusing to connect.".format(
                parsed.hostname
            )
        )
    return parsed.hostname


def get_rpc_url(network_name: str) -> str:
    imports = settings.NETWORKS[network_name]
    url = __import__("os").getenv(imports["rpc_env"], "").strip() or imports["rpc_default"]
    assert_allowed_host(url)
    return url


def get_web3(network_name: str) -> Web3:
    url = get_rpc_url(network_name)
    provider = Web3.HTTPProvider(url, request_kwargs={"timeout": _RPC_TIMEOUT_SECONDS})
    w3 = Web3(provider)
    if not w3.is_connected():
        raise ConnectionError("Cannot reach RPC node for network '{}'".format(network_name))
    network_chain_id = settings.NETWORKS[network_name]["chain_id"]
    if int(w3.eth.chain_id) != network_chain_id:
        raise RuntimeError(
            "RPC returned chain_id {} but expected {} for network '{}'".format(
                w3.eth.chain_id, network_chain_id, network_name
            )
        )
    return w3


class NonceTracker:
    """Single in-process nonce counter per network (sync executor only)."""

    def __init__(self) -> None:
        self._next_nonce = {}

    def _key(self, w3: Web3, address: str, network_name: str) -> str:
        return "{}:{}".format(network_name, address.lower())

    def get_next(self, w3: Web3, address: str, network_name: str) -> int:
        key = self._key(w3, address, network_name)
        remote = int(w3.eth.get_transaction_count(Web3.to_checksum_address(address), "pending"))
        if key not in self._next_nonce or remote > self._next_nonce[key]:
            self._next_nonce[key] = remote
        return self._next_nonce[key]

    def consume(self, w3: Web3, address: str, network_name: str) -> int:
        nonce = self.get_next(w3, address, network_name)
        key = self._key(w3, address, network_name)
        self._next_nonce[key] = nonce + 1
        return nonce

    def reset(self, address: str, network_name: str) -> None:
        key = "{}:{}".format(network_name, address.lower())
        self._next_nonce.pop(key, None)