import os
import json
import re
from datetime import datetime
from threading import Thread
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
import uvicorn

# ===================== 核心配置 =====================
# 从环境变量读取Token，安全无泄露
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
VALID_GROUPS = ["组1", "组2", "组3", "组4"]
DATA_PATH = "data.json"
COMMISSION_RATE = 0.01  # 1%提成
DEDUCT_RATE = 0.05      # 5%佣金扣除
NET_RATE = COMMISSION_RATE * (1 - DEDUCT_RATE)  # 0.95%实发比例

# ===================== 数据操作工具 =====================
def load_data():
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"records": [], "total_commission": 0.0, "net_salary": 0.0, "total_income": 0.0}

def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ===================== 消息解析 =====================
def parse_bill(text: str):
    # 支持新格式：组1/10000+10000+10000/天明
    pattern_new = r"^(组[1-4])\/([\d+]+)\/(.+)$"
    match_new = re.match(pattern_new, text.strip())
    if match_new:
        group, amount_str, user = match_new.groups()
        # 拆分金额并累加
        amounts = list(map(float, amount_str.split("+")))
        total_amount = sum(amounts)
        return {
            "group": group,
            "type": "+",
            "amount": total_amount,
            "operator": user,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    # 兼容旧格式：组1+10000+天明 / 组2-500+李四
    pattern_old = r"^(组[1-4])([+-])(\d+\.?\d*)\+(.+)$"
    match_old = re.match(pattern_old, text.strip())
    if match_old:
        group, typ, amount, user = match_old.groups()
        amount = float(amount)
        return {
            "group": group,
            "type": typ,
            "amount": amount,
            "operator": user,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
    
    return None

# ===================== Telegram机器人逻辑 =====================
def start(update: Update, context: CallbackContext):
    msg = (
        "📊 团队记账机器人已启动\n"
        "支持格式：\n"
        "1. 多笔叠加收入：组X/金额+金额+.../入款人  例：组1/10000+5000/天明\n"
        "2. 单笔收入：组X+金额+入款人  例：组1+10000+天明\n"
        "3. 支出记录：组X-金额+入款人  例：组2-500+李四\n\n"
        "指令列表：\n"
        "/start - 查看使用说明\n"
        "/status - 查看全局统计数据\n"
        "/total - 查看累计总入账金额\n"
        "/group - 查看各小组明细统计\n"
        "/clear - 清空所有记录（慎用）"
    )
    update.message.reply_text(msg)

def add_record(update: Update, context: CallbackContext):
    text = update.message.text
    result = parse_bill(text)
    if not result:
        update.message.reply_text("❌ 格式错误！请使用支持的记账格式")
        return

    data = load_data()
    add_commission = 0.0
    add_net = 0.0
    add_income = 0.0

    if result["type"] == "+":
        raw_amount = result["amount"]
        add_commission = raw_amount * COMMISSION_RATE
        add_net = raw_amount * NET_RATE
        add_income = raw_amount
    else:
        raw_amount = -result["amount"]
        add_commission = -raw_amount * COMMISSION_RATE
        add_net = -raw_amount * NET_RATE

    record = {
        **result,
        "this_commission": round(add_commission, 2),
        "this_net_salary": round(add_net, 2)
    }
    data["records"].append(record)
    data["total_commission"] = round(data["total_commission"] + add_commission, 2)
    data["net_salary"] = round(data["net_salary"] + add_net, 2)
    data["total_income"] = round(data["total_income"] + add_income, 2)

    save_data(data)

    reply = (
        f"✅ 记账成功！\n"
        f"组别：{result['group']}\n"
        f"金额：{result['amount']:.2f}\n"
        f"操作人：{result['operator']}\n"
        f"本次提成：{add_commission:.2f}\n"
        f"本次实发：{add_net:.2f}\n\n"
        f"总入账金额：{data['total_income']:.2f}\n"
        f"累计实发工资：{data['net_salary']:.2f}"
    )
    update.message.reply_text(reply)

def get_status(update: Update, context: CallbackContext):
    data = load_data()
    msg = (
        "📈 当前全局统计\n"
        f"总入账金额：{data['total_income']:.2f} 元\n"
        f"实发工资（扣5%佣金）：{data['net_salary']:.2f} 元"
    )
    update.message.reply_text(msg)

def get_total_income(update: Update, context: CallbackContext):
    data = load_data()
    msg = (
        "💰 总入账统计\n"
        f"所有收入记录累计：{data['total_income']:.2f} 元"
    )
    update.message.reply_text(msg)

def clear_data(update: Update, context: CallbackContext):
    default_data = {"records": [], "total_commission": 0.0, "net_salary": 0.0, "total_income": 0.0}
    save_data(default_data)
    update.message.reply_text("🗑️ 所有记录已清空！")

# 新增：按组别统计功能
def get_group_stats(update: Update, context: CallbackContext):
    data = load_data()
    records = data["records"]
    
    # 初始化每个组的统计数据
    group_stats = {
        "组1": {"income": 0.0, "commission": 0.0, "net": 0.0},
        "组2": {"income": 0.0, "commission": 0.0, "net": 0.0},
        "组3": {"income": 0.0, "commission": 0.0, "net": 0.0},
        "组4": {"income": 0.0, "commission": 0.0, "net": 0.0}
    }
    
    # 遍历所有记录，按组汇总计算
    for r in records:
        group = r["group"]
        if r["type"] == "+":
            group_stats[group]["income"] += r["amount"]
            group_stats[group]["commission"] += r["this_commission"]
            group_stats[group]["net"] += r["this_net_salary"]
        else:
            group_stats[group]["income"] -= r["amount"]
            group_stats[group]["commission"] -= r["this_commission"]
            group_stats[group]["net"] -= r["this_net_salary"]
    
    # 生成统计消息
    msg = "📊 各小组入账与工资统计\n\n"
    for group, stats in group_stats.items():
        msg += (
            f"【{group}】\n"
            f"总入账：{stats['income']:.2f} 元\n"
            f"累计提成：{stats['commission']:.2f} 元\n"
            f"累计实发：{stats['net']:.2f} 元\n\n"
        )
    update.message.reply_text(msg)

# ===================== FastAPI网页账单 =====================
app = FastAPI(title="记账账单看板")

@app.get("/", response_class=HTMLResponse)
def bill_page():
    data = load_data()
    records = data["records"]
    html = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>团队记账账单</title>
        <style>
            body{{font-family: Arial; max-width: 1200px; margin: 0 auto; padding: 20px;}}
            .title{{text-align: center; color: #2c3e50;}}
            .stats{{background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;}}
            table{{width: 100%; border-collapse: collapse; margin-top: 20px;}}
            th,td{{border:1px solid #ddd; padding:10px; text-align:center;}}
            th{{background: #3498db; color:white;}}
            tr:nth-child(even){{background: #f8f9fa;}}
        </style>
    </head>
    <body>
        <h1 class="title">团队记账与工资统计看板</h1>
        <div class="stats">
            <h3>统计总览</h3>
            <p>累计总入账：{data['total_income']:.2f} 元</p>
            <p>累计总提成：{data['total_commission']:.2f} 元</p>
            <p>累计实发工资：{data['net_salary']:.2f} 元</p>
        </div>
        <table>
            <tr>
                <th>时间</th><th>组别</th><th>类型</th><th>金额</th><th>操作人</th><th>本次提成</th><th>本次实发</th>
            </tr>
    """
    for r in records:
        html += f"""
            <tr>
                <td>{r['time']}</td>
                <td>{r['group']}</td>
                <td>{'收入' if r['type']=='+' else '支出'}</td>
                <td>{r['amount']:.2f}</td>
                <td>{r['operator']}</td>
                <td>{r['this_commission']:.2f}</td>
                <td>{r['this_net_salary']:.2f}</td>
            </tr>
        """
    html += """
        </table>
    </body>
    </html>
    """
    return html

# ===================== 多线程启动服务 =====================
def run_bot():
    updater = Updater(BOT_TOKEN)
    dp = updater.dispatcher
    # 注册所有命令
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("status", get_status))
    dp.add_handler(CommandHandler("total", get_total_income))
    dp.add_handler(CommandHandler("clear", clear_data))
    dp.add_handler(CommandHandler("group", get_group_stats)) # 注册分组统计命令
    # 注册普通消息处理器
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, add_record))
    updater.start_polling()
    updater.idle()

def run_web():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    t1 = Thread(target=run_bot)
    t2 = Thread(target=run_web)
    t1.start()
    t2.start()
