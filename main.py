import os
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from flask import Flask, request
from flask_session import Session
import asyncio

# ========== 配置 ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OAUTH_CLIENT_SECRET_FILE = "client_secret.json"
OAUTH_SCOPES = ['https://www.googleapis.com/auth/drive.file']
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")
PORT = int(os.getenv("PORT", 8080))

# ========== 日志 ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Flask 应用 ==========
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "defaultsecret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ========== 临时存储授权状态 ==========
user_oauth_map = {}

# ========== Telegram Bot ==========
app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统！请输入 /auth 授权 Google")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = Flow.from_client_secrets_file(
        OAUTH_CLIENT_SECRET_FILE,
        scopes=OAUTH_SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    user_oauth_map[state] = update.effective_user.id
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("授权 Google", url=authorization_url)]])
    await update.message.reply_text("请点击以下链接授权 Google：", reply_markup=markup)

app_telegram.add_handler(CommandHandler("start", start))
app_telegram.add_handler(CommandHandler("auth", auth))

# ========== Flask 回调 ==========
@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get('state')
    telegram_user_id = user_oauth_map.get(state)
    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        logger.info(f"✅ 用户 {telegram_user_id} 成功授权 Google")
        return f"<h2>✅ 授权成功</h2><p>Telegram ID: {telegram_user_id}</p>"
    except Exception as e:
        logger.error(f"❌ 授权失败: {e}")
        return f"<h2>❌ 授权失败:</h2><p>{e}</p>"

# ========== 启动服务 ==========
async def main():
    # 启动 Telegram bot
    await app_telegram.initialize()
    await app_telegram.start()
    await app_telegram.updater.start_polling()
    logger.info("🤖 Telegram Bot 已启动")

    # 启动 Flask（非阻塞）
    from threading import Thread
    def run_flask():
        app.run(host='0.0.0.0', port=PORT)
    Thread(target=run_flask).start()

    # 等待直到关闭
    await app_telegram.updater.wait_until_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
