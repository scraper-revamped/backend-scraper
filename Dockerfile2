# # # Use a base image with Python
# # FROM python:3.11

# # # Set the working directory
# # WORKDIR /app

# # # # Install required packages for Chrome and other dependencies
# # # RUN apt-get update && apt-get install -y \
# # #     wget \
# # #     unzip \
# # #     libnss3 \
# # #     libxss1 \
# # #     libappindicator3-1 \
# # #     libatk-bridge2.0-0 \
# # #     libgtk-3-0 \
# # #     libgbm-dev \
# # #     && apt-get clean \
# # #     && rm -rf /var/lib/apt/lists/*
# # RUN apt-get update && apt-get install -y \
# #     wget \
# #     unzip \
# #     libnss3 \
# #     libxss1 \
# #     libappindicator3-1 \
# #     libatk-bridge2.0-0 \
# #     libgtk-3-0 \
# #     libgbm-dev \
# #     chromium \
# #     chromium-driver \
# #     && apt-get clean \
# #     && rm -rf /var/lib/apt/lists/*

# # # Add Google's official GPG key
# # RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - 

# # # Set up the Google repository
# # RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# # # Install Google Chrome
# # RUN apt-get update && apt-get install -y google-chrome-stable

# # # Install Python dependencies (add your requirements.txt if you have one)
# # COPY requirements.txt ./
# # RUN pip install --no-cache-dir -r requirements.txt


# # # Copy the application code into the container
# # COPY . .


# # # Expose the port the app runs on
# # EXPOSE 8080

# # # Command to run the application
# # CMD ["streamlit", "run", "test_main.py", "--server.port=8080", "--server.address=0.0.0.0"]



# FROM python:3.11

# # Set the working directory
# WORKDIR /app

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


# # Add Google's official GPG key
# RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - 

# # Set up the Google repository
# RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# # Install Google Chrome
# RUN apt-get update && apt-get install -y google-chrome-stable

# # Install Python dependencies (add your requirements.txt if you have one)
# COPY requirements.txt ./
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy the application code into the container
# COPY . .

# # Expose the port the app runs on
# EXPOSE 8080

# # Command to run the application
# CMD ["streamlit", "run", "test_main.py", "--server.port=8080", "--server.address=0.0.0.0"]


# FROM python:3.11-slim

# WORKDIR /app

# # Install Chrome and dependencies
# RUN apt-get update && apt-get install -y \
#     wget \
#     gnupg \
#     unzip \
#     chromium \
#     chromium-driver \
#     libnss3 \
#     libgconf-2-4 \
#     libfontconfig1 \
#     xvfb \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Set environment variables
# ENV PYTHONUNBUFFERED=1
# ENV CHROME_BIN=/usr/bin/chromium
# ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
# ENV DISPLAY=:99

# # Copy and install requirements
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# # Copy application code
# COPY . .

# # Create a wrapper script to start Xvfb and the application
# RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x16 &\npython main.py' > /app/start.sh
# RUN chmod +x /app/start.sh

# EXPOSE 8080

# CMD ["/app/start.sh"]


# # Use an official Python runtime as a parent image
# FROM python:3.9-slim

# # Set the working directory in the container
# WORKDIR /app

# # Install system dependencies for Chrome/Chromium and other libraries
# RUN apt-get update && apt-get install -y \
#     wget \
#     gnupg \
#     unzip \
#     chromium \
#     chromium-driver \
#     libnss3 \
#     libgconf-2-4 \
#     libfontconfig1 \
#     xvfb \
#     libgomp1 \
#     && apt-get clean \
#     && rm -rf /var/lib/apt/lists/*

# # Set environment variables for Chrome/Chromium
# ENV CHROME_BIN=/usr/bin/chromium
# ENV CHROMEDRIVER_PATH=/usr/bin/chromedriver
# ENV DISPLAY=:99

# # Set environment variables for Flask and Gunicorn
# ENV PYTHONUNBUFFERED=1
# ENV PORT 8080
# ENV FLASK_APP=main.py
# ENV FLASK_ENV=production

# # Copy the current directory contents into the container at /app
# COPY . /app

# # Install any needed packages specified in requirements.txt
# RUN pip install --no-cache-dir -r requirements.txt

# # Install Gunicorn for production
# RUN pip install gunicorn

# # Expose port 8080
# EXPOSE 8080

# # Create a wrapper script to start Xvfb and Gunicorn
# RUN echo '#!/bin/bash\nXvfb :99 -screen 0 1024x768x16 &\nexec gunicorn --bind 0.0.0.0:8080 main:app' > /app/start.sh
# RUN chmod +x /app/start.sh

# # Run the application using the wrapper script
# CMD ["/app/start.sh"]

# 

FROM python:3.11

WORKDIR /app

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

# Add Google's official GPG key
RUN wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - 

# Set up the Google repository
RUN echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list

# Install Google Chrome
RUN apt-get update && apt-get install -y google-chrome-stable
# Install ChromeDriver from Chrome for Testing for Chrome version 133.0.6943.53
# Download the ChromeDriver for Chrome version 133.0.6943.53 (Linux 64-bit)
RUN wget -q --continue -P /tmp "https://storage.googleapis.com/chrome-for-testing-public/133.0.6943.53/linux64/chromedriver-linux64.zip" && \
    unzip /tmp/chromedriver-linux64.zip -d /usr/local/bin/ && \
    mv /usr/local/bin/chromedriver-linux64/chromedriver /usr/local/bin/chromedriver && \
    rm -rf /usr/local/bin/chromedriver-linux64 && \
    rm /tmp/chromedriver-linux64.zip && \
    chmod +x /usr/local/bin/chromedriver




# Install Python dependencies (add your requirements.txt if you have one)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application code into the container
COPY . .

# Expose the port the app runs on
EXPOSE 8080

# Use port 8080 for Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]