#!/usr/bin/env python3
"""
A股盘前资讯 | 云端采集脚本
使用东方财富等公有API，采集美股行情、A股财经要闻、行业消息
输出 Markdown 格式供微信推送
"""

import requests
import json
import re
from datetime import datetime, timedelta
import pytz

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def fetch_us_market():
    """获取美股三大指数最新行情"""
    codes = {
        ".DJI": "道琼斯",
        ".IXIC": "纳斯达克",
        ".INX": "标普500",
    }
    result = []
    for code, name in codes.items():
        try:
            url = f"https://qt.gtimg.cn/q={code}"
            resp = requests.get(url, timeout=10)
            resp.encoding = "gbk"
            data = resp.text
            if code not in data:
                continue
            parts = data.split("~")
            if len(parts) < 32:
                continue
            price = parts[3]
            change_pct = parts[32]
            result.append(f"| {name} | {price} | {change_pct}% |")
        except Exception as e:
            result.append(f"| {name} | 获取失败 | — |")
    return result


def fetch_a_share_indices():
    """A股主要指数"""
    codes = {
        "s_sh000001": "上证指数",
        "s_sz399001": "深证成指",
        "s_sz399006": "创业板指",
        "s_sh000688": "科创50",
    }
    result = []
    for code, name in codes.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            headers = {"Referer": "https://finance.sina.com.cn"}
            resp = requests.get(url, headers=headers, timeout=10)
            resp.encoding = "gbk"
            data = resp.text
            parts = data.split(",")
            if len(parts) < 4:
                continue
            price = parts[3]
            change = round(float(price) - float(parts[2]), 2)
            change_pct = round((float(price) - float(parts[2])) / float(parts[2]) * 100, 2)
            sign = "+" if change >= 0 else ""
            result.append(f"| {name} | {price} | {sign}{change} | {sign}{change_pct}% |")
        except Exception:
            result.append(f"| {name} | — | — | — |")
    return result


def fetch_financial_news():
    """抓取财经要闻（从东方财富快讯）"""
    headlines = []
    try:
        url = "https://kuaixun.eastmoney.com/txt_440100000000.html"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        resp.encoding = "utf-8"
        text = resp.text
        titles = re.findall(r'<a[^>]*title="([^"]*)"[^>]*>', text)
        seen = set()
        for t in titles[:15]:
            t = t.strip()
            if t and len(t) > 8 and t not in seen:
                seen.add(t)
                headlines.append(t)
    except Exception:
        pass
    return headlines[:8]


def generate_stock_briefing():
    """生成 A 股盘前资讯"""
    today = datetime.now(BEIJING_TZ)
    date_str = today.strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    lines = [
        f"# A股盘前资讯 | {date_str}（{weekday}）",
        "",
        "## 一、美股上周五收盘",
        "",
        "| 指数 | 收盘价 | 涨跌幅 |",
        "|------|--------|--------|",
    ]
    lines.extend(fetch_us_market())

    lines += [
        "",
        "## 二、A股主要指数（上一交易日）",
        "",
        "| 指数 | 收盘价 | 涨跌 | 涨跌幅 |",
        "|------|--------|------|--------|",
    ]
    lines.extend(fetch_a_share_indices())

    headlines = fetch_financial_news()
    if headlines:
        lines += [
            "",
            "## 三、财经要闻速览",
            "",
        ]
        for i, h in enumerate(headlines, 1):
            lines.append(f"{i}. {h}")

    lines += [
        "",
        "## 四、今日关注",
        "",
        "- **新股申购**: 查看当日新股日历",
        "- **停复牌**: 关注银河微电(688689) 今日复牌",
        "- **重要事件**: 北京太空算力大会 6/29-6/30 举办",
        "- **基金停牌**: 纳指科技ETF(159509)、全球芯片LOF(501225) 10:30前停牌",
        "",
        "---",
        f"*推送时间: {today.strftime('%Y-%m-%d %H:%M')} (UTC+8)*",
        "*数据来源: 腾讯自选股/东方财富/新浪财经*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_stock_briefing())
