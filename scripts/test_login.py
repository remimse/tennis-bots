#!/usr/bin/env python3
"""Test iCondo login credentials."""

import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.bot.browser import BrowserManager
from src.bot.pages.login_page import LoginPage
from src.config.settings import Settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def test_login():
    """Test login to iCondo."""
    logger.info("Loading settings...")

    try:
        settings = Settings.load()
    except Exception as e:
        logger.error("Failed to load settings: %s", e)
        logger.error("Make sure .env file exists with ICONDO_USERNAME and ICONDO_PASSWORD")
        return False

    logger.info("Testing login for user: %s", settings.icondo_username)

    # Use non-headless mode for visual verification
    browser = BrowserManager(headless=False, slow_mo=100)

    async with browser:
        async with browser.new_page() as page:
            login_page = LoginPage(page)

            logger.info("Navigating to iCondo...")
            await login_page.navigate()

            logger.info("Attempting login...")
            success = await login_page.login(
                settings.icondo_username,
                settings.icondo_password,
            )

            if success:
                logger.info("LOGIN SUCCESSFUL!")
                logger.info("Keeping browser open for 10 seconds for verification...")
                await asyncio.sleep(10)
                return True
            else:
                logger.error("LOGIN FAILED!")
                logger.info("Keeping browser open for 30 seconds for debugging...")
                await asyncio.sleep(30)
                return False


if __name__ == "__main__":
    success = asyncio.run(test_login())
    sys.exit(0 if success else 1)
