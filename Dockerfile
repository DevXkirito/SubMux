# Base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install FFmpeg
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Command to run the bot
CMD ["python", "bot.py"]
