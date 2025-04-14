# main_oauth.py
import os
from flask import Flask, session, request
from flask_session import Session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import logging

# ========== 初始化 ==========
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FLASK_SECRET = os.getenv("FLASK_SECRET", "my_flask_secret")
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
PORT = int(os.getenv("PORT", 8080))

app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== Telegram 指令 ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃授权系统，输入 /auth 开始授权")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=OAUTH_REDIRECT_URL,
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session["state"] = state
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("点击这里授权 Google", url=authorization_url)]
    ])
    await update.message.reply_text("请点击以下按钮授权 Google：", reply_markup=reply_markup)

# ========== Flask OAuth 回调 ==========
@app.route("/oauth2callback")
def oauth2callback():
    try:
        flow = Flow.from_client_secrets_file(
            'client_secret.json',
            scopes=["https://www.googleapis.com/auth/drive.file"],
            redirect_uri=OAUTH_REDIRECT_URL,
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_id = session.get("telegram_user_id")

        if user_id:
            logger.info(f"✅ 用户 {user_id} 授权成功")
            return f"✅ 授权成功！Token: {credentials.token[:10]}..."
        else:
            return "⚠️ 找不到 Telegram 用户信息"
    except Exception as e:
        return f"❌ 授权失败：{str(e)}"

# ========== 启动逻辑 ==========
def run_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("auth", auth))
    app_telegram.run_polling()

if __name__ == "__main__":
    from threading import Thread
    Thread(target=run_bot).start()
    app.run(host="0.0.0.0", port=PORT + 1)
