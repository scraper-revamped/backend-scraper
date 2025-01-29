# Use a base image with Python
FROM python:3.11

# Set the working directory
WORKDIR /app

# # Install required packages for Chrome and other dependencies
# RUN apt-get update && apt-get install -y \
#     wget \
#     unzip \
#     libnss3 \
#     libxss1 \
#     libappindicator3-1 \
#     libatk-bridge2.0-0 \
#     libgtk-3-0 \
#     libgbm-dev \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    libnss3 \
    libxss1 \
    libappindicator3-1 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    libgbm-dev \
    chromium \
    chromium-driver \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Add Google's official GPG key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - 

# Set up the Google repository
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable

# Install Python dependencies (add your requirements.txt if you have one)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt


# Copy the application code into the container
COPY . .


# Expose the port the app runs on
EXPOSE 8080

# Command to run the application
CMD ["python", "test_main.py"]