import logging
import os
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from flask import Flask, request, redirect, url_for

# ---------------------- Telegram Bot 配置 ----------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # 从 Railway 环境变量获取
OAUTH_CLIENT_SECRET_FILE = 'client_secret.json'
OAUTH_SCOPES = ['https://www.googleapis.com/auth/drive.metadata.readonly']  # 替换为您需要的 Google API 权限
OAUTH_REDIRECT_URI = os.environ.get("OAUTH_REDIRECT_URL")  # 从 Railway 环境变量获取

# 新增：全局变量存储 Telegram 用户ID 和 OAuth 状态
user_oauth_map = {}

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(f"你好 {user.first_name}！发送 /auth 进行 Google 授权。")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true'
        )

        telegram_user_id = update.effective_user.id
        user_oauth_map[state] = telegram_user_id  # 存起来！
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("授权 Google", url=authorization_url)]])
        await update.message.reply_text("请点击以下链接授权 Google 服务：", reply_markup=markup)

    except Exception as e:
        logger.error(f"❌ 生成授权 URL 失败: {e}")
        await update.message.reply_text(f"❌ 授权失败，请稍后再试。错误信息：{e}")

def run_telegram_bot():
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("auth", auth))

    logger.info("Telegram Bot is running...")
    application.run_polling()

# ---------------------- Flask Web 服务器配置 ----------------------
app = Flask(__name__)

@app.route("/oauth2callback")
def oauth2callback():
    try:
        state = request.args.get('state')
        telegram_user_id = user_oauth_map.get(state)  # 从内存 map 里拿出 ID！

        flow = Flow.from_client_secrets_file(
            OAUTH_CLIENT_SECRET_FILE,
            scopes=OAUTH_SCOPES,
            state=state,
            redirect_uri=OAUTH_REDIRECT_URI
        )
        flow.fetch_token(authorization_response=request.url)
        credentials = flow.credentials

        if telegram_user_id:
            logger.info(f"✅ 用户 {telegram_user_id} 授权成功")
            return f"""
                <h2>✅ 授权成功！</h2>
                <p>Telegram 用户 ID：{telegram_user_id}</p>
                <p>你现在可以回到 Telegram 使用 AI 妃功能。</p>
            """
        else:
            return "⚠️ 授权成功，但未找到关联的 Telegram 用户。"

    except Exception as e:
        logger.error(f"❌ OAuth 回调失败: {e}")
        return f"❌ 回调失败: {e}"

if __name__ == '__main__':
    # 启动 Telegram Bot (在一个独立的线程中)
    import threading
    telegram_thread = threading.Thread(target=run_telegram_bot)
    telegram_thread.daemon = True
    telegram_thread.start()

    # 启动 Flask Web 服务器
    port = int(os.environ.get('PORT', 8080))
    logger.info(f"Flask server starting on port {port}")
    app.run(host='0.0.0.0', port=port)
