"""Browser management using Playwright."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from playwright.async_api import Browser, BrowserContext, Page, async_playwright

logger = logging.getLogger(__name__)


class BrowserManager:
    """Manages Playwright browser instances with proper lifecycle management."""

    def __init__(self, headless: bool = True, slow_mo: int = 0):
        """
        Initialize browser manager.

        Args:
            headless: Run browser without visible window
            slow_mo: Slow down actions by this many milliseconds (for debugging)
        """
        self.headless = headless
        self.slow_mo = slow_mo
        self._playwright = None
        self._browser: Optional[Browser] = None

    async def start(self) -> None:
        """Initialize Playwright and launch browser."""
        logger.info("Starting browser (headless=%s, slow_mo=%d)", self.headless, self.slow_mo)
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=self.headless,
            slow_mo=self.slow_mo,
            args=[
                "--disable-gpu",
                "--disable-dev-shm-usage",
                "--no-sandbox",
                "--disable-setuid-sandbox",
            ],
        )
        logger.info("Browser started successfully")

    async def stop(self) -> None:
        """Clean shutdown of browser and Playwright."""
        logger.info("Stopping browser")
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        logger.info("Browser stopped")

    @asynccontextmanager
    async def new_context(
        self,
        storage_state: Optional[str] = None,
        **kwargs,
    ) -> AsyncGenerator[BrowserContext, None]:
        """
        Create an isolated browser context.

        Args:
            storage_state: Path to saved session state (cookies, localStorage)
            **kwargs: Additional context options

        Yields:
            BrowserContext for the session
        """
        if not self._browser:
            raise RuntimeError("Browser not started. Call start() first.")

        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            storage_state=storage_state,
            **kwargs,
        )
        try:
            yield context
        finally:
            await context.close()

    @asynccontextmanager
    async def new_page(
        self,
        storage_state: Optional[str] = None,
    ) -> AsyncGenerator[Page, None]:
        """
        Create a new page in an isolated context.

        This is a convenience method that creates both context and page.

        Args:
            storage_state: Path to saved session state

        Yields:
            Page for interactions
        """
        async with self.new_context(storage_state=storage_state) as context:
            page = await context.new_page()
            yield page

    async def save_session(self, context: BrowserContext, path: str) -> None:
        """
        Save browser session state for reuse.

        Args:
            context: Browser context to save
            path: File path to save state
        """
        await context.storage_state(path=path)
        logger.info("Session saved to %s", path)

    async def __aenter__(self) -> "BrowserManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.stop()
