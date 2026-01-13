# iCondo Tennis Court Booking Bot

Automated tennis court booking for iCondo condominiums in Singapore.

## Features

- Automatic booking at scheduled times (when new slots open)
- Configurable preferences (days, times, courts)
- Telegram notifications for booking success/failure
- Docker support for easy deployment
- Retry logic with error screenshots for debugging

## Prerequisites

- Docker and Docker Compose
- iCondo account credentials
- (Optional) Telegram bot for notifications

## Quick Start

### 1. Clone and Configure

```bash
cd tennis-bots

# Copy example files
cp .env.example .env
cp config/config.example.yaml config/config.yaml
```

### 2. Set Your Credentials

Edit `.env` with your iCondo credentials:

```bash
ICONDO_USERNAME=your_email@example.com
ICONDO_PASSWORD=your_password

# Optional: Telegram notifications
TELEGRAM_BOT_TOKEN=123456:ABC...
TELEGRAM_CHAT_ID=987654321
```

### 3. Configure Booking Preferences

Edit `config/config.yaml`:

```yaml
booking:
  preferred_days:
    - saturday
    - sunday
  preferred_times:
    start_time: "08:00"
    end_time: "11:00"
  preferred_courts:
    - "Tennis Court 1"
    - "Tennis Court 2"
  advance_booking_days: 7

scheduler:
  trigger_time: "00:00:05"  # Just after midnight
```

### 4. Run with Docker

```bash
# Build and start
cd docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

## Manual Testing

### Test Login (without Docker)

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Test login (opens browser window)
python scripts/test_login.py
```

### Run Single Booking Attempt

```bash
# With browser window (for debugging)
python scripts/run_once.py

# Headless mode
python scripts/run_once.py --headless

# Specific date
python scripts/run_once.py --date 2024-01-20
```

### Run with Docker (single attempt)

```bash
cd docker
docker-compose --profile manual run --rm tennis-bot-once
```

## Configuration Reference

### Environment Variables (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `ICONDO_USERNAME` | Yes | iCondo login email |
| `ICONDO_PASSWORD` | Yes | iCondo password |
| `TELEGRAM_BOT_TOKEN` | No | Telegram bot token for notifications |
| `TELEGRAM_CHAT_ID` | No | Telegram chat ID for notifications |
| `BROWSER_HEADLESS` | No | Run browser headlessly (default: true) |

### Config File (config/config.yaml)

| Setting | Description |
|---------|-------------|
| `booking.preferred_days` | Days to attempt booking (monday-sunday) |
| `booking.preferred_times.start_time` | Earliest acceptable slot time |
| `booking.preferred_times.end_time` | Latest acceptable slot time |
| `booking.preferred_courts` | Court preference order |
| `booking.advance_booking_days` | Days ahead when slots open (usually 7) |
| `scheduler.trigger_time` | When to run booking (Singapore time) |
| `scheduler.retry_count` | Number of retry attempts |

## Setting Up Telegram Notifications

1. Message [@BotFather](https://t.me/botfather) on Telegram
2. Create a new bot with `/newbot`
3. Copy the bot token to `TELEGRAM_BOT_TOKEN`
4. Message [@userinfobot](https://t.me/userinfobot) to get your chat ID
5. Copy your chat ID to `TELEGRAM_CHAT_ID`
6. Start a chat with your bot

## Troubleshooting

### Check Logs

```bash
# Docker logs
docker-compose logs -f tennis-bot

# Local logs
cat logs/bot.log
```

### Check Screenshots

Error screenshots are saved to `screenshots/` directory.

### Common Issues

**Login fails:**
- Verify credentials in `.env`
- Run `python scripts/test_login.py` to see the browser
- Check if iCondo site structure changed

**No slots found:**
- Check preferred time window in config
- Verify court names match exactly
- Check screenshots for page state

**Container crashes:**
- Ensure `shm_size: '2gb'` is set in docker-compose
- Check Docker has enough memory allocated

## Project Structure

```
tennis-bots/
├── docker/
│   ├── Dockerfile
│   └── docker-compose.yml
├── src/
│   ├── main.py              # Entry point with scheduler
│   ├── bot/
│   │   ├── icondo_bot.py    # Main orchestrator
│   │   ├── browser.py       # Browser management
│   │   └── pages/           # Page objects
│   ├── config/
│   │   └── settings.py      # Configuration
│   └── notifications/
│       └── telegram.py      # Telegram notifications
├── config/
│   └── config.example.yaml
├── scripts/
│   ├── test_login.py        # Test credentials
│   └── run_once.py          # Manual booking
└── README.md
```

## Customization

### Adjusting Selectors

If iCondo updates their website, you may need to update the CSS selectors in:
- `src/bot/pages/login_page.py`
- `src/bot/pages/booking_page.py`

Use Playwright's codegen tool to discover selectors:

```bash
playwright codegen https://resident.icondo.asia
```

## Disclaimer

This bot is for personal use. Use responsibly and in accordance with iCondo's terms of service.
