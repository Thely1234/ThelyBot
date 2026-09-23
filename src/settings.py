"""Central configuration for the arbitrage bot.

Security contracts enforced by this module:
- The PRIVATE KEY is read from the PRIVATE_KEY environment variable only.
  The bot never asks for a seed phrase / mnemonic.
- Every outbound HTTP host must appear in ALLOWED_HOSTS below. A different
  host makes the bot abort before any request is sent.
- No transaction is ever sent to a recipient other than the bot's own
  trading address. The bot only interacts with well-known public DEX
  router contracts (Uniswap-V2 style interfaces).
"""

import os

ALLOWED_HOSTS = {
    "eth.llamarpc.com",
    "ethereum-rpc.publicnode.com",
    "rpc.ankr.com",
    "polygon-rpc.com",
    "polygon-bor-rpc.publicnode.com",
    "bsc-dataseed1.binance.org",
    "bsc-dataseed2.binance.org",
    "bsc-rpc.publicnode.com",
    "arb1.arbitrum.io",
    "arbitrum.llamarpc.com",
    "mainnet.infura.io",
    "polygon-mainnet.infura.io",
    "bsc-mainnet.infura.io",
    "arbitrum-mainnet.infura.io",
    "eth-mainnet.g.alchemy.com",
    "polygon-mainnet.g.alchemy.com",
    "bnb-mainnet.g.alchemy.com",
    "arb-mainnet.g.alchemy.com",
    "api.coingecko.com",
}

NETWORKS = {
    "ethereum": {
        "chain_id": 1,
        "native_symbol": "ETH",
        "coin_gecko_id": "ethereum",
        "rpc_env": "ETHEREUM_RPC",
        "rpc_default": "https://ethereum-rpc.publicnode.com",
        "explorer": "https://etherscan.io/tx/",
        "max_gwei": 150.0,
        "min_gas_balance": 0.01,
    },
    "bsc": {
        "chain_id": 56,
        "native_symbol": "BNB",
        "coin_gecko_id": "binancecoin",
        "rpc_env": "BSC_RPC",
        "rpc_default": "https://bsc-dataseed1.binance.org",
        "explorer": "https://bscscan.com/tx/",
        "max_gwei": 10.0,
        "min_gas_balance": 0.02,
    },
    "polygon": {
        "chain_id": 137,
        "native_symbol": "POL",
        "coin_gecko_id": "matic-network",
        "rpc_env": "POLYGON_RPC",
        "rpc_default": "https://polygon-bor-rpc.publicnode.com",
        "explorer": "https://polygonscan.com/tx/",
        "max_gwei": 200.0,
        "min_gas_balance": 1.0,
    },
}

DEXES = {
    "ethereum": {
        "uniswap_v2": {
            "factory": "0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",
            "router": "0x7a250d5630B4cF539739dF2C5dAcb4c659F2488D",
            "fee": 0.003,
        },
        "sushiswap": {
            "factory": "0xC0AEe478e3658e2610c5F7A4A2E1777cE9e4f2Ac",
            "router": "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F",
            "fee": 0.003,
        },
    },
    "bsc": {
        "pancakeswap": {
            "factory": "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73",
            "router": "0x10ED43C718714eb63d5aA57B78B54704E256024E",
            "fee": 0.0025,
        },
        "sushiswap": {
            "factory": "0xc35DADB65012eC5796536BD9864eD8773aBc74C4",
            "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "fee": 0.003,
        },
    },
    "polygon": {
        "quickswap": {
            "factory": "0x5757371414417b8C6CAad45bAeF941aC7d3Ab32",
            "router": "0xa5E0829CaCEd8fFDD4De3c43696c57F7D7A678ff",
            "fee": 0.003,
        },
        "sushiswap": {
            "factory": "0xc35DADB65012eC5796536BD9864eD8773aBc74C4",
            "router": "0x1b02dA8Cb0d097eB8D57A175b88c7D8b47997506",
            "fee": 0.003,
        },
    },
}

TOKENS = {
    "ethereum": [
        {"symbol": "USDC", "address": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6},
        {"symbol": "DAI", "address": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18},
        {"symbol": "USDT", "address": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6},
        {"symbol": "WETH", "address": "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "decimals": 18},
        {"symbol": "WBTC", "address": "0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599", "decimals": 8},
    ],
    "bsc": [
        {"symbol": "USDT", "address": "0x55d398326f99059fF775485246999027B3197955", "decimals": 18},
        {"symbol": "BUSD", "address": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", "decimals": 18},
        {"symbol": "WBNB", "address": "0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c", "decimals": 18},
        {"symbol": "CAKE", "address": "0x0E09FaBB73Bd3Ade0a17ECC321fD13a19e81cE82", "decimals": 18},
    ],
    "polygon": [
        {"symbol": "USDC", "address": "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", "decimals": 6},
        {"symbol": "DAI", "address": "0x8f3Cf7ad23Cd3CaDbD9735AFf958023239c6A063", "decimals": 18},
        {"symbol": "USDT", "address": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "decimals": 6},
        {"symbol": "WMATIC", "address": "0x0d500B1d8E8eF31E21C99d1Db9A6444d3ADf1270", "decimals": 18},
    ],
}

ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [
            {"name": "_owner", "type": "address"},
            {"name": "_spender", "type": "address"},
        ],
        "name": "allowance",
        "outputs": [{"name": "remaining", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "_spender", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "approve",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]

ROUTER_V2_ABI = [
    {
        "constant": True,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "path", "type": "address[]"},
        ],
        "name": "getAmountsOut",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
    {
        "constant": False,
        "inputs": [
            {"name": "amountIn", "type": "uint256"},
            {"name": "amountOutMin", "type": "uint256"},
            {"name": "path", "type": "address[]"},
            {"name": "to", "type": "address"},
            {"name": "deadline", "type": "uint256"},
        ],
        "name": "swapExactTokensForTokens",
        "outputs": [{"name": "amounts", "type": "uint256[]"}],
        "type": "function",
    },
]

MAX_UINT256 = 2 ** 256 - 1


def get_enabled_chains() -> list:
    raw = os.getenv("CHAINS", "").strip().lower()
    if not raw:
        return list(NETWORKS.keys())
    chains = [c.strip() for c in raw.split(",") if c.strip()]
    unknown = [c for c in chains if c not in NETWORKS]
    if unknown:
        raise ValueError("Unknown chain in CHAINS env: {}".format(",".join(unknown)))
    return chains


def env_float(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def env_int(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def env_bool(name, default):
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


def get_scan_interval() -> int:
    return env_int("SCAN_INTERVAL_SECONDS", 15)


def get_trade_size_usd() -> float:
    return env_float("TRADE_SIZE_USD", 10.0)


def get_max_trade_percent() -> float:
    return env_float("MAX_TRADE_PERCENT_OF_BALANCE", 20.0)


def get_min_profit_usd() -> float:
    return env_float("MIN_PROFIT_USD", 1.0)


def get_min_profit_percent() -> float:
    return env_float("MIN_PROFIT_PERCENT", 0.6)


def get_slippage_tolerance() -> float:
    return env_float("SLIPPAGE_TOLERANCE", 0.01)


def get_min_token_balance_usd() -> float:
    return env_float("MIN_TOKEN_BALANCE_USD", 0.5)


def get_gas_price_multiplier() -> float:
    return env_float("GAS_PRICE_MULTIPLIER", 1.1)


def get_gas_limit_multiplier() -> float:
    return env_float("GAS_LIMIT_MULTIPLIER", 1.2)


def is_dry_run_enabled() -> bool:
    return env_bool("DRY_RUN", True)