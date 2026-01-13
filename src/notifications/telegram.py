"""Telegram notification service."""

import logging
from typing import Optional

import aiohttp

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Send notifications via Telegram bot."""

    API_BASE = "https://api.telegram.org/bot"

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token from @BotFather
            chat_id: Chat ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"{self.API_BASE}{bot_token}"

    @classmethod
    def from_settings(cls, settings) -> Optional["TelegramNotifier"]:
        """
        Create notifier from settings if configured.

        Args:
            settings: Application settings

        Returns:
            TelegramNotifier if configured, None otherwise
        """
        if not settings.notifications.enabled:
            return None

        token = settings.notifications.telegram_bot_token
        chat_id = settings.notifications.telegram_chat_id

        if not token or not chat_id:
            logger.warning("Telegram notifications enabled but token/chat_id not set")
            return None

        return cls(bot_token=token, chat_id=chat_id)

    async def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Send a message via Telegram.

        Args:
            message: Message text to send
            parse_mode: Parse mode (HTML or Markdown)

        Returns:
            True if sent successfully
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": message,
                        "parse_mode": parse_mode,
                    },
                ) as response:
                    if response.status == 200:
                        logger.info("Telegram message sent successfully")
                        return True
                    else:
                        error = await response.text()
                        logger.error("Telegram API error: %s", error)
                        return False
        except Exception as e:
            logger.error("Failed to send Telegram message: %s", e)
            return False

    async def test_connection(self) -> bool:
        """
        Test the Telegram connection by sending a test message.

        Returns:
            True if connection successful
        """
        return await self.send("iCondo Tennis Bot connected!")
