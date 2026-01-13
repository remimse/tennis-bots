#!/usr/bin/env python3
"""Run a single booking attempt manually."""

import argparse
import asyncio
import logging
import sys
from datetime import date, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.icondo_bot import ICondoBot
from src.config.settings import Settings
from src.notifications.telegram import TelegramNotifier


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run a single tennis court booking attempt"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Target date (YYYY-MM-DD). Defaults to advance_booking_days from today.",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run in headless mode (no browser window)",
    )
    parser.add_argument(
        "--no-notify",
        action="store_true",
        help="Disable notifications",
    )
    return parser.parse_args()


async def run_booking(target_date: date, headless: bool, notify: bool):
    """Run a single booking attempt."""
    logger.info("Loading settings...")

    try:
        settings = Settings.load()
    except Exception as e:
        logger.error("Failed to load settings: %s", e)
        logger.error("Make sure .env file exists with ICONDO_USERNAME and ICONDO_PASSWORD")
        return False

    # Override headless setting
    settings.browser.headless = headless

    # Setup notifier
    notifier = None
    if notify:
        notifier = TelegramNotifier.from_settings(settings)

    logger.info("Target date: %s", target_date)
    logger.info("Headless mode: %s", headless)
    logger.info("Notifications: %s", "enabled" if notifier else "disabled")
    logger.info("Preferred times: %s - %s",
                settings.booking.preferred_times.start_time,
                settings.booking.preferred_times.end_time)
    logger.info("Preferred courts: %s", settings.booking.preferred_courts)

    bot = ICondoBot(settings, notifier)

    async with bot:
        try:
            slot = await bot.attempt_booking(target_date)
            if slot:
                logger.info("SUCCESS! Booked: %s at %s on %s",
                           slot.court, slot.start_time, slot.date)
                return True
            else:
                logger.warning("No slots available or booking failed")
                return False
        except Exception as e:
            logger.error("Booking failed: %s", e)
            return False


def main():
    """Main entry point."""
    args = parse_args()

    # Parse target date
    if args.date:
        try:
            target_date = date.fromisoformat(args.date)
        except ValueError:
            logger.error("Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)
    else:
        # Load settings to get advance_booking_days
        try:
            settings = Settings.load()
            advance_days = settings.booking.advance_booking_days
        except Exception:
            advance_days = 7
        target_date = date.today() + timedelta(days=advance_days)

    success = asyncio.run(run_booking(
        target_date=target_date,
        headless=args.headless,
        notify=not args.no_notify,
    ))

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
