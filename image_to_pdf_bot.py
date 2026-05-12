import threading
import os
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from PIL import Image
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

# ── Web server to keep Render alive ──────────────────────────────────────────
class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")

    def log_message(self, format, *args):
        pass  # Suppress request logs

def run_server():
    server = HTTPServer(("0.0.0.0", 8080), Handler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN environment variable is not set!")

# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📖 របៀបប្រើប្រាស់បូត", callback_data="how_to_use")],
        [InlineKeyboardButton("🖼️ ប្រភេទរូបភាពដែលស្គាល់", callback_data="supported_types")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "👋 សូមស្វាគមន៍មកកាន់ *បូតបំប្លែងរូបភាពទៅ PDF*!\n\n"
        "📸 ផ្ញើរូបភាពណាមួយមកបូត រួចបូតនឹងបំប្លែងវាទៅជាឯកសារ PDF ភ្លាមៗ!\n\n"
        "ចុចប៊ូតុងខាងក្រោមដើម្បីស្វែងយល់បន្ថែម 👇",
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "how_to_use":
        await query.message.reply_text(
            "📖 *របៀបប្រើប្រាស់បូត*\n\n"
            "1️⃣ ចុច /start ដើម្បីចាប់ផ្តើម\n"
            "2️⃣ ផ្ញើរូបភាពមក (ផ្ញើជា *File* ឬ *Photo* ក៏បាន)\n"
            "3️⃣ រង់ចាំបន្តិច បូតនឹងបំប្លែងវាទៅជា PDF\n"
            "4️⃣ ទាញយក PDF របស់អ្នក!\n\n"
            "💡 *គន្លឹះ:* ប្រសិនបើចង់បានគុណភាពល្អ សូមផ្ញើជា *File* ជាជាង Photo",
            parse_mode="Markdown",
        )

    elif query.data == "supported_types":
        await query.message.reply_text(
            "🖼️ *ប្រភេទរូបភាពដែលស្គាល់*\n\n"
            "✅ JPG / JPEG\n"
            "✅ PNG\n"
            "✅ BMP\n"
            "✅ WEBP\n"
            "✅ TIFF\n\n"
            "❌ *មិនស្គាល់:* GIF, SVG, RAW\n\n"
            "📏 *ទំហំអតិបរមា:* 20MB",
            parse_mode="Markdown",
        )

async def handle_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ កំពុងបំប្លែងរូបភាពទៅ PDF សូមរង់ចាំ...")

    input_path = None
    output_path = None

    try:
        tmp_dir = tempfile.gettempdir()

        # Get the file
        if update.message.document:
            file = await update.message.document.get_file()
            file_name = update.message.document.file_name or "image.jpg"
        elif update.message.photo:
            file = await update.message.photo[-1].get_file()
            file_name = "image.jpg"
        else:
            await update.message.reply_text("⚠️ សូមផ្ញើរូបភាពតែប៉ុណ្ណោះ!")
            return

        # Download the image
        input_path = os.path.join(tmp_dir, f"{file.file_id}.jpg")
        output_path = os.path.join(tmp_dir, f"{file.file_id}.pdf")
        await file.download_to_drive(input_path)

        # Convert to PDF
        image = Image.open(input_path).convert("RGB")
        image.save(output_path, "PDF", resolution=100.0)

        # Send PDF back
        with open(output_path, "rb") as pdf_file:
            pdf_name = file_name.rsplit(".", 1)[0] + ".pdf"
            await update.message.reply_document(
                document=pdf_file,
                filename=pdf_name,
                caption="✅ បំប្លែងរួចរាល់! នេះជា PDF របស់អ្នក 🎉",
            )

    except Exception as e:
        await update.message.reply_text(
            f"⚠️ មានបញ្ហាក្នុងការបំប្លែង។\nសូមព្យាយាមម្តងទៀត!\nError: {e}"
        )

    finally:
        # Always clean up temp files, even if an error occurred
        for path in (input_path, output_path):
            if path and os.path.exists(path):
                os.remove(path)

async def handle_other(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📸 សូមផ្ញើរូបភាពដើម្បីបំប្លែងទៅ PDF!\n"
        "ចុច /start ដើម្បីមើលម៉ឺនុយ។"
    )

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_other))
    print("🤖 Image to PDF Bot is running...")
    app.run_polling(drop_pending_updates=True, allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()
