import logging
import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
import asyncio
import threading

# Telegram Bot 配置
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OAUTH_CLIENT_SECRET_FILE = "client_secret.json"
OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]
OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URL")
PORT = int(os.environ.get("PORT", 8080))

# 全局用户 map
user_oauth_map = {}

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask App
flask_app = Flask(__name__)

@flask_app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get('state')
        telegram_user_id = user_oauth_map.get(state)

        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        if telegram_user_id:
            logger.info(f"✅ 用户 {telegram_user_id} 授权成功")
            return f"<h2>✅ 授权成功</h2><p>Telegram 用户 ID：{telegram_user_id}</p>"
        else:
            return "⚠️ 授权成功，但无法关联 Telegram 用户。"
    except Exception as e:
        logger.error(f"❌ 回调失败: {e}")
        return f"❌ 回调失败: {e}"

# Telegram 处理逻辑
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统！请使用 /auth 授权 Google 服务。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        user_oauth_map[state] = update.effective_user.id
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("授权 Google", url=auth_url)]])
        await update.message.reply_text("请点击以下链接授权 Google：", reply_markup=markup)
    except Exception as e:
        logger.error(f"/auth 失败: {e}")
        await update.message.reply_text(f"❌ 生成授权链接失败：{e}")

# 启动 telegram bot
async def run_telegram_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    await app.run_polling()

# 主入口：Flask + Bot 同时运行
def run_all():
    # 启动 Flask（非阻塞）
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=PORT), daemon=True).start()

    # 启动 Telegram Bot（主线程内）
    asyncio.run(run_telegram_bot())

if __name__ == "__main__":
    run_all()
