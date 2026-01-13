"""Main entry point for the iCondo Tennis Court Booking Bot."""

import asyncio
import logging
import signal
import sys
from datetime import datetime

import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.bot.icondo_bot import ICondoBot
from src.config.settings import Settings
from src.notifications.telegram import TelegramNotifier


def setup_logging(level: str = "INFO") -> None:
    """Configure structured logging."""
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )


logger = logging.getLogger(__name__)


class BotRunner:
    """Manages the bot lifecycle and scheduling."""

    def __init__(self, settings: Settings):
        """
        Initialize the bot runner.

        Args:
            settings: Application settings
        """
        self.settings = settings
        self.scheduler = AsyncIOScheduler(timezone="Asia/Singapore")
        self.notifier = TelegramNotifier.from_settings(settings)
        self.bot: ICondoBot | None = None
        self._shutdown_event = asyncio.Event()

    async def _booking_job(self) -> None:
        """Execute scheduled booking job."""
        logger.info("Running scheduled booking job at %s", datetime.now())

        if not self.bot:
            self.bot = ICondoBot(self.settings, self.notifier)

        async with self.bot:
            await self.bot.run_scheduled_booking()

    def _setup_scheduler(self) -> None:
        """Configure the scheduler with booking job."""
        trigger_time = self.settings.scheduler.trigger_time

        # Schedule daily booking job
        self.scheduler.add_job(
            self._booking_job,
            CronTrigger(
                hour=trigger_time.hour,
                minute=trigger_time.minute,
                second=trigger_time.second,
                timezone="Asia/Singapore",
            ),
            id="daily_booking",
            name="Daily Tennis Court Booking",
            misfire_grace_time=60,
        )

        logger.info(
            "Scheduled booking job at %02d:%02d:%02d Singapore time",
            trigger_time.hour,
            trigger_time.minute,
            trigger_time.second,
        )

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers."""
        loop = asyncio.get_event_loop()

        def signal_handler(sig):
            logger.info("Received signal %s, shutting down...", sig)
            self._shutdown_event.set()

        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

    async def run(self) -> None:
        """Run the bot with scheduler."""
        logger.info("Starting iCondo Tennis Bot")
        logger.info("Configuration loaded:")
        logger.info("  - Preferred days: %s", [d.value for d in self.settings.booking.preferred_days])
        logger.info(
            "  - Preferred times: %s - %s",
            self.settings.booking.preferred_times.start_time,
            self.settings.booking.preferred_times.end_time,
        )
        logger.info("  - Advance booking days: %d", self.settings.booking.advance_booking_days)
        logger.info("  - Browser headless: %s", self.settings.browser.headless)

        self._setup_scheduler()
        self._setup_signal_handlers()

        self.scheduler.start()
        logger.info("Scheduler started, waiting for scheduled jobs...")

        # Send startup notification
        if self.notifier:
            await self.notifier.send("iCondo Tennis Bot started and waiting for scheduled booking time.")

        # Wait for shutdown signal
        await self._shutdown_event.wait()

        # Cleanup
        self.scheduler.shutdown()
        if self.bot:
            await self.bot.stop()

        logger.info("Bot shutdown complete")


async def main() -> None:
    """Main entry point."""
    setup_logging()

    try:
        settings = Settings.load()
    except Exception as e:
        logger.error("Failed to load settings: %s", e)
        logger.error("Make sure .env file exists with ICONDO_USERNAME and ICONDO_PASSWORD")
        sys.exit(1)

    runner = BotRunner(settings)
    await runner.run()


if __name__ == "__main__":
    asyncio.run(main())
