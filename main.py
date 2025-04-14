import os
import logging
from flask import Flask, session, request
from flask_session import Session
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from threading import Thread

# 初始化日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载 .env
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "defaultsecret")
PORT = int(os.getenv("PORT", 8080))
FLASK_SECRET = os.getenv("FLASK_SECRET", "kaven_secure")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")

# 初始化 Flask
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Flask 路由
@app.route("/")
def home():
    return "✅ AI妃系统运行中"

@app.route("/oauth2callback")
def oauth2callback():
    return "✅ 授权成功！（模拟）"

@app.route("/health")
def health():
    return {"status": "ok"}

# Flask 子线程运行
def run_flask():
    app.run(host="0.0.0.0", port=PORT + 1)

# Telegram 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI妃 OAuth 系统。发送 /auth 开始授权流程。")

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("请点击按钮完成授权：", reply_markup=reply_markup)

# Telegram 主线程运行（webhook）
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

# 主程序入口
if __name__ == "__main__":
    # 启动 Flask（放子线程）
    Thread(target=run_flask, daemon=True).start()

    # 启动 Telegram Bot（主线程）
    run_bot()
