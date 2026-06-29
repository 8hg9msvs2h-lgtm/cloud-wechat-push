#!/usr/bin/env python3
"""
主入口 — 根据参数执行对应推送任务
用法: python main.py stock    # A股盘前资讯
      python main.py ai       # AI新闻简报
      python main.py all      # 两个都推送
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from datetime import datetime
import pytz

beijing_tz = pytz.timezone("Asia/Shanghai")
today_str = datetime.now(beijing_tz).strftime("%Y年%m月%d日")


def run_stock():
    from stock_briefing import generate_stock_briefing
    from push import send_wechat

    content = generate_stock_briefing()
    title = f"A股盘前资讯 | {today_str}"
    return send_wechat(title, content)


def run_ai():
    from ai_news import generate_ai_news
    from push import send_wechat

    content = generate_ai_news()
    title = f"AI新闻简报 | {today_str}"
    return send_wechat(title, content)


if __name__ == "__main__":
    task = sys.argv[1] if len(sys.argv) > 1 else "all"

    ok = True
    if task in ("stock", "all"):
        print("\n=== 执行: A股盘前资讯 ===")
        if not run_stock():
            ok = False

    if task in ("ai", "all"):
        print("\n=== 执行: AI新闻简报 ===")
        if not run_ai():
            ok = False

    sys.exit(0 if ok else 1)
