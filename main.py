import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# 加载 .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

# /start 指令回应
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("我在 ✅")

# 启动 Telegram Bot（使用 polling，最稳）
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
