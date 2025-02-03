import os
import subprocess
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.error import TelegramError

# Configuration
FONT_PATH = "fonts/HelveticaRounded-Bold.otf"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Start command
def start(update: Update, context: CallbackContext):
    update.message.reply_text("Welcome! Send me a video and a subtitle file (SRT or ASS).")

# Ping command
def ping(update: Update, context: CallbackContext):
    update.message.reply_text("Pong! The bot is alive and ready to process your requests.")

# Process video with subtitles
def process_video_with_subtitles(video_path, subtitle_path, output_path):
    command = [
        "ffmpeg",
        "-i", video_path,
        "-vf", f"subtitles={subtitle_path}:force_style='FontName=Helvetica Rounded Bold,FontSize=20,PrimaryColour=&HFFFFFF&,BorderStyle=1'",
        "-c:v", "libx265",  # H.265 codec
        "-pix_fmt", "yuv420p10le",  # 10-bit color depth
        "-preset", "medium",  # Encoding speed/quality tradeoff
        "-crf", "23",  # Quality level (lower is better)
        "-c:a", "copy",  # Copy audio stream without re-encoding
        output_path
    ]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    # Progress bar
    for line in process.stdout:
        print(line.strip())
        if "frame=" in line:
            frame_info = line.split("frame=")[1].split("fps")[0].strip()
            context.bot.send_message(chat_id=update.effective_chat.id, text=f"Processing frame {frame_info}...")
    
    process.wait()

# Handle document uploads
def handle_document(update: Update, context: CallbackContext):
    document = update.message.document
    file_id = document.file_id
    file_name = document.file_name
    file_path = os.path.join(OUTPUT_DIR, file_name)

    # Download the file
    file = context.bot.get_file(file_id)
    file.download(file_path)

    if file_name.endswith((".mp4", ".mkv")):
        context.user_data["video_path"] = file_path
        update.message.reply_text("Video received. Now send the subtitle file (SRT or ASS).")
    elif file_name.endswith((".srt", ".ass")):
        context.user_data["subtitle_path"] = file_path
        update.message.reply_text("Subtitle received. Processing...")

        # Check if both video and subtitle are received
        video_path = context.user_data.get("video_path")
        subtitle_path = context.user_data.get("subtitle_path")
        if video_path and subtitle_path:
            output_path = os.path.join(OUTPUT_DIR, "output.mkv")
            process_video_with_subtitles(video_path, subtitle_path, output_path)
            update.message.reply_document(document=open(output_path, "rb"))
            update.message.reply_text("Processing complete!")
            # Clean up
            os.remove(video_path)
            os.remove(subtitle_path)
            os.remove(output_path)

# Main function
def main():
    # Replace 'YOUR_TOKEN' with your bot token
    updater = Updater("YOUR_TOKEN", use_context=True)
    dp = updater.dispatcher

    # Add handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ping", ping))  # Add ping command handler
    dp.add_handler(MessageHandler(Filters.document, handle_document))

    # Start the bot
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
