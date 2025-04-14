import os
import logging
from flask import Flask, session, request
from flask_session import Session
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from threading import Thread

# ========== 加载环境变量 ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FLASK_SECRET = os.getenv("FLASK_SECRET", "my_flask_secret")
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
PORT = int(os.getenv("PORT", 8080))

# ========== Flask 配置 ==========
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# ========== 日志 ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Telegram 指令 ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("你好！我是 AI 妃 🤖，输入 /auth 开始授权流程")
    logger.info(f"用户 {update.effective_user.id} 启动了 /start")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=OAUTH_REDIRECT_URL,
    )
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["state"] = state
    reply_markup = InlineKeyboardMarkup(
        [[InlineKeyboardButton("🔐 点击这里授权 Google", url=auth_url)]]
    )
    await update.message.reply_text("请点击下方按钮完成授权：", reply_markup=reply_markup)

# ========== Google OAuth 回调 ==========
@app.route("/oauth2callback")
def oauth2callback():
    try:
        flow = Flow.from_client_secrets_file(
            "client_secret.json",
            scopes=["https://www.googleapis.com/auth/drive.file"],
            redirect_uri=OAUTH_REDIRECT_URL,
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_id = session.get("telegram_user_id")

        if user_id:
            logger.info(f"✅ 用户 {user_id} 授权成功")
            return f"✅ 授权成功！前10位 token: {credentials.token[:10]}..."
        else:
            return "⚠️ 未找到 Telegram 用户 ID"
    except Exception as e:
        logger.error(f"❌ 授权回调异常: {e}")
        return f"❌ 授权失败：{str(e)}"

# ========== 启动 Telegram Bot ==========
def run_bot():
    try:
        app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
        app_telegram.add_handler(CommandHandler("start", start))
        app_telegram.add_handler(CommandHandler("auth", auth))
        logging.info("🚀 Telegram Bot 正在启动 polling...")
        app_telegram.run_polling()
    except Exception as e:
        logger.error(f"Telegram Bot 启动失败: {e}", exc_info=True)

# ========== 主入口 ==========
if __name__ == "__main__":
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=PORT + 1)
