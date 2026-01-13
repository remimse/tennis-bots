"""Booking page interactions for iCondo tennis courts."""

import logging
import random
import asyncio
from dataclasses import dataclass
from datetime import date, time, datetime
from typing import Optional

from playwright.async_api import Page

logger = logging.getLogger(__name__)


@dataclass
class BookingSlot:
    """Represents an available booking slot."""

    court: str
    date: date
    start_time: time
    end_time: time
    available: bool
    element_selector: Optional[str] = None  # Selector to click for booking


class BookingPage:
    """Handle facility booking interactions for tennis courts."""

    # Selectors - these need to be discovered from actual iCondo site
    # Using generic selectors that should work with typical booking systems
    SELECTORS = {
        "facilities_menu": [
            'text=Facilities',
            'text=Booking',
            'a[href*="facilit"]',
            'a[href*="book"]',
            '[class*="facilities"]',
        ],
        "tennis_option": [
            'text=Tennis',
            'text=Tennis Court',
            '[class*="tennis"]',
            'img[alt*="tennis" i]',
        ],
        "date_picker": [
            'input[type="date"]',
            '[class*="date-picker"]',
            '[class*="datepicker"]',
            '[class*="calendar"]',
        ],
        "next_date_button": [
            'button:has-text(">")',
            'button:has-text("Next")',
            '[class*="next"]',
            '[aria-label*="next"]',
        ],
        "time_slots": [
            '[class*="slot"]',
            '[class*="time-slot"]',
            '[class*="booking-slot"]',
            'button[class*="available"]',
            'td[class*="available"]',
        ],
        "available_slot": [
            '[class*="available"]',
            ':not([class*="booked"]):not([class*="disabled"])',
        ],
        "confirm_button": [
            'button:has-text("Confirm")',
            'button:has-text("Book")',
            'button:has-text("Submit")',
            'button[type="submit"]',
        ],
        "success_message": [
            'text=Success',
            'text=Confirmed',
            'text=Booked',
            '[class*="success"]',
        ],
    }

    def __init__(self, page: Page):
        """
        Initialize booking page.

        Args:
            page: Playwright page instance
        """
        self.page = page

    async def _find_element(self, selector_key: str, timeout: int = 10000):
        """Try multiple selectors to find an element."""
        selectors = self.SELECTORS[selector_key]
        timeout_per_selector = max(1000, timeout // len(selectors))

        for selector in selectors:
            try:
                element = self.page.locator(selector).first
                await element.wait_for(timeout=timeout_per_selector, state="visible")
                logger.debug("Found element with selector: %s", selector)
                return element
            except Exception:
                continue

        raise TimeoutError(f"Could not find element for {selector_key}")

    async def _human_delay(self, min_ms: int = 100, max_ms: int = 500) -> None:
        """Add human-like delay between actions."""
        delay = random.randint(min_ms, max_ms) / 1000
        await asyncio.sleep(delay)

    async def navigate_to_tennis(self) -> None:
        """Navigate to tennis court booking section."""
        logger.info("Navigating to tennis court booking")

        # Click on facilities/booking menu
        try:
            facilities = await self._find_element("facilities_menu")
            await facilities.click()
            await self._human_delay()
        except TimeoutError:
            logger.warning("Facilities menu not found, may already be on booking page")

        # Select tennis courts
        tennis = await self._find_element("tennis_option")
        await tennis.click()
        await self._human_delay()
        logger.info("Tennis court section loaded")

    async def select_date(self, target_date: date) -> None:
        """
        Select the target booking date.

        Args:
            target_date: Date to book
        """
        logger.info("Selecting date: %s", target_date)

        # Try to find and interact with date picker
        try:
            date_picker = await self._find_element("date_picker", timeout=5000)

            # Try to set date directly if it's an input
            date_str = target_date.strftime("%Y-%m-%d")
            await date_picker.fill(date_str)
            await self._human_delay()
            return
        except TimeoutError:
            logger.debug("Date picker input not found, trying navigation buttons")

        # Alternative: Navigate using next/prev buttons
        # This is common in calendar-style pickers
        today = date.today()
        days_ahead = (target_date - today).days

        if days_ahead > 0:
            try:
                for _ in range(days_ahead):
                    next_button = await self._find_element("next_date_button", timeout=3000)
                    await next_button.click()
                    await self._human_delay(50, 150)
            except TimeoutError:
                logger.warning("Could not navigate dates, assuming date is already selected")

    async def get_available_slots(self) -> list[BookingSlot]:
        """
        Scrape available booking slots from the page.

        Returns:
            List of available BookingSlot objects
        """
        logger.info("Scanning for available time slots")
        slots = []

        # Wait for slots to load
        await asyncio.sleep(1)

        # Find all slot elements
        try:
            slot_elements = self.page.locator('[class*="slot"], [class*="time"], td')
            count = await slot_elements.count()
            logger.debug("Found %d potential slot elements", count)

            for i in range(count):
                element = slot_elements.nth(i)

                # Check if slot appears available
                class_attr = await element.get_attribute("class") or ""
                text = await element.text_content() or ""

                # Skip if clearly unavailable
                if any(x in class_attr.lower() for x in ["booked", "disabled", "unavailable"]):
                    continue

                # Try to parse time from text
                slot = self._parse_slot_text(text, i)
                if slot and "available" in class_attr.lower():
                    slot.available = True
                    slots.append(slot)

        except Exception as e:
            logger.warning("Error scanning slots: %s", e)

        logger.info("Found %d available slots", len(slots))
        return slots

    def _parse_slot_text(self, text: str, index: int) -> Optional[BookingSlot]:
        """
        Parse slot information from element text.

        Args:
            text: Text content of the slot element
            index: Element index for identification

        Returns:
            BookingSlot if parseable, None otherwise
        """
        import re

        # Try to extract time pattern (e.g., "08:00", "8:00 AM", "08:00 - 09:00")
        time_pattern = r"(\d{1,2}):?(\d{2})?\s*(AM|PM)?"
        matches = re.findall(time_pattern, text, re.IGNORECASE)

        if matches:
            try:
                hour = int(matches[0][0])
                minute = int(matches[0][1]) if matches[0][1] else 0
                am_pm = matches[0][2].upper() if matches[0][2] else None

                if am_pm == "PM" and hour != 12:
                    hour += 12
                elif am_pm == "AM" and hour == 12:
                    hour = 0

                start = time(hour, minute)
                end = time(hour + 1, minute)  # Assume 1-hour slots

                return BookingSlot(
                    court="Tennis Court",  # Default, adjust if court info available
                    date=date.today(),  # Will be set by caller
                    start_time=start,
                    end_time=end,
                    available=False,  # Will be set by caller
                    element_selector=f"[class*='slot']:nth-child({index + 1})",
                )
            except (ValueError, IndexError):
                pass

        return None

    async def book_slot(self, slot: BookingSlot) -> bool:
        """
        Attempt to book a specific slot.

        Args:
            slot: BookingSlot to book

        Returns:
            True if booking successful
        """
        logger.info(
            "Attempting to book: %s at %s on %s",
            slot.court,
            slot.start_time,
            slot.date,
        )

        try:
            # Click on the slot
            if slot.element_selector:
                slot_element = self.page.locator(slot.element_selector)
            else:
                # Try to find by time
                time_text = slot.start_time.strftime("%H:%M")
                slot_element = self.page.locator(f'text={time_text}').first

            await slot_element.click()
            await self._human_delay()

            # Click confirm/book button
            confirm = await self._find_element("confirm_button")
            await confirm.click()

            # Wait for success
            try:
                await self._find_element("success_message", timeout=10000)
                logger.info("Booking confirmed!")
                return True
            except TimeoutError:
                logger.warning("Success message not found, booking may have failed")
                return False

        except Exception as e:
            logger.error("Booking failed: %s", e)
            return False

    async def book_preferred_slot(
        self,
        target_date: date,
        preferred_times: tuple[time, time],
        preferred_courts: list[str],
    ) -> Optional[BookingSlot]:
        """
        Find and book the best available slot based on preferences.

        Args:
            target_date: Date to book
            preferred_times: (start_time, end_time) preference window
            preferred_courts: List of court names in preference order

        Returns:
            Booked slot if successful, None otherwise
        """
        await self.select_date(target_date)
        slots = await self.get_available_slots()

        if not slots:
            logger.warning("No available slots found")
            return None

        # Filter by time preference
        start_pref, end_pref = preferred_times
        in_window = [
            s
            for s in slots
            if s.available and start_pref <= s.start_time <= end_pref
        ]

        if not in_window:
            logger.warning("No slots in preferred time window")
            # Fall back to any available slot
            in_window = [s for s in slots if s.available]

        if not in_window:
            return None

        # Sort by court preference
        court_priority = {c: i for i, c in enumerate(preferred_courts)}
        in_window.sort(key=lambda s: court_priority.get(s.court, 999))

        # Try to book the best slot
        for slot in in_window:
            slot.date = target_date
            if await self.book_slot(slot):
                return slot

        return None
