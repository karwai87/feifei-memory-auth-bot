# main.py
import os
import logging
from flask import Flask, session, request
from flask_session import Session
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from google_auth_oauthlib.flow import Flow
from threading import Thread
from datetime import datetime
import pytz

# ========== 加载环境 ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secure_secret")
PORT = int(os.getenv("PORT", 8080))

# ========== Flask 初始化 ==========
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "defaultsecret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ========== Telegram 指令 ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统，输入 /auth 开始授权")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=REDIRECT_URI,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    keyboard = [[InlineKeyboardButton("点击授权", url=auth_url)]]
    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("请点击按钮完成授权：", reply_markup=markup)

# ========== Telegram Bot 运行 ==========
def run_telegram_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))

    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )

# ========== Flask 回调接口 ==========
@app.route("/")
def index():
    return "✅ AI 妃系统启动成功"

@app.route("/oauth2callback")
def oauth2callback():
    return "✅ 授权完成（你可以关闭此页面）"

# ========== 启动点 ==========
if __name__ == "__main__":
    Thread(target=run_telegram_bot).start()
    app.run(host="0.0.0.0", port=PORT + 1)

import os
from flask import Flask, request
from flask_session import Session
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from telegram import Update
from threading import Thread
from dotenv import load_dotenv
from datetime import datetime
import pytz

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 5000))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
FLASK_SECRET = os.getenv("FLASK_SECRET", "default_secret")

app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

@app.route("/")
def home():
    return "✅ AI 妃记忆系统正在运行"

@app.route("/oauth2callback")
def oauth2callback():
    return "✅ 授权成功，你现在可以回到 Telegram 对话继续使用。"

@app.route("/health")
def health():
    return {"status": "ok"}

# Telegram 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃，输入 /auth 开始授权流程")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 请点击以下链接开始授权流程：https://example.com/oauth")

# Bot 启动函数
def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("auth", auth))

    app_bot.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path="/webhook",
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )

# 启动入口
if __name__ == "__main__":
    Thread(target=run_bot, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT)
