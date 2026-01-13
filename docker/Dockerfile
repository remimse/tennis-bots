# iCondo Tennis Court Booking Bot
# Based on official Playwright image with all browser dependencies

FROM mcr.microsoft.com/playwright/python:v1.40.0-jammy

# Set working directory
WORKDIR /app

# Create non-root user for security
RUN groupadd -r botuser && useradd -r -g botuser botuser

# Set timezone to Singapore
ENV TZ=Asia/Singapore
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY config/ ./config/
COPY scripts/ ./scripts/

# Create directories for logs and screenshots
RUN mkdir -p /app/logs /app/screenshots /app/storage && \
    chown -R botuser:botuser /app

# Make scripts executable
RUN chmod +x scripts/*.py

# Switch to non-root user
USER botuser

# Environment variables (override via docker-compose or docker run)
ENV PYTHONUNBUFFERED=1
ENV BROWSER_HEADLESS=true

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command - run the bot with scheduler
CMD ["python", "-m", "src.main"]
