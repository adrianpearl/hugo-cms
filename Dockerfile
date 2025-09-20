FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Hugo
RUN wget -O hugo.deb https://github.com/gohugoio/hugo/releases/download/v0.121.1/hugo_extended_0.121.1_linux-amd64.deb \
    && dpkg -i hugo.deb \
    && rm hugo.deb

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV GIT_PYTHON_REFRESH=quiet
ENV PATH="/usr/bin:$PATH"

# Expose port
EXPOSE 5000

# Run the application
CMD ["python", "app.py"]
