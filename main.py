import os
import logging
from flask import Flask, request
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
import threading

# --- 环境变量 ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
OAUTH_CLIENT_SECRET_FILE = "client_secret.json"
PORT = int(os.getenv("PORT", 8080))

# --- Google 权限范围 ---
SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask 初始化 ---
app = Flask(__name__)

# --- 用户认证状态存储 ---
user_states = {}

# --- Telegram Bot 逻辑 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统！请使用 /auth 授权 Google 服务。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = Flow.from_client_secrets_file(
        OAUTH_CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URL
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    user_states[state] = update.effective_user.id
    button = InlineKeyboardMarkup([[InlineKeyboardButton("点击授权", url=authorization_url)]])
    await update.message.reply_text("请点击下方按钮授权 Google：", reply_markup=button)

# --- OAuth 回调 ---
@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    code = request.args.get("code")
    if state not in user_states:
        return "⚠️ 授权失败：未知的 state"

    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URL,
            state=state
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        telegram_id = user_states[state]

        logger.info(f"✅ 用户 {telegram_id} 授权成功！")
        return f"<h2>✅ 授权成功！</h2><p>Telegram ID: {telegram_id}</p>"

    except Exception as e:
        logger.error(f"OAuth 失败: {e}")
        return f"❌ 授权失败: {e}"

# --- 启动 Bot ---
def run_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("auth", auth))
    logger.info("🤖 Telegram Bot 正在运行")
    app_bot.run_polling()

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()
    logger.info(f"🌐 Flask Web 服务运行中，监听端口 {PORT}")
    app.run(host="0.0.0.0", port=PORT)
