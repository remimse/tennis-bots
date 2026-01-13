"""Configuration settings using Pydantic."""

from datetime import time
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import Field
from pydantic_settings import BaseSettings


class DayOfWeek(str, Enum):
    """Days of the week for booking preferences."""

    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class TimeSlotPreference(BaseSettings):
    """Preferred time window for bookings."""

    start_time: time = Field(
        default=time(8, 0), description="Earliest acceptable start time"
    )
    end_time: time = Field(
        default=time(11, 0), description="Latest acceptable end time"
    )


class BookingPreferences(BaseSettings):
    """Booking preferences configuration."""

    preferred_days: list[DayOfWeek] = Field(
        default=[DayOfWeek.SATURDAY, DayOfWeek.SUNDAY],
        description="Days to attempt booking",
    )
    preferred_times: TimeSlotPreference = Field(default_factory=TimeSlotPreference)
    preferred_courts: list[str] = Field(
        default=["Tennis Court 1", "Tennis Court 2"],
        description="Court preference order (first = highest priority)",
    )
    booking_duration_hours: int = Field(default=1, ge=1, le=2)
    advance_booking_days: int = Field(
        default=7, description="How many days in advance slots open"
    )


class SchedulerConfig(BaseSettings):
    """Scheduler configuration."""

    trigger_time: time = Field(
        default=time(0, 0, 5),
        description="Time to trigger booking attempt (just after midnight)",
    )
    retry_count: int = Field(default=3, ge=1)
    retry_delay_seconds: int = Field(default=5, ge=1)


class NotificationConfig(BaseSettings):
    """Notification settings."""

    enabled: bool = True
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")


class BrowserConfig(BaseSettings):
    """Browser settings."""

    headless: bool = Field(default=True, alias="BROWSER_HEADLESS")
    slow_mo: int = Field(default=0, description="Slow down actions in milliseconds")
    screenshot_on_error: bool = True


class Settings(BaseSettings):
    """Main settings class combining all configuration."""

    # Credentials from environment
    icondo_username: str = Field(..., alias="ICONDO_USERNAME")
    icondo_password: str = Field(..., alias="ICONDO_PASSWORD")

    # Sub-configurations (loaded from YAML or defaults)
    booking: BookingPreferences = Field(default_factory=BookingPreferences)
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    notifications: NotificationConfig = Field(default_factory=NotificationConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True

    @classmethod
    def load(cls, config_path: Optional[Path] = None) -> "Settings":
        """Load settings from environment and optional YAML config file."""
        yaml_config = {}

        # Try to load YAML config if path provided or default exists
        if config_path is None:
            config_path = Path("config/config.yaml")

        if config_path.exists():
            with open(config_path) as f:
                yaml_config = yaml.safe_load(f) or {}

        # Parse nested configurations from YAML
        booking_config = yaml_config.get("booking", {})
        scheduler_config = yaml_config.get("scheduler", {})
        notification_config = yaml_config.get("notifications", {})
        browser_config = yaml_config.get("browser", {})

        # Convert time strings to time objects
        if "preferred_times" in booking_config:
            times = booking_config["preferred_times"]
            if isinstance(times.get("start_time"), str):
                h, m = map(int, times["start_time"].split(":"))
                times["start_time"] = time(h, m)
            if isinstance(times.get("end_time"), str):
                h, m = map(int, times["end_time"].split(":"))
                times["end_time"] = time(h, m)

        if "trigger_time" in scheduler_config:
            if isinstance(scheduler_config["trigger_time"], str):
                parts = scheduler_config["trigger_time"].split(":")
                h, m = int(parts[0]), int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                scheduler_config["trigger_time"] = time(h, m, s)

        return cls(
            booking=BookingPreferences(**booking_config) if booking_config else BookingPreferences(),
            scheduler=SchedulerConfig(**scheduler_config) if scheduler_config else SchedulerConfig(),
            notifications=NotificationConfig(**notification_config) if notification_config else NotificationConfig(),
            browser=BrowserConfig(**browser_config) if browser_config else BrowserConfig(),
        )
