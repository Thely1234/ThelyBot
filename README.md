# Cross-DEX Arbitrage Bot (Open Python)

A fully open, auditable Python bot that scans live on-chain order-book
liquidity (Uniswap-V2-style DEX routers) for cross-DEX arbitrage
opportunities and, in live mode, executes them with real slippage and gas
protection.

**This is a complete rewrite.** It does not use, import, or execute any of
the old compiled (`.so`) binaries. Every line is plain `.py`.

---

## Security contract (enforced in code)

| Rule | Enforced by |
|---|---|
| No seed phrase / mnemonic is ever requested | The bot only reads the `PRIVATE_KEY` env var; there is no prompt path |
| Private key never leaves the process | Key is used only to sign locally; it is never logged or sent anywhere |
| Only trusted endpoints | `src/settings.py → ALLOWED_HOSTS`; any other RPC/HTTP host aborts startup in `src/connections.py` / `src/pricing.py` |
| HTTPS only | Non-HTTPS URLs are rejected |
| No fixed recipient | Every transaction `to=` is either a public DEX router or the bot's own address |
| Wallet isolation | Run with a **dedicated backup wallet with a tiny balance**. Never the main/cold wallet |
| Dry-run by default | Real transactions require `--live` **and** `DRY_RUN=false` |

---

## Setup

```bash
git clone <your-fork> ZeroWork-Rich
cd ZeroWork-Rich
chmod +x setup.sh
./setup.sh
```

Or manually:

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Configure

Edit `.env`:

```
PRIVATE_KEY=<0x hex of a DEDICATED BACKUP TRADING WALLET>
CHAINS=ethereum,bsc,polygon
DRY_RUN=true
```

> ⚠️ **Wallet isolation policy (required):** create a fresh wallet, fund it
> with a **small amount** you can afford to lose, and a bit of native gas
> (ETH / BNB / POL) on each chain you scan. Keep your main wallet far away
> from this bot. The bot will never move funds to any address but its own.

## Run

```bash
# Analyze only – no transactions are sent:
python3 main.py

# Single-chain dry run:
python3 main.py --chain ethereum

# Real execution (enables swaps/approvals):
python3 main.py --live
```

---

## How the strategy works

For each chain and each token the wallet actually holds:

1. **Real quotes** — for every local DEX pair (e.g. Uniswap V2 vs SushiSwap
   on Ethereum, PancakeSwap vs SushiSwap on BSC, QuickSwap vs SushiSwap on
   Polygon) the bot calls `router.getAmountsOut(...)` on-chain
   (`src/market.py`). No mock data, no random numbers.
2. **Round trip** — buy the pair on the dex that gives you more for your
   base token, sell it back on the dex that pays more, ending in the same
   token.
3. **Slippage protection** — both legs are executed with
   `amountOutMin = quote × (1 − SLIPPAGE_TOLERANCE)`, so the transaction
   reverts rather than fill a bad price.
4. **Gas accounting** — the bot builds the real unsigned transactions,
   calls `eth_estimateGas`, applies the gas multiplier and a per-chain
   `max_gwei` cap, converts the cost to USD with CoinGecko, and rejects the
   trade unless the net profit clears `MIN_PROFIT_USD` and
   `MIN_PROFIT_PERCENT` **after** gas.
5. **Execution** — approvals (only if allowance is insufficient) then the
   two swap legs are signed locally and broadcast sequentially
   (`src/executor.py`).

DEX router addresses are public, well-known contracts (verifiable on
Explorer): Uniswap V2 Router `0x7a250d56…`, SushiSwap `0xd9e1cE17…`,
PancakeSwap `0x10ED43C7…`, QuickSwap `0xa5E0829C…`.

## Known risks (honest disclosure)

- **Non-atomic execution:** the two swap legs are two transactions. If the
  second one reverts you temporarily hold the intermediate token. That is
  why trade sizes are capped and a backup wallet is mandatory.
- **Profitability:** real arbitrage is competed by professionals/MEV bots;
  opportunities may be rare or non-existent. Rely on `MIN_PROFIT_*`
  thresholds so you never chase losses.
- **Private key safety:** a wallet whose private key lives on a server or
  in a file is at risk. Keep balances small, rotate keys, and never reuse
  the key elsewhere.

## Project layout

```
main.py               entry point (env-only key, --live gating)
src/settings.py       networks/DEXs/tokens, whitelist, guardrails
src/connections.py    Web3 providers, host whitelist, nonce tracker
src/pricing.py        CoinGecko price feed (only price API)
src/market.py         on-chain balances + getAmountsOut quotes
src/executor.py       approvals, swaps, gas, signing, broadcast
src/bot.py            scan loop and profit filtering
```

## License & support

This project is provided as-is for educational/audit use. Do not run funds
you cannot afford to lose. Report issues to the repository maintainer.