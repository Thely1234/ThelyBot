#!/usr/bin/env python3
"""Cross-DEX Arbitrage Bot (fully open Python).

Security contract:
- No seed phrase / mnemonic is ever requested. The private key is read from
  the PRIVATE_KEY environment variable only.
- Run this bot with a dedicated backup wallet holding a small amount only.
- By default the bot runs in DRY-RUN and does not send any transaction.
  Pass --live to allow real transactions.

Usage:
    PRIVATE_KEY=0x... python3 main.py            # dry run
    PRIVATE_KEY=0x... python3 main.py --live     # real execution
"""

import argparse
import os
import sys

import colorama
from colorama import Fore, Style
from dotenv import load_dotenv
from eth_account import Account

from src import settings
from src.bot import Bot
from src.logging_setup import setup_logger
from src.pricing import PriceFeed

colorama.init(autoreset=True)
load_dotenv()

logger = setup_logger("Main", level=os.getenv("LOG_LEVEL", "INFO"))


def get_private_key() -> str:
    key = os.getenv("PRIVATE_KEY", "").strip()
    if not key:
        print(
            Fore.RED
            + "PRIVATE_KEY environment variable is not set.\n"
            + "Export your trading-wallet private key (0x...) before starting:\n"
            + "  export PRIVATE_KEY=0x...   (Linux/macOS)\n"
            + "  set PRIVATE_KEY=0x...     (Windows CMD)\n"
            + "The bot never asks for a seed phrase."
        )
        sys.exit(1)
    if len(key.replace("0x", "")) != 64:
        print(Fore.RED + "PRIVATE_KEY must be a 64-character hex private key (with or without 0x).")
        sys.exit(1)
    return key


def purge_env_key() -> None:
    os.environ.pop("PRIVATE_KEY", None)


def main() -> None:
    parser = argparse.ArgumentParser(description="Cross-DEX Arbitrage Bot (open Python)")
    parser.add_argument(
        "--chain",
        action="append",
        default=None,
        help="Chain(s) to scan (ethereum, bsc, polygon). Repeatable; default all.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Allow real transactions. Omit for DRY-RUN analysis only.",
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=None,
        help="Number of scan rounds before exiting (default: run indefinitely).",
    )
    parser.add_argument(
        "--log-level",
        default=None,
        help="Override LOG_LEVEL (DEBUG/INFO/WARNING/ERROR).",
    )
    args = parser.parse_args()

    if args.log_level:
        global logger
        logger = setup_logger("Main", level=args.log_level.upper())

    key = get_private_key()
    account = Account.from_key(key)
    addr = account.address
    purge_env_key()

    chains = args.chain or settings.get_enabled_chains()
    if args.live and settings.is_dry_run_enabled():
        override = os.environ.get("DRY_RUN", "true").lower()
        if override in ("1", "true", "yes", "on"):
            print(
                Fore.RED
                + "Live mode requested but DRY_RUN=true in .env. "
                + "Set DRY_RUN=false or remove it to trade live."
            )
            sys.exit(1)

    dry_run = not args.live

    print(Fore.CYAN + "=" * 66)
    print(Fore.YELLOW + Style.BRIGHT + "  CROSS-DEX ARBITRAGE BOT — open Python build")
    print(Fore.CYAN + "=" * 66)
    print(Fore.WHITE + f"  Trading address : {addr}")
    print(Fore.WHITE + f"  Chains          : {', '.join(chains)}")
    print(Fore.GREEN if dry_run else Fore.RED +
          f"  Mode            : {'DRY-RUN (no transactions sent)' if dry_run else 'LIVE (real transactions)'}")
    print(Fore.CYAN + "=" * 66)
    print(Fore.YELLOW + Style.BRIGHT + "  WALLET ISOLATION NOTICE")
    print(Fore.WHITE + "  This bot must run with a dedicated backup wallet that holds")
    print(Fore.WHITE + "  only a small amount you can afford to lose. NEVER use your main,")
    print(Fore.WHITE + "  cold, or savings wallet. Keep native gas tokens on the same chain.")
    print(Fore.CYAN + "=" * 66)

    price_feed = PriceFeed()
    bot = Bot(account, price_feed, chains, dry_run=dry_run)

    try:
        bot.run_forever(max_scans=args.iterations)
    except KeyboardInterrupt:
        logger.info("Stopped by user.")
    finally:
        purge_env_key()

    logger.info(
        "Session done | scans={} | opportunities={} | executed={}".format(
            bot.scans, bot.opportunities, bot.executed
        )
    )


if __name__ == "__main__":
    main()