import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow

from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", 8080))
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 存储授权状态
user_oauth_map = {}

# Flask 实例
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ AI 妃系统运行中", 200

@app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get("state")
        code = request.args.get("code")
        user_id = user_oauth_map.get(state)

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URL
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        logger.info(f"✅ 用户 {user_id} 授权成功")
        return f"<h2>✅ 授权成功！</h2><p>Telegram 用户 ID：{user_id}</p>"

    except Exception as e:
        logger.error(f"❌ 授权失败: {e}")
        return f"<h2>❌ 授权失败</h2><p>{e}</p>"

# Telegram Bot 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统，请使用 /auth 授权 Google 服务。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URL
    )
    auth_url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true')
    user_id = update.effective_user.id
    user_oauth_map[state] = user_id
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("授权 Google", url=auth_url)]])
    await update.message.reply_text("请点击以下链接授权 Google 服务：", reply_markup=markup)

# 同时运行 Flask 和 Telegram Bot
async def run_all():
    # 启动 Flask（单独线程）
    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    # 启动 Telegram Polling
    app_telegram: Application = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("auth", auth))

    logger.info("🤖 Telegram Bot 正在启动...")
    await app_telegram.run_polling()

if __name__ == "__main__":
    asyncio.run(run_all())
