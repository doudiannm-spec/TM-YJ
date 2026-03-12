import re

# ... 前面原有代码保持不变 ...

def auto_add_from_format(update: Update, context: CallbackContext):
    """
    检测用户是否发送了指定格式的消息，如果是则自动录入系统
    格式:
    前台:
    平台:
    来源:
    项目:
    账号:
    邀请码:
    """
    text = update.message.text.strip()
    
    # 正则匹配 6 行，每行 key: value
    pattern = r"^前台:\s*(.+)\n平台:\s*(.+)\n来源:\s*(.+)\n项目:\s*(.+)\n账号:\s*(.+)\n邀请码:\s*(.+)$"
    match = re.match(pattern, text, re.MULTILINE)
    
    if not match:
        return  # 格式不对，不处理
    
    # 解析出字段
    front_desk = match.group(1).strip()
    platform = match.group(2).strip()
    source = match.group(3).strip()
    project = match.group(4).strip()
    account = match.group(5).strip()
    invite_code = match.group(6).strip()
    
    # 构造记录
    record = {
        "front_desk": front_desk,
        "platform": platform,
        "source": source,
        "project": project,
        "account": account,
        "invite_code": invite_code,
        "user": update.effective_user.full_name,
        "user_id": update.effective_user.id,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    # 加载现有数据
    data = load_data()
    today = get_today()
    
    if today not in data:
        data[today] = {"entries": []}
    elif "entries" not in data[today]:
        data[today]["entries"] = []
    
    # 添加记录
    data[today]["entries"].append(record)
    save_data(data)
    
    # 回复用户
    update.message.reply_text(
        f"✅ 已成功录入系统：\n"
        f"前台: {front_desk}\n"
        f"平台: {platform}\n"
        f"来源: {source}\n"
        f"项目: {project}\n"
        f"账号: {account}\n"
        f"邀请码: {invite_code}\n"
        f"提交人: {record['user']}"
    )

# ... 中间原有代码保持不变 ...

def main():
    config = load_config()
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("请设置 TELEGRAM_BOT_TOKEN 环境变量")
        return
    
    updater = Updater(token, use_context=True)
    dp = updater.dispatcher
    
    # 原有命令
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats_command))
    dp.add_handler(CommandHandler("yesterday", yesterday_command))
    dp.add_handler(CommandHandler("user_stats", user_stats_command))
    dp.add_handler(MessageHandler(Filters.status_update.new_chat_members, handle_new_chat_members))
    
    # 👇 新增：自动加人格式检测
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, auto_add_from_format))
    
    dp.add_error_handler(error_handler)
    
    updater.start_polling()
    logger.info("机器人已启动")
    updater.idle()
