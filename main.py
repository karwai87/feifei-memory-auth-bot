import os
import logging
from flask import Flask, redirect, request, session
from flask_session import Session
from google_auth_oauthlib.flow import Flow
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, Application
from dotenv import load_dotenv
from threading import Thread

# 加载环境变量
# 加载 .env
load_dotenv()

# 2. 写入 client_secret.json 文件（带 try 保护）
try:
    client_secret_json = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET_JSON")
    if client_secret_json:
        with open("client_secret.json", "w") as f:
            json.dump(json.loads(client_secret_json), f)
except Exception as e:
    print(f"[写入 client_secret.json 失败]：{e}")

# 3. 配置日志（可选）
logging.basicConfig(level=logging.INFO)

# 4. 初始化 Flask 和后续逻辑

# Flask 初始化
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "defaultsecret")
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# 常量设置
BOT_TOKEN = os.getenv("BOT_TOKEN")
CLIENT_SECRETS_FILE = "client_secret.json"
SCOPES = ["https://www.googleapis.com/auth/drive.file"]
REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URL")  # 直接从 env 读取
bot_user_tokens = {}

# Flask 路由 - 授权回调
@app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get("state")
        if state != session.get("state"):
            return "❌ 状态不一致，可能是 CSRF 攻击"

        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI,
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
                "scopes": credentials.scopes,
            }
            return "✅ 授权成功！你可以关闭这个页面了"
        return "❌ 无法识别用户 ID，授权失败"
    except Exception as e:
        return f"❌ 授权失败：{e}"

# Telegram /start 指令
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI妃 OAuth 系统，发送 /auth 开始授权流程。")

# Telegram /auth 指令
async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
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

        await update.message.reply_text("请点击下方按钮完成授权：", reply_markup=reply_markup)
    except Exception as e:
        await update.message.reply_text(f"⚠️ 授权流程异常：{e}")

# Telegram Bot 启动逻辑（独立线程）
def start_telegram_bot():
    app_bot = ApplicationBuilder().token(BOT_TOKEN).build()
    app_bot.add_handler(CommandHandler("start", start))
    app_bot.add_handler(CommandHandler("auth", auth))
    app_bot.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        url_path="/webhook",
        webhook_url=f"{REDIRECT_URI}".replace("/oauth2callback", "/webhook")
    )

# 启动 Flask + Telegram Bot
if __name__ == "__main__":
    Thread(target=start_telegram_bot).start()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
