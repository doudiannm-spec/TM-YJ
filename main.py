import logging
from datetime import datetime
from telegram import Update, Message
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# 配置日志
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 存储邀请统计：{日期: {邀请人ID: {被邀请人ID: 次数}}}
stats = {}  

def start(update: Update, context: CallbackContext) -> None:
    """处理 /start 命令"""
    update.message.reply_text('机器人已启动，正在统计群内邀请信息...')

def handle_message(update: Update, context: CallbackContext) -> None:
    """处理群聊消息，提取邀请信息"""
    message = update.message
    chat = message.chat

    # 仅处理群聊消息
    if chat.type not in ['group', 'supergroup']:
        return

    text = message.text
    if not text:
        return

    # 解析消息格式：平台:xxx 来源:xxx 项目:xxx 账号:xxx 邀请码:xxx
    lines = text.split('\n')
    info = {}
    for line in lines:
        if ':' in line:
            key, val = line.split(':', 1)
            info[key.strip()] = val.strip()

    # 检查必要字段是否存在
    required_fields = ['平台', '来源', '项目', '账号', '邀请码']
    if not all(field in info for field in required_fields):
        return

    inviter = message.from_user  # 邀请人（发送消息的用户）
    invitee = info['账号']       # 被邀请人（消息中的账号）

    # 获取今天的日期（格式：YYYY-MM-DD）
    today = datetime.now().strftime('%Y-%m-%d')

    # 初始化统计结构
    if today not in stats:
        stats[today] = {}
    if inviter.id not in stats[today]:
        stats[today][inviter.id] = {}

    # 统计邀请次数（若同一邀请人多次邀请同一人，可累加）
    if invitee in stats[today][inviter.id]:
        stats[today][inviter.id][invitee] += 1
    else:
        stats[today][inviter.id][invitee] = 1

    # 回复确认信息
    reply = f"✅ 已统计邀请：\n邀请人：{inviter.full_name} (ID: {inviter.id})\n被邀请人：{invitee}\n平台：{info['平台']}\n来源：{info['来源']}\n项目：{info['项目']}\n邀请码：{info['邀请码']}"
    message.reply_text(reply)

def get_stats(update: Update, context: CallbackContext) -> None:
    """处理 /stats 命令，查询当天统计"""
    today = datetime.now().strftime('%Y-%m-%d')
    if today not in stats or not stats[today]:
        update.message.reply_text(f"📊 今日（{today}）暂无邀请统计")
        return

    # 构造统计信息
    result = f"📊 今日（{today}）邀请统计：\n"
    for inviter_id, invitees in stats[today].items():
        inviter = context.bot.get_chat_member(update.message.chat_id, inviter_id).user
        result += f"\n👤 邀请人：{inviter.full_name} (ID: {inviter_id})\n"
        for invitee, count in invitees.items():
            result += f"  - 被邀请人：{invitee}，次数：{count}\n"

    update.message.reply_text(result)

def error_handler(update: Update, context: CallbackContext) -> None:
    """错误"""
   处理 logger.error(f"更新 {update} 引发错误 {context.error}")

def main() -> None:
    """启动机器人"""
    # 从环境变量获取Telegram Bot Token（建议用环境变量，避免硬编码）
    token = "YOUR_BOT_TOKEN"  # 替换为你的Bot Token（从@BotFather获取）
    updater = Updater(token)
    dispatcher = updater.dispatcher

    # 注册命令和消息处理器
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("stats", get_stats))
    dispatcher.add_handler(MessageHandler(Filters.text & Filters.chat_type.groups, handle_message))
    dispatcher.add_error_handler(error_handler)

    # 启动机器人
    updater.start_polling()
    logger.info("机器人已启动，开始监听消息...")
    updater.idle()

if __name__ == '__main__':
    main()
