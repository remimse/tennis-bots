"""Login page interactions for iCondo."""

import logging
from playwright.async_api import Page

logger = logging.getLogger(__name__)


class LoginPage:
    """Handle iCondo login flow."""

    # iCondo resident portal URL
    URL = "https://resident.icondo.asia"

    # Selectors - these may need adjustment based on actual iCondo site structure
    # Using multiple selector strategies for resilience
    SELECTORS = {
        "username_input": [
            'input[name="username"]',
            'input[type="email"]',
            'input[placeholder*="email" i]',
            'input[placeholder*="username" i]',
        ],
        "password_input": [
            'input[name="password"]',
            'input[type="password"]',
        ],
        "login_button": [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
        ],
        "logged_in_indicator": [
            'text=Dashboard',
            'text=Home',
            'text=Facilities',
            'text=Book',
            '[class*="dashboard"]',
            '[class*="home"]',
        ],
    }

    def __init__(self, page: Page):
        """
        Initialize login page.

        Args:
            page: Playwright page instance
        """
        self.page = page

    async def _find_element(self, selector_key: str, timeout: int = 10000):
        """
        Try multiple selectors to find an element.

        Args:
            selector_key: Key in SELECTORS dict
            timeout: Total timeout in milliseconds

        Returns:
            Element locator if found

        Raises:
            TimeoutError: If no selector matches
        """
        selectors = self.SELECTORS[selector_key]
        timeout_per_selector = timeout // len(selectors)

        for selector in selectors:
            try:
                element = self.page.locator(selector)
                await element.wait_for(timeout=timeout_per_selector, state="visible")
                logger.debug("Found element with selector: %s", selector)
                return element
            except Exception:
                continue

        raise TimeoutError(f"Could not find element for {selector_key}")

    async def navigate(self) -> None:
        """Navigate to the login page."""
        logger.info("Navigating to iCondo login page: %s", self.URL)
        await self.page.goto(self.URL, wait_until="networkidle")
        logger.info("Login page loaded")

    async def login(self, username: str, password: str) -> bool:
        """
        Perform login with username and password.

        Args:
            username: iCondo username/email
            password: iCondo password

        Returns:
            True if login successful
        """
        logger.info("Attempting login for user: %s", username)

        # Fill username
        username_input = await self._find_element("username_input")
        await username_input.fill(username)
        logger.debug("Username entered")

        # Fill password
        password_input = await self._find_element("password_input")
        await password_input.fill(password)
        logger.debug("Password entered")

        # Click login button
        login_button = await self._find_element("login_button")
        await login_button.click()
        logger.debug("Login button clicked")

        # Wait for login to complete
        return await self.wait_for_login_success()

    async def wait_for_login_success(self, timeout: int = 15000) -> bool:
        """
        Wait for successful login indication.

        Args:
            timeout: Maximum wait time in milliseconds

        Returns:
            True if login successful, False otherwise
        """
        logger.info("Waiting for login success...")

        try:
            # Wait for any logged-in indicator
            await self._find_element("logged_in_indicator", timeout=timeout)
            logger.info("Login successful!")
            return True
        except TimeoutError:
            logger.warning("Login may have failed - no success indicator found")
            # Check for error messages
            await self._check_for_errors()
            return False

    async def _check_for_errors(self) -> None:
        """Check and log any login error messages."""
        error_selectors = [
            '[class*="error"]',
            '[class*="alert"]',
            'text=Invalid',
            'text=incorrect',
        ]

        for selector in error_selectors:
            try:
                error = self.page.locator(selector)
                if await error.is_visible():
                    text = await error.text_content()
                    logger.error("Login error detected: %s", text)
                    return
            except Exception:
                continue

    async def is_logged_in(self) -> bool:
        """
        Check if already logged in.

        Returns:
            True if logged in
        """
        try:
            await self._find_element("logged_in_indicator", timeout=3000)
            return True
        except TimeoutError:
            return False
