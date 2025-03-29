# Use slim Python 3 base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the CLI tool
COPY bin/ad2-firmwareupload bin/ad2-firmwareupload
RUN chmod +x bin/ad2-firmwareupload

# Default command for firmware flashing
ENTRYPOINT ["bin/ad2-firmwareupload"]
