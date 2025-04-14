import os
import logging
import requests
from flask import Flask, redirect, request, session
from flask_session import Session
from google_auth_oauthlib.flow import Flow
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
FLASK_SECRET = os.getenv("FLASK_SECRET")
CLIENT_SECRETS_FILE = "client_secret.json"
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
PORT = int(os.getenv("PORT", 8080))

# 初始化 Flask
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

bot_user_tokens = {}

# 设置 Telegram Webhook
def set_telegram_webhook():
    webhook_url = "https://feifei-memory-auth-bot-production.up.railway.app/webhook"
    telegram_api = f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook"
    response = requests.post(telegram_api, data={"url": webhook_url})
    print("Webhook 设置结果：", response.text)

@app.route("/")
def home():
    return "✅ AI妃授权系统正在运行中！"

@app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get("state")
        if state != session.get("state"):
            return "❌ 状态不一致，可能是 CSRF 攻击"

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        user_id = session.get("telegram_user_id")
        if user_id:
            bot_user_tokens[user_id] = {
                "token": credentials.token,
                "refresh_token": credentials.refresh_token,
                "client_id": credentials.client_id,
                "client_secret": credentials.client_secret,
                "scopes": credentials.scopes
            }
            return "✅ 授权成功！你现在可以关闭此页面。"
        else:
            return "❌ 无 Telegram 用户 ID，无法完成绑定。"
    except Exception as e:
        return f"❌ 授权失败：{e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI妃 OAuth 系统，请发送 /auth 开始授权流程。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = update.effective_user.id
        session["telegram_user_id"] = user_id

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )

        authorization_url, state = flow.authorization_url(
            access_type="offline",
            include_granted_scopes=True,
            prompt="consent"
        )

        session["state"] = state
        keyboard = [[InlineKeyboardButton("点击此处授权", url=authorization_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text("请点击以下按钮授权登录：", reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(f"⚠️ 授权流程异常：{e}")

def run_all():
    from telegram.ext import Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))

    # 注册 webhook（最关键）
    set_telegram_webhook()

    # 启动 webhook 服务器
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        webhook_url="https://feifei-memory-auth-bot-production.up.railway.app/webhook"
    )

if __name__ == "__main__":
    run_all()
