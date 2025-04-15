import os
import logging
from flask import Flask, request, session, redirect, url_for
from flask_session import Session
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
FLASK_SECRET = os.getenv("FLASK_SECRET", "your_flask_secret")
PORT = int(os.getenv("PORT", 8080))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # 例如: https://your-app-name.railway.app/webhook
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "telegram_webhook_secret")
OAUTH_CLIENT_SECRET_FILE = 'client_secret.json'  # 确保此文件在项目根目录下
OAUTH_SCOPES = ["https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/spreadsheets"]
OAUTH_REDIRECT_URI = os.getenv("OAUTH_REDIRECT_URI")  # 例如: https://your-app-name.railway.app/oauth2callback

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 初始化 Flask 应用
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config['SESSION_TYPE'] = 'filesystem'  # 建议生产环境使用更持久化的存储如 Redis
Session(app)

# 初始化 Telegram Bot Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# ==== Telegram Bot Handlers ====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃系统！请使用 /auth 授权 Google 服务。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = Flow.from_client_secrets_file(
        OAUTH_CLIENT_SECRET_FILE,
        scopes=OAUTH_SCOPES,
        redirect_uri=OAUTH_REDIRECT_URI
    )
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    session['state'] = state
    session['telegram_user_id'] = update.effective_user.id
    markup = InlineKeyboardMarkup([[InlineKeyboardButton("授权 Google", url=authorization_url)]])
    await update.message.reply_text("请点击以下链接授权 Google 服务：", reply_markup=markup)

# 将 Handlers 添加到 Telegram Bot Application
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("auth", auth))

# ==== Flask Webhook Endpoint for Telegram ====
@app.route("/webhook", methods=["POST"])
async def webhook():
    if request.headers.get('X-Telegram-Bot-Api-Secret-Token') == WEBHOOK_SECRET:
        update = Update.de_json(request.get_json(), application.bot)
        await application.process_update(update)
        return "OK", 200
    else:
        logger.warning("Received invalid webhook secret token")
        return "Unauthorized", 401

# ==== Flask Google OAuth Callback ====
@app.route("/oauth2callback")
def oauth2callback():
    if 'error' in request.args:
        return f"授权失败: {request.args['error']}"

    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            state=session['state'],
            redirect_uri=OAUTH_REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials
        telegram_user_id = session.get('telegram_user_id')

        if telegram_user_id:
            logger.info(f"用户 {telegram_user_id} 成功授权 Google Drive/Sheets。")
            # 在这里你可以将 credentials 保存到你的用户数据中，例如数据库
            session['google_credentials'] = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes
            }
            return f"授权成功！你的 Telegram 用户 ID 是 {telegram_user_id}。"
        else:
            return "授权成功，但无法关联 Telegram 用户。"

    except Exception as e:
        logger.error(f"OAuth 2.0 回调处理失败: {e}")
        return f"OAuth 2.0 回调处理失败: {e}"

# ==== Health Check Endpoint for Railway ====
@app.route("/")
def health_check():
    return "AI 妃系统运行正常", 200

if __name__ == "__main__":
    # 在 Railway 上部署时，需要设置 Webhook
    if WEBHOOK_URL:
        application.run_webhook(listen="0.0.0.0",
                                port=PORT,
                                webhook_url=WEBHOOK_URL,
                                secret_token=WEBHOOK_SECRET)
        # Flask 仍然需要运行，以便处理 OAuth 回调和健康检查
        app.run(host="0.0.0.0", port=PORT, use_reloader=False)
    else:
        logger.warning("WEBHOOK_URL 未设置，将使用 polling 模式 (仅适用于本地开发)")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
