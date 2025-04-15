import os
import logging
import asyncio
from flask import Flask, request
from google_auth_oauthlib.flow import Flow
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes
)

# ========== 配置 ==========
BOT_TOKEN = os.environ.get("BOT_TOKEN")
OAUTH_REDIRECT_URL = os.environ.get("OAUTH_REDIRECT_URL")
OAUTH_CLIENT_SECRET_FILE = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "client_secret.json")
SCOPES = ["https://www.googleapis.com/auth/drive.metadata.readonly"]

app_flask = Flask(__name__)
user_oauth_map = {}

# ========== 日志 ==========
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========== Bot 指令 ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"收到 /start 指令，来自用户 {update.effective_user.id}")
    await update.message.reply_text("欢迎使用 AI 妃系统！请输入 /auth 授权 Google")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URL,
        )
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        user_id = update.effective_user.id
        user_oauth_map[state] = user_id

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("点击授权 Google", url=auth_url)]]
        )
        await update.message.reply_text("请点击以下按钮完成授权：", reply_markup=keyboard)

    except Exception as e:
        logger.error(f"/auth 出错：{e}")
        await update.message.reply_text("❌ 无法生成授权链接，请稍后再试。")

# ========== Flask 授权回调 ==========
@app_flask.route("/oauth2callback")
def oauth2callback():
    try:
        code = request.args.get("code")
        state = request.args.get("state")
        user_id = user_oauth_map.get(state)

        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=SCOPES,
            redirect_uri=OAUTH_REDIRECT_URL,
            state=state
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        logger.info(f"✅ 用户 {user_id} 授权成功")
        return f"<h2>✅ 授权成功！</h2><p>Telegram 用户 ID：{user_id}</p><p>你现在可以回到 Telegram 使用 AI 妃功能。</p>"

    except Exception as e:
        logger.error(f"回调失败：{e}")
        return f"<h2>❌ 授权失败</h2><p>{e}</p>"

# ========== 启动逻辑 ==========
async def run_bot():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("auth", auth))
    logger.info("🤖 Telegram Bot 正在启动...")
    await app.run_polling()

async def main():
    loop = asyncio.get_running_loop()

    # 启动 Flask（异步执行）
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"🚀 Flask Web 服务器监听端口 {port}")
    asyncio.create_task(app_flask.run_task(host="0.0.0.0", port=port, use_reloader=False))

    # 启动 Telegram Bot
    await run_bot()

# Monkey patch Flask 以支持 asyncio.create_task 调用 run
from werkzeug.serving import is_running_from_reloader
if __name__ == "__main__":
    if not is_running_from_reloader():  # 防止双重执行
        asyncio.run(main())
