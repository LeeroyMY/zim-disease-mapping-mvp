# Use an official Python runtime as a parent image
FROM python:3.12.3-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies for GDAL/GeoDjango and PostgreSQL
RUN apt-get update && apt-get install -y \
    binutils \
    libproj-dev \
    gdal-bin \
    libgdal-dev \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the project files into the container
COPY . /app/

# Fix Windows CRLF line endings and make entrypoint executable
RUN sed -i 's/\r$//' render-entrypoint.sh && chmod +x render-entrypoint.sh

# Expose port 8000
EXPOSE 8000

# Run entrypoint script
CMD ["./render-entrypoint.sh"]
