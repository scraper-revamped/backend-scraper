# FROM python:3.11

# WORKDIR /app

# # Install system dependencies
# RUN apt-get update && apt-get install -y \
#     wget \
#     unzip \
#     jq \
#     libnss3 \
#     libxss1 \
#     libappindicator3-1 \
#     libatk-bridge2.0-0 \
#     libgtk-3-0 \
#     libgbm-dev \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Add Google's official GPG key for Chrome installation
# RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -

# # Set up the Google Chrome repository
# RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# # Install Google Chrome
# RUN apt-get update && apt-get install -y google-chrome-stable

# # Install ChromeDriver (version matching the installed Chrome)
# RUN wget -q --continue -P /tmp "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.92/linux64/chromedriver-linux64.zip" && \
#     unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
#     mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
#     rm -rf /usr/local/bin/chromedriver-linux64 && \
#     rm /tmp/chromedriver-linux64.zip && \
#     chmod +x /usr/local/bin/chromedriver

# # Copy the requirements.txt and install Python dependencies
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the application code into the container
# COPY . .

# # Set the environment variable for Flask
# ENV FLASK_APP=app.py
# ENV FLASK_RUN_HOST=0.0.0.0
# ENV FLASK_RUN_PORT=8080

# # Expose port for Flask
# EXPOSE 8080

# # Run the Flask app
# CMD ["flask", "run"]

FROM python:3.11

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    jq \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Google's official GPG key for Chrome installation (new method)
RUN wget -q -O /usr/share/keyrings/google-linux-signing-key.gpg https://dl.google.com/linux/linux_signing_key.pub

# Set up the Google Chrome repository
RUN echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-linux-signing-key.gpg] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Install ChromeDriver (version matching the installed Chrome)
# RUN wget -q --continue -P /tmp "https://storage.googleapis.com/chrome-for-testing-public/136.0.7103.92/linux64/chromedriver-linux64.zip" && \
#     unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
#     mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
#     rm -rf /usr/local/bin/chromedriver-linux64 && \
#     rm /tmp/chromedriver-linux64.zip && \
#     chmod +x /usr/local/bin/chromedriver


RUN CHROME_VERSION=$(google-chrome --version | awk '{print $3}') && \
    MAJOR_VERSION=$(echo $CHROME_VERSION | cut -d. -f1) && \
    DRIVER_URL="https://storage.googleapis.com/chrome-for-testing-public/${MAJOR_VERSION}/linux64/chromedriver-linux64.zip" && \
    wget -q --continue -P /tmp "$DRIVER_URL" && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf /usr/local/bin/chromedriver-linux64 && \
    rm /tmp/chromedriver-linux64.zip && \
    chmod +x /usr/local/bin/chromedriver


# Copy the requirements.txt and install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Set the environment variable for Flask
ENV FLASK_APP=app.py
ENV FLASK_RUN_HOST=0.0.0.0
ENV FLASK_RUN_PORT=8080

# Expose port for Flask
EXPOSE 8080

# Run the Flask app
CMD ["flask", "run"]
