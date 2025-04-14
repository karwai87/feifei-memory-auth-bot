import os
import json
import logging
from threading import Thread
from flask import Flask, request, session
from flask_session import Session
from google_auth_oauthlib.flow import Flow
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)
from datetime import datetime
import pytz
from dotenv import load_dotenv

# ==================== 初始化日志 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ==================== Flask 初始化 ====================
app = Flask(__name__)
load_dotenv()
app.secret_key = os.getenv("FLASK_SECRET", "defaultsecret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ==================== 环境变量 ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 5000))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "secret")

bot_user_tokens = {}

# ==================== Telegram 指令 ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃授权系统，输入 /auth 开始授权")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        session["telegram_user_id"] = user_id

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent"
        )

        session["state"] = state
        keyboard = [[InlineKeyboardButton("点击授权", url=authorization_url)]]
        markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("请点击按钮完成授权：", reply_markup=markup)
    except Exception as e:
        await update.message.reply_text(f"⚠️ 授权错误：{e}")

# ==================== Flask OAuth 路由 ====================
@app.route("/")
def home():
    return "✅ Flask 启动成功 - Bot 授权系统在线"

@app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get("state")
        if state != session.get("state"):
            return "❌ 状态不一致，可能是 CSRF 攻击"

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials
        user_id = session.get("telegram_user_id")

        if user_id:
            bot_user_tokens[user_id] = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }
            return "✅ 授权成功，AI记忆系统已记录。"
        return "❌ 未找到用户 ID"
    except Exception as e:
        return f"❌ 授权失败：{e}"

# ==================== 启动逻辑 ====================
def run_bot():
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

if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=PORT)
