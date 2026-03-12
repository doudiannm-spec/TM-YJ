import os
import json
from datetime import datetime, date
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Bot, ParseMode

# ================== 配置参数 ==================
BOT_TOKEN = os.getenv("BOT_TOKEN")  # 从 GitHub Secrets 读取
CHAT_ID = os.getenv("CHAT_ID")      # 你的私聊 Chat ID（接收统计）
DATA_FILE = "data.json"             # 存储拉人数据的文件
TODAY = str(date.today())           # 今日日期（如 2024-09-15）

# ================== 数据处理函数 ==================
def load_data():
    """加载历史数据（拉人记录）"""
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}  # 空数据

def save_data(data):
    """保存数据到文件"""
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

def get_user_pulls(name):
    """获取用户今日拉人总数"""
    data = load_data()
    # 初始化今日数据
    if TODAY not in data:
        data[TODAY] = {}
    # 初始化用户数据
    if name not in data[TODAY]:
        data[TODAY][name] = 0
    return data[TODAY][name]

def add_pull(name):
    """增加用户今日拉人数"""
    data = load_data()
    if TODAY not in data:
        data[TODAY] = {}
    if name not in data[TODAY]:
        data[TODAY][name] = 0
    data[TODAY][name] += 1
    save_data(data)
    return data[TODAY][name]

# ================== 机器人命令处理 ==================
def start(update, context):
    """/start 命令：欢迎语"""
    update.message.reply_text(
        "👋 拉人统计机器人已启动！\n"
        "请在群内发送拉人信息（前台:、平台:、来源:、项目:、账号:、邀请码:），我会自动统计。\n"
        "私聊我发送 `/查询 红豆`，可查看某人今日拉人数量。"
    )

def handle_group_message(update, context):
    """处理群内拉人信息（仅统计指定格式）"""
    msg = update.message.text
    # 检查消息是否包含6个关键字段（前台:、平台:、来源:、项目:、账号:、邀请码:）
    required_fields = ["前台:", "平台:", "来源:", "项目:", "账号:", "邀请码:"]
    if all(field in msg for field in required_fields):
        # 提取姓名（从“前台:XXX”中解析，假设格式为“前台:红豆”）
        name = msg.split("前台:")[1].split("\n")[0].strip()
        # 增加拉人计数
        total = add_pull(name)
        # 回复确认
        update.message.reply_text(f"✅ 已记录：{name} 今日拉人 +1（累计：{total}）")

def query_user(update, context):
    """/查询 姓名：私聊查询某人今日拉人数量"""
    if update.message.chat.type != "private":  # 仅私聊可用
        return
    args = context.args
    if not args:
        update.message.reply_text("❌ 请输入姓名，例如：/查询 红豆")
        return
    name = " ".join(args)
    total = get_user_pulls(name)
    update.message.reply_text(f"📊 {name} 今日（{TODAY}）拉人数量：{total}")

# ================== 主程序 ==================
def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # 注册命令
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("查询", query_user))
    # 注册群消息处理（仅过滤拉人格式的消息）
    dp.add_handler(MessageHandler(Filtersxt &.te Filters.group, handle_group_message))

    # 启动机器人
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
