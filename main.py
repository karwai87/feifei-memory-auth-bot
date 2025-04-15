import os
import logging
import asyncio
import threading
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request
from google_auth_oauthlib.flow import Flow

# 环境变量
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OAUTH_REDIRECT_URL = os.environ.get("OAUTH_REDIRECT_URL")
OAUTH_CLIENT_SECRET_FILE = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "client_secret.json")
OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

# Flask 初始化
app_flask = Flask(__name__)
port = int(os.environ.get("PORT", 8080))

# 用户OAuth状态缓存
user_oauth_map = {}

# 日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Telegram 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"收到 /start 指令，来自用户 {user.id}")
    await update.message.reply_text("欢迎使用 AI 妃系统！请输入 /auth 授权 Google")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            redirect_uri=OAUTH_REDIRECT_URL
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        user_oauth_map[state] = update.effective_user.id
        keyboard = [[InlineKeyboardButton("授权 Google", url=auth_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("请点击下方按钮完成授权：", reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"❌ 生成授权链接失败: {e}")
        await update.message.reply_text("❌ 无法生成授权链接，请稍后再试。")

# Flask 回调处理
@app_flask.route('/oauth2callback')
def oauth2callback():
    try:
        state = request.args.get('state')
        code = request.args.get('code')

        if not state or not code:
            return "缺少 state 或 code 参数", 400

        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URL
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_id = user_oauth_map.get(state)
        logger.info(f"✅ 用户 {user_id} 授权成功")

        return f"<h2>✅ 授权成功！</h2><p>Telegram 用户 ID：{user_id}</p><p>你现在可以回到 Telegram 使用 AI 妃功能。</p>"
    except Exception as e:
        logger.error(f"❌ 回调处理失败: {e}")
        return f"❌ 授权失败：{e}", 500

# 启动 Telegram bot
async def run_telegram_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    logger.info("✅ Telegram Bot 已启动")
    await app.run_polling()

# 启动 Flask 服务器
def run_flask_server():
    logger.info(f"🚀 Flask Web 服务监听端口 {port}")
    app_flask.run(host="0.0.0.0", port=port)

# 启动主程序
if __name__ == "__main__":
    flask_thread = threading.Thread(target=run_flask_server)
    flask_thread.daemon = True
    flask_thread.start()

    asyncio.run(run_telegram_bot())
