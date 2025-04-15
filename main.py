### Railway 上 Telegram Bot + Google OAuth 部署问题分析总结

#### 🧠 问题背景
- 项目基于 python-telegram-bot v20+ 和 Flask 实现
- Railway 部署 Telegram Bot，同时整合 Google OAuth 流程
- 出现 Bot 无回应、服务崩溃等问题

---

### ❗ 主要问题来源

#### 1. Webhook / Polling 冲突
- polling 与 webhook 互斥，未正确释放 webhook 导致 polling 无法获取更新

#### 2. run_polling / run_webhook 阻塞主线程
- Flask 和 Bot 共用线程导致冲突
- run_polling / run_webhook 均为阻塞函数，Flask run() 也会阻塞

#### 3. asyncio 与 Thread 冲突
- PTB v20 使用 asyncio，但 Thread 无事件循环，导致 RuntimeError

#### 4. Railway 端口限制
- Railway 只开放 $PORT，一个服务若同时监听多个端口将失败
- run_webhook 和 Flask 默认分别监听端口，冲突

---

### ✅ 推荐解决方案结构

#### ✅ 改用 Flask 统一接收 Webhook + OAuth 回调

```
main.py
├── /webhook         # 接收 Telegram 推送的 JSON
├── /oauth2callback  # OAuth 授权回调
└── /health          # Railway 保活健康检查
```

---

### ✅ 新版 main.py（Webhook + OAuth）

```python
import os
import logging
from flask import Flask, request, session
from flask_session import Session
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from google_auth_oauthlib.flow import Flow
from dotenv import load_dotenv
import telegram
import asyncio

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
FLASK_SECRET = os.getenv("FLASK_SECRET")
OAUTH_REDIRECT_URL = os.getenv("OAUTH_REDIRECT_URL")
PORT = int(os.getenv("PORT", 8080))

# Flask
app = Flask(__name__)
app.secret_key = FLASK_SECRET
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Telegram Application
application = ApplicationBuilder().token(BOT_TOKEN).build()

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("欢迎使用 AI 妃授权系统，输入 /auth 开始授权")

async def auth(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session["telegram_user_id"] = user_id

    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=OAUTH_REDIRECT_URL
    )
    url, state = flow.authorization_url(access_type='offline', include_granted_scopes='true', prompt='consent')
    session["state"] = state

    button = telegram.InlineKeyboardButton("点击授权", url=url)
    markup = telegram.InlineKeyboardMarkup([[button]])
    await update.message.reply_text("请点击按钮完成授权：", reply_markup=markup)

application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("auth", auth))

# Webhook 接收
@app.route("/webhook", methods=["POST"])
async def telegram_webhook():
    if request.is_json:
        update = telegram.Update.de_json(request.get_json(), application.bot)
        await application.process_update(update)
    return "ok"

# OAuth 回调
@app.route("/oauth2callback")
def oauth2callback():
    flow = Flow.from_client_secrets_file(
        "client_secret.json",
        scopes=["https://www.googleapis.com/auth/drive.file"],
        redirect_uri=OAUTH_REDIRECT_URL
    )
    flow.fetch_token(authorization_response=request.url)
    creds = flow.credentials
    user_id = session.get("telegram_user_id")
    return f"✅ 授权成功，欢迎用户 {user_id}"

# 健康检查
@app.route("/health")
def health():
    return {"status": "ok"}, 200

# 启动 Flask
if __name__ == '__main__':
    # 设置 Webhook
    asyncio.run(application.bot.set_webhook(url=WEBHOOK_URL))
    app.run(host="0.0.0.0", port=PORT)
```

---

### ✅ requirements.txt
```
Flask==2.3.2
Flask-Session==0.4.0
python-telegram-bot[webhooks]==20.6
python-dotenv==1.0.0
google-auth-oauthlib==1.0.0
google-api-python-client
google-auth-httplib2
pytz
```

---

### 🧠 关键记忆（记录入 AI妃记忆系统）

```
关键词：Railway / Telegram Bot / Flask / OAuth / Webhook / Polling / PTB v20
问题类型：启动失败 / Bot 无回应 / Webhook 不工作 / RuntimeError / asyncio 线程冲突
解决方法：Flask 接管 Webhook，PTB 通过 Application.process_update() 接收
经验总结：run_polling / run_webhook 阻塞，Web 服务整合需统一入口；使用 Flask 异步接收更灵活
```

