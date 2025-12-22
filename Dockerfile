FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps for Playwright Chromium
RUN apt-get update && apt-get install -y \
    wget curl gnupg ca-certificates fonts-liberation \
    libasound2 libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libdrm2 libgbm1 libgtk-3-0 \
    libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamage1 libxrandr2 libxshmfence1 libxkbcommon0 \
    libglib2.0-0 libxfixes3 libxrender1 libxcb1 libxext6 libxinerama1 libxcursor1 libxi6 libxtst6 \
    libpangocairo-1.0-0 libcairo2 libpango-1.0-0 libatspi2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Chromium in the image (critical for Railway)
RUN python -m playwright install chromium

COPY . .

# Fix Windows CRLF (اگر ویندوزی هستی این خیلی مهمه) + اجازه اجرا
RUN sed -i 's/\r$//' /app/start.sh && chmod +x /app/start.sh

EXPOSE 8000

CMD ["/app/start.sh"]
