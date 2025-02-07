import os
import re
import logging
import asyncio
from telegram import Update, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)

# Configuration
API_ID = 22641991  # Replace with your API ID
API_HASH = "364c5c5f81e1f1fc3a19a8b41a5ea98f"  # Replace with your API Hash
BOT_TOKEN = "6040076450:AAE1R9oM7QmtwBbnURhzLZ2GeYTayI7EkmY"  # Replace with your Bot Token
FONT_NAME = "HelveticaRounded-Bold.otf"
FONT_SIZE = 20
FONT_COLOR = "white"
FONT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts")

# Conversation states
WAITING_VIDEO, WAITING_SUBS = range(2)

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Send /burn_subtitle to start the process of adding subtitles to your video.\n"
        "Supported video formats: MP4, MKV\n"
        "Supported subtitle formats: SRT, ASS"
    )
    return ConversationHandler.END

async def burn_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Please send the video file first")
    return WAITING_VIDEO

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    video_file = await update.message.document.get_file()
    
    # Store file info in context
    context.user_data["video_file"] = video_file
    context.user_data["video_ext"] = update.message.document.file_name.split(".")[-1]
    
    await update.message.reply_text("Now please send the subtitle file")
    return WAITING_SUBS

async def handle_subtitle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    sub_file = await update.message.document.get_file()
    
    # Create temporary filenames
    input_video = f"temp_{user.id}_input.{context.user_data['video_ext']}"
    input_sub = f"temp_{user.id}_sub.{update.message.document.file_name.split('.')[-1]}"
    output_video = f"temp_{user.id}_output.{context.user_data['video_ext']}"

    try:
        # Download files
        await context.user_data["video_file"].download_to_drive(input_video)
        await sub_file.download_to_drive(input_sub)

        # FFmpeg command with improved escaping
        ffmpeg_cmd = [
            "ffmpeg",
            "-y",
            "-i",
            input_video,
            "-filter_complex",
            f"[0:v]scale=1920:1080,subtitles=f={input_sub}:fontsdir='{FONT_DIR}':force_style='FontName={FONT_NAME},FontSize={FONT_SIZE},PrimaryColour={FONT_COLOR}'[v]",
            "-map",
            "[v]",
            "-map",
            "0:a?",
            "-c:v",
            "libx265",
            "-preset",
            "medium",
            "-crf",
            "23",
            "-pix_fmt",
            "yuv420p10le",
            output_video,
        ]

        process = await asyncio.create_subprocess_exec(
            *ffmpeg_cmd,
            stderr=asyncio.subprocess.PIPE,
        )

        progress_msg = await update.message.reply_text("Processing: 0% [░░░░░░░░░░]")
        duration = None

        while True:
            line = await process.stderr.readline()
            if not line:
                break

            line = line.decode().strip()
            
            # Get duration
            if not duration:
                duration_match = re.search(r"Duration: (\d+:\d+:\d+\.\d+)", line)
                if duration_match:
                    duration_parts = duration_match.group(1).split(":")
                    duration = (
                        float(duration_parts[0]) * 3600
                        + float(duration_parts[1]) * 60
                        + float(duration_parts[2])
                    )

            # Update progress
            time_match = re.search(r"time=(\d+:\d+:\d+\.\d+)", line)
            if time_match and duration:
                time_parts = time_match.group(1).split(":")
                current_time = (
                    float(time_parts[0]) * 3600
                    + float(time_parts[1]) * 60
                    + float(time_parts[2])
                )
                progress = min(current_time / duration, 1.0)
                bar = "█" * int(progress * 20) + "░" * (20 - int(progress * 20))
                await progress_msg.edit_text(
                    f"Processing: {int(progress*100)}% [{bar}]"
                )

        if await process.wait() == 0:
            await update.message.reply_document(
                document=InputFile(output_video), caption="Processed Video"
            )
        else:
            await update.message.reply_text("Error processing video")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        await update.message.reply_text(f"Error processing video: {str(e)}")
    finally:
        # Cleanup files
        for f in [input_video, input_sub, output_video]:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception as e:
                logger.error(f"Error deleting file {f}: {str(e)}")

    return ConversationHandler.END

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("burn_subtitle", burn_subtitle)],
        states={
            WAITING_VIDEO: [MessageHandler(filters.Document.VIDEO | filters.Document.MIME_VIDEO, handle_video)],
            WAITING_SUBS: [MessageHandler(filters.Document.MIME_TYPE("text/plain") | filters.Document.MIME_TYPE("text/x-ssa"), handle_subtitle)],
        },
        fallbacks=[CommandHandler("cancel", start)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(conv_handler)

    application.run_polling()

if __name__ == "__main__":
    main()
