# Use an official Python runtime as a parent image.
FROM python:3.11-slim

# Install curl (needed for the subprocess call) and clean up apt caches.
RUN apt-get update && apt-get install -y curl && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Set the working directory to /app.
WORKDIR /app

# Copy the requirements file into the container.
COPY requirements2.txt ./

# Install any needed packages specified in requirements.txt.
RUN pip install --no-cache-dir -r requirements2.txt

# Copy the rest of the application code.
COPY . .

# Expose port 8080 to the outside world.
EXPOSE 8080

# Define environment variable for Flask (optional).
ENV FLASK_APP=app.py

# Run the application.
CMD ["python", "test_conn.py"]
