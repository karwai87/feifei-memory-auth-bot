import os
import threading
import logging
from flask import Flask, request, redirect
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow

# 环境变量
BOT_TOKEN = os.getenv("BOT_TOKEN")
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")
CLIENT_SECRET_FILE = "client_secret.json"

# 日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask 初始化
app_flask = Flask(__name__)

# OAuth 授权状态管理
user_oauth_map = {}

@app_flask.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get('state')
        telegram_user_id = user_oauth_map.get(state)

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=['https://www.googleapis.com/auth/drive.metadata.readonly'],
            state=state,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        if telegram_user_id:
            logger.info(f"✅ 用户 {telegram_user_id} 授权成功")
            return f"✅ 授权成功！Telegram 用户 ID：{telegram_user_id}，你现在可以返回 Telegram 使用 bot 功能。"
        else:
            return "⚠️ 授权成功，但找不到 Telegram 用户 ID"

    except Exception as e:
        logger.error(f"❌ OAuth 回调失败: {e}")
        return f"❌ 授权失败: {e}"

# Telegram 处理函数
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"收到 /start 指令，来自用户 {user.id}")
    await update.message.reply_text("欢迎使用 AI 妃系统！请输入 /auth 授权 Google")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=['https://www.googleapis.com/auth/drive.metadata.readonly'],
            redirect_uri=OAUTH_REDIRECT_URI
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )
        user_oauth_map[state] = update.effective_user.id
        keyboard = [[InlineKeyboardButton("授权 Google", url=authorization_url)]]
        await update.message.reply_text("请点击下方链接授权 Google：", reply_markup=InlineKeyboardMarkup(keyboard))
    except Exception as e:
        logger.error(f"❌ 生成授权链接失败: {e}")
        await update.message.reply_text(f"❌ 授权失败：{e}")

# 启动 Telegram bot
def run_telegram():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    logger.info("Telegram Bot 已启动")
    app.run_polling()

# 启动 Flask
def run_flask():
    logger.info("Flask Web 服务运行中，监听端口 8080")
    app_flask.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))

# 同时运行两个服务
if __name__ == "__main__":
    threading.Thread(target=run_telegram).start()
    threading.Thread(target=run_flask).start()
