# Use the official Python image.
# https://hub.docker.com/_/python
FROM python:3.10-slim

# Allow statements and log messages to immediately appear in the Knative logs
ENV PYTHONUNBUFFERED True

# Set the port for Cloud Run (default is 8080)
ENV PORT 8080

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
# This layer will only rebuild if requirements.txt changes
COPY requirements.txt .

# Install production dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy only necessary application files
COPY main.py .
COPY importstock.py .
COPY tickers.json .

# Run the web service on container startup
# functions-framework will use the PORT environment variable
CMD exec functions-framework --target=cloud_function_entry --source=main.py --port=$PORT
