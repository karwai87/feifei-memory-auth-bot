# main.py
import os
import logging
from flask import Flask, request, session
from flask_session import Session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# ==== 初始化 ====
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FLASK_SECRET = os.getenv("FLASK_SECRET", "your_flask_secret")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://xxx.up.railway.app/webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegramsecret")
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")

app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ==== Telegram 逻辑 ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统，输入 /auth 开始授权")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        'client_secret.json',
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=REDIRECT_URI
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    session["state"] = state
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("点我授权 Google", url=auth_url)]])
    await update.message.reply_text("点击下方按钮开始授权：", reply_markup=markup)

# ==== Flask OAuth 回调 ====
@app.route("/oauth2callback")
def oauth2callback():
    try:
        flow = Flow.from_client_secrets_file(
            'client_secret.json',
            scopes=["https://www.googleapis.com/auth/drive.file"],
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_id = session.get("telegram_user_id")
        if user_id:
            logger.info(f"✅ 用户 {user_id} 成功授权")
            return f"✅ 授权成功！Access Token 前10位: {credentials.token[:10]}..."
        else:
            return "⚠️ 无法识别用户 ID"
    except Exception as e:
        return f"❌ 授权失败：{e}"

@app.route("/")
def index():
    return "✅ AI妃系统运行中"

@app.route("/health")
def health():
    return {"status": "healthy"}

# ==== 启动 Bot（Webhook 模式）====
def start_bot():
    app_telegram = ApplicationBuilder().token(BOT_TOKEN).build()
    app_telegram.add_handler(CommandHandler("start", start))
    app_telegram.add_handler(CommandHandler("auth", auth))

    app_telegram.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url=WEBHOOK_URL,
        secret_token=WEBHOOK_SECRET,
        drop_pending_updates=True
    )

# ==== 主程序入口 ====
if __name__ == "__main__":
    start_bot()  # 不再放入 Thread，主线程运行 Telegram
