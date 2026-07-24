FROM python:3.11-slim

# Set the working directory
WORKDIR /app

# 1. Install system dependencies
# We add 'gnupg' for the key verification and fonts needed for Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    fonts-liberation \
    xdg-utils \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# 2. Add Google's official GPG key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor > /usr/share/keyrings/google-chrome.gpg

# 3. Set up the Google Chrome repository
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# 4. Install Google Chrome Stable (This will install the latest version, e.g., 142)
RUN apt-get update && apt-get install -y google-chrome-stable

# --- REMOVED MANUAL CHROMEDRIVER INSTALLATION ---
# Selenium will now handle this automatically.

# 5. Copy requirements and install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# 6. Copy the application code
COPY . .

# 7. Environment Variables
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# 8. Expose the port
EXPOSE 8080

# 9. Run the app under a virtual display so Chrome can run HEADFUL (not headless).
# Headful Chrome is far harder for the Etimad WAF (F5 BIG-IP ASM) to detect than
# headless, which it was rejecting - blocking the lookup XHRs and leaving the
# activity filter empty.
# Start Xvfb in the BACKGROUND, then `exec flask` so Flask is the foreground
# process and binds $PORT immediately (Cloud Run health-checks the port). Chrome
# spawned per request inherits DISPLAY=:99. Wrapping flask in xvfb-run instead
# prevented Flask from binding in time and failed the startup probe.
CMD ["/bin/bash", "-c", "Xvfb :99 -screen 0 1920x1080x24 -nolisten tcp & export DISPLAY=:99; exec flask run --host=0.0.0.0 --port=${PORT:-8080}"]