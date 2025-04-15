import os
import logging
import asyncio
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
from hypercorn.asyncio import serve
from hypercorn.config import Config

load_dotenv()

# ========== 环境变量 ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
PORT = int(os.getenv("PORT", 8080))
CLIENT_SECRET_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]  # 替换为您需要的 Google API 权限

# ========== 日志 ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Flask ==========
app = Flask(__name__)
user_oauth_map = {}

@app.route("/")
def home():
    return "✅ AI 妃系统运行中", 200

@app.route("/oauth2callback")
def oauth2callback():
    state = request.args.get("state")
    code = request.args.get("code")
    user_id = user_oauth_map.get(state)

    try:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRET_FILE,
            scopes=SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URL
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        logger.info(f"✅ 用户 {user_id} 完成授权")
        return f"""
            <h2>✅ 授权成功！</h2>
            <p>Telegram 用户 ID：{user_id}</p>
            <p>你现在可以回到 Telegram 使用 AI 妃功能。</p>
        """
    except Exception as e:
        logger.error(f"❌ 授权失败: {e}")
        return f"<h2>❌ 授权失败</h2><p>{e}</p>"

# ========== Telegram Bot ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"你好 {user.first_name}！发送 /auth 开始授权。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri=OAUTH_REDIRECT_URL
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    user_oauth_map[state] = user_id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("点击这里授权 Google", url=auth_url)]
    ])
    await update.message.reply_text("请点击下方按钮授权 Google：", reply_markup=keyboard)

async def main():
    # 启动 Telegram Bot
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("auth", auth))

    async def run_flask():
        config = Config()
        config.bind = [f"0.0.0.0:{PORT}"]
        await serve(app, config)

    # 使用 asyncio.gather 并发运行 Telegram Bot 和 Flask
    try:
        await asyncio.gather(app_telegram.run_polling(), run_flask())
    except Exception as e:
        logger.error(f"主程序发生异常: {e}")
    finally:
        await app_telegram.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
