import os
import re
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("请在 .env 文件中设置 BOT_TOKEN")

# 正则表达式匹配拉人格式
PATTERN = re.compile(
    r"前台:\s*(?P<front_desk>.+?)\s*\n"
    r"平台:\s*(?P<platform>.+?)\s*\n"
    r"来源:\s*(?P<source>.+?)\s*\n"
    r"项目:\s*(?P<project>.+?)\s*\n"
    r"账号:\s*(?P<account>.+?)\s*\n"
    r"(邀请码:\s*(?P<invite_code>.+?))?",
    re.DOTALL
)

# 内存存储统计数据（生产环境建议替换为数据库）
stats = {}  # { "user_id": { "date": count } }
user_names = {}  # { "user_id": "username/full_name" }

def get_today():
    return datetime.now().strftime("%Y-%m-%d")

async def track_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    text = update.message.text
    match = PATTERN.search(text)
    if not match:
        return
    
    user = update.message.from_user
    user_id = user.id
    today = get_today()
    
    # 记录用户名
    if user_id not in user_names:
        user_names[user_id] = user.full_name or user.username or str(user_id)
    
    # 更新统计
    if user_id not in stats:
        stats[user_id] = {}
    if today not in stats[user_id]:
        stats[user_id][today] = 0
    stats[user_id][today] += 1
    
    await update.message.reply_text(f"✅ 已记录 {user_names[user_id]} 的拉人记录！今日累计：{stats[user_id][today]}")

async def stats_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = get_today()
    reply = f"📊 今日({today}) 拉人统计：\n\n"
    total = 0
    for user_id, data in stats.items():
        count = data.get(today, 0)
        if count > 0:
            reply += f"• {user_names.get(user_id, '未知用户')}: {count} 人\n"
            total += count
    reply += f"\n总计：{total} 人"
    await update.message.reply_text(reply)

async def stats_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ 用法：/stats_user @用户名 或 /stats_user 用户ID")
        return
    target = context.args[0]
    target_id = None
    target_name = target
    
    if target.startswith("@"):
        for uid, name in user_names.items():
            if name == target[1:]:
                target_id = uid
                break
    else:
        try:
            target_id = int(target)
        except ValueError:
            pass
    
    if not target_id or target_id not in stats:
        await update.message.reply_text("❌ 未找到该用户的统计数据")
        return
    
    reply = f"📊 {user_names.get(target_id, target_name)} 的拉人统计：\n\n"
    total = 0
    for date, count in sorted(stats[target_id].items()):
        reply += f"• {date}: {count} 人\n"
        total += count
    reply += f"\n总计：{total} 人"
    await update.message.reply_text(reply)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 我是拉人统计机器人！\n"
        "请按以下格式发送拉人信息：\n"
        "```\n前台:\n平台:\n来源:\n项目:\n账号:\n邀请码:\n```\n"
        "可用命令：\n"
        "/stats_today - 查看今日统计\n"
        "/stats_user @用户名 - 查看指定用户统计"
    )

def main():
    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats_today", stats_today))
    application.add_handler(CommandHandler("stats_user", stats_user))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, track_message))
    application.run_polling()

if __name__ == "__main__":
    main()
