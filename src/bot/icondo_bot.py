"""Main bot orchestrator for iCondo tennis court booking."""

import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from src.bot.browser import BrowserManager
from src.bot.pages.login_page import LoginPage
from src.bot.pages.booking_page import BookingPage, BookingSlot
from src.config.settings import Settings
from src.notifications.telegram import TelegramNotifier

logger = logging.getLogger(__name__)


class BookingError(Exception):
    """Raised when booking fails."""

    pass


class ICondoBot:
    """Main bot orchestrating the booking process."""

    def __init__(
        self,
        settings: Settings,
        notifier: Optional[TelegramNotifier] = None,
    ):
        """
        Initialize the bot.

        Args:
            settings: Application settings
            notifier: Optional notification service
        """
        self.settings = settings
        self.notifier = notifier
        self.browser_manager = BrowserManager(
            headless=settings.browser.headless,
            slow_mo=settings.browser.slow_mo,
        )
        self.screenshots_dir = Path("screenshots")
        self.screenshots_dir.mkdir(exist_ok=True)

    async def start(self) -> None:
        """Start the bot and browser."""
        await self.browser_manager.start()

    async def stop(self) -> None:
        """Stop the bot and browser."""
        await self.browser_manager.stop()

    async def __aenter__(self) -> "ICondoBot":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(BookingError),
        reraise=True,
    )
    async def attempt_booking(self, target_date: date) -> Optional[BookingSlot]:
        """
        Main booking flow with retry logic.

        Args:
            target_date: Date to book

        Returns:
            BookingSlot if successful, None otherwise

        Raises:
            BookingError: If booking fails after retries
        """
        logger.info("Starting booking attempt for %s", target_date)

        async with self.browser_manager.new_page() as page:
            try:
                # Step 1: Login
                login_page = LoginPage(page)
                await login_page.navigate()

                login_success = await login_page.login(
                    self.settings.icondo_username,
                    self.settings.icondo_password,
                )

                if not login_success:
                    await self._save_screenshot(page, "login_failed")
                    raise BookingError("Login failed")

                # Step 2: Navigate to booking
                booking_page = BookingPage(page)
                await booking_page.navigate_to_tennis()

                # Step 3: Book preferred slot
                prefs = self.settings.booking
                booked_slot = await booking_page.book_preferred_slot(
                    target_date=target_date,
                    preferred_times=(
                        prefs.preferred_times.start_time,
                        prefs.preferred_times.end_time,
                    ),
                    preferred_courts=prefs.preferred_courts,
                )

                if booked_slot:
                    await self._notify_success(booked_slot)
                    logger.info("Successfully booked: %s", booked_slot)
                    return booked_slot
                else:
                    await self._save_screenshot(page, "no_slots")
                    await self._notify_failure("No available slots matching preferences")
                    return None

            except BookingError:
                raise
            except Exception as e:
                await self._save_screenshot(page, "error")
                logger.exception("Booking attempt failed")
                raise BookingError(f"Booking failed: {e}") from e

    async def _save_screenshot(self, page, prefix: str) -> None:
        """Save screenshot for debugging."""
        if self.settings.browser.screenshot_on_error:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = self.screenshots_dir / f"{prefix}_{timestamp}.png"
            await page.screenshot(path=str(path))
            logger.info("Screenshot saved: %s", path)

    async def _notify_success(self, slot: BookingSlot) -> None:
        """Send success notification."""
        if self.notifier:
            message = (
                f"Tennis court booked!\n\n"
                f"Court: {slot.court}\n"
                f"Date: {slot.date}\n"
                f"Time: {slot.start_time.strftime('%H:%M')} - {slot.end_time.strftime('%H:%M')}"
            )
            await self.notifier.send(message)

    async def _notify_failure(self, reason: str) -> None:
        """Send failure notification."""
        if self.notifier:
            message = f"Tennis court booking failed!\n\nReason: {reason}"
            await self.notifier.send(message)

    def should_book_today(self) -> bool:
        """
        Check if booking should be attempted today.

        Booking is attempted if the target date (advance_booking_days from now)
        falls on a preferred day.

        Returns:
            True if should attempt booking
        """
        from datetime import timedelta

        target_date = date.today() + timedelta(
            days=self.settings.booking.advance_booking_days
        )
        target_day = target_date.strftime("%A").lower()

        preferred = [d.value for d in self.settings.booking.preferred_days]
        should_book = target_day in preferred

        logger.info(
            "Target date %s is %s - booking %s",
            target_date,
            target_day,
            "will be attempted" if should_book else "skipped (not preferred day)",
        )

        return should_book

    async def run_scheduled_booking(self) -> Optional[BookingSlot]:
        """
        Run the scheduled booking job.

        This is called by the scheduler at the configured time.

        Returns:
            BookingSlot if successful, None otherwise
        """
        from datetime import timedelta

        if not self.should_book_today():
            return None

        target_date = date.today() + timedelta(
            days=self.settings.booking.advance_booking_days
        )

        try:
            return await self.attempt_booking(target_date)
        except BookingError as e:
            await self._notify_failure(str(e))
            return None
