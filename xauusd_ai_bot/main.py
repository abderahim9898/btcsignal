import sys
import argparse
import signal
import time
from typing import Optional
from config import config
from logger import logger
from analyzer import MarketAnalyzer
from scheduler import MarketScheduler
from biquote_client import BiquoteClient
from database import DatabaseManager


def print_startup_banner(biquote_status: str, gemini_status: str, telegram_status: str):
    """Displays the standardized application startup banner."""
    banner = f"""
========================================
XAUUSD AI TRADING ANALYSIS BOT
========================================

Market:
{config.symbol}

Data Provider:
BiQuote.io ({config.biquote_base_url})

Timeframe:
{config.timeframe}

Timezone:
{config.timezone}

Schedule:
{config.work_start_hour}:00 - {config.work_end_hour}:00

Candle Count:
{config.candle_count}

BiQuote API:
{biquote_status}

Gemini AI:
{gemini_status}

Telegram:
{telegram_status}

Database:
READY ({config.db_path})

========================================
"""
    print(banner)


def perform_startup_validation() -> tuple[str, str, str]:
    """Validates connectivity to BiQuote, Gemini configuration, and Telegram configuration."""
    logger.info("Performing startup system health checks...")

    # 1. BiQuote Health Check
    client = BiquoteClient()
    quote = client.get_quote()
    biquote_status = "READY" if quote and quote.mid > 0 else "WARNING (Quote unreachable or stale)"

    # 2. Gemini Health Check
    gemini_status = "READY" if config.gemini_api_key else "NOT CONFIGURED (Check GEMINI_API_KEY in .env)"

    # 3. Telegram Health Check
    telegram_status = "READY" if config.telegram_bot_token and config.telegram_chat_id else "NOT CONFIGURED (Check Telegram tokens in .env)"

    return biquote_status, gemini_status, telegram_status


def main():
    parser = argparse.ArgumentParser(description="XAUUSD AI Trading Analysis Bot")
    parser.add_argument("--once", action="store_true", help="Run a single analysis cycle and exit.")
    parser.add_argument("--ignore-schedule", action="store_true", help="Ignore working hours schedule and run immediately.")
    parser.add_argument("--ignore-stale", action="store_true", help="Ignore quote staleness check (useful outside market hours).")
    parser.add_argument("--force", action="store_true", help="Bypass deduplication check and force re-analysis.")
    parser.add_argument("--only-signals", action="store_true", help="Only dispatch Telegram notification when active LONG/SHORT signal occurs.")
    args = parser.parse_args()

    logger.info("BOT STARTED")

    # Perform DB Init
    db_mgr = DatabaseManager()

    # Startup Health Checks & Banner
    bq_status, gm_status, tg_status = perform_startup_validation()
    print_startup_banner(bq_status, gm_status, tg_status)

    analyzer = MarketAnalyzer(db_mgr=db_mgr)
    scheduler = MarketScheduler()

    # Setup Graceful Shutdown Handler
    shutdown_requested = False

    def signal_handler(sig, frame):
        nonlocal shutdown_requested
        logger.info("\nShutdown signal received. Stopping bot gracefully...")
        shutdown_requested = True
        logger.info("BOT STOPPED")
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Handle --once flag
    if args.once:
        logger.info("Running single analysis cycle (--once mode)...")
        analyzer.run_analysis_cycle(ignore_stale=args.ignore_stale, force=args.force, only_signals=args.only_signals)
        logger.info("Single cycle completed. Exiting.")
        return

    # Continuous Loop
    logger.info("Waiting for next scheduled analysis...")
    while not shutdown_requested:
        try:
            local_now = scheduler.get_current_local_time()
            within_hours = scheduler.is_within_working_hours(local_now)

            if within_hours or args.ignore_schedule:
                logger.info(f"[{local_now.strftime('%H:%M:%S')}] Triggering analysis cycle...")
                analyzer.run_analysis_cycle(ignore_stale=args.ignore_stale, only_signals=args.only_signals)
            else:
                logger.info(f"Current local time ({local_now.strftime('%H:%M:%S')}) is outside operating schedule ({config.work_start_hour}:00 - {config.work_end_hour}:00). Sleeping.")

            # Wait for next 5-minute tick
            scheduler.wait_until_next_tick()

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt received. Stopping bot.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            logger.info("Retrying after 30 seconds...")
            time.sleep(30)

    logger.info("BOT STOPPED")


if __name__ == "__main__":
    main()
