FROM python:3.10

# Install required dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    fontconfig \
    && fc-cache -f -v

# Copy custom fonts
COPY fonts/ /usr/share/fonts/truetype/custom/
RUN fc-cache -f -v && fc-list | grep HelveticaRounded
# Set working directory
WORKDIR /app

# Copy files
COPY . .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Run the bot
CMD ["python", "bot.py"]
