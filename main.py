import os
import logging
import asyncio
from flask import Flask, redirect, request, session
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from oauthlib.oauth2 import WebApplicationClient
import requests
import json

# --- 环境变量读取 ---
BOT_TOKEN = os.environ.get("BOT_TOKEN")
FLASK_SECRET = os.environ.get("FLASK_SECRET", "dev_secret")
OAUTH_REDIRECT_URL = os.environ.get("OAUTH_REDIRECT_URL")
GOOGLE_CLIENT_SECRET_FILE = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET_FILE", "client_secret.json")
PORT = int(os.environ.get("PORT", 8080))

# --- 日志设置 ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Flask App 初始化 ---
app = Flask(__name__)
app.secret_key = FLASK_SECRET

# --- 读取 Google OAuth 配置 ---
with open(GOOGLE_CLIENT_SECRET_FILE) as f:
    google_creds = json.load(f)["web"]

GOOGLE_CLIENT_ID = google_creds["client_id"]
GOOGLE_CLIENT_SECRET = google_creds["client_secret"]
GOOGLE_AUTH_URI = google_creds["auth_uri"]
GOOGLE_TOKEN_URI = google_creds["token_uri"]

client = WebApplicationClient(GOOGLE_CLIENT_ID)


# --- Telegram Bot 指令处理 ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info(f"收到 /start 指令，来自用户 {update.effective_user.id}")
    await update.message.reply_text("欢迎使用 AI 妃系统！请输入 /auth 授权 Google")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    authorization_url = client.prepare_request_uri(
        GOOGLE_AUTH_URI,
        redirect_uri=OAUTH_REDIRECT_URL,
        scope=["https://www.googleapis.com/auth/userinfo.email"],
    )
    await update.message.reply_text(f"请点击授权：{authorization_url}")


# --- Flask 路由处理 Google OAuth 回调 ---
@app.route("/oauth2callback")
def oauth2callback():
    code = request.args.get("code")
    if not code:
        return "缺少 code 参数", 400

    token_url, headers, body = client.prepare_token_request(
        GOOGLE_TOKEN_URI,
        authorization_response=request.url,
        redirect_url=OAUTH_REDIRECT_URL,
        code=code,
    )
    token_response = requests.post(token_url, headers=headers, data=body, auth=(GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET))
    client.parse_request_body_response(json.dumps(token_response.json()))
    return "授权成功 ✅ 请返回 Telegram"


# --- Telegram Bot 初始化函数 ---
async def run_bot():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))
    logger.info("🤖 Telegram Bot 已启动")
    await application.run_polling()


# --- 启动入口 ---
async def main():
    loop = asyncio.get_event_loop()

    # 同时运行 Flask + Telegram Bot
    bot_task = asyncio.create_task(run_bot())
    flask_task = asyncio.to_thread(app.run, host="0.0.0.0", port=PORT)

    await asyncio.gather(bot_task, flask_task)

if __name__ == "__main__":
    asyncio.run(main())
