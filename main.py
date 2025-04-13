import os
import json
import logging
from flask import Flask, redirect, request, session
from flask_session import Session
from google_auth_oauthlib.flow import Flow
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev_secret_key")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = "https://feifei-memory-auth-production.up.railway.app/oauth2callback"

BOT_TOKEN = os.environ["BOT_TOKEN"]
bot_user_tokens = {}

@app.route("/")
def home():
    return "欢迎来到 AI妃 OAuth 系统"

@app.route("/oauth2callback")
def oauth2callback():
    state = session.get("state")
    if state != request.args.get("state"):
        return "State 参数不匹配，可能遭受 CSRF 攻击。", 400

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    try:
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
            return "授权成功! 您现在可以关闭此页面。"
        else:
            return "找不到 Telegram 用户 ID，无法绑定。"
    except Exception as e:
        return f"授权失败: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI妃 OAuth 系统，发送 /auth 开始授权。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    authorization_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )

    session["state"] = state
    keyboard = [[InlineKeyboardButton("点击此处授权", url=authorization_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text("请点击以下按钮完成授权：", reply_markup=reply_markup)

def run_all():
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))

    # ✅ 使用 webhook 而不是 polling
    application.run_webhook(
        listen="0.0.0.0",
        port=8080,
        webhook_url="https://feifei-memory-auth-production.up.railway.app"
    )

if __name__ == "__main__":
    run_all()
