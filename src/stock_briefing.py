#!/usr/bin/env python3
"""
A股盘前资讯 | 云端采集脚本（升级版）
数据源：东方财富/新浪财经/财联社/腾讯自选股
输出 Markdown 格式供微信推送
"""

import requests
import re
import json
from datetime import datetime, timedelta
import pytz

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


# ============== 工具函数 ==============

def _get(url, headers=None, timeout=10, encoding=None):
    """通用请求"""
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    if headers:
        default_headers.update(headers)
    try:
        resp = requests.get(url, headers=default_headers, timeout=timeout)
        if encoding:
            resp.encoding = encoding
        return resp
    except Exception:
        return None


def last_trading_day():
    """动态计算上一个交易日（跳过周末和节假日近似）"""
    today = datetime.now(BEIJING_TZ)
    d = today - timedelta(days=1)
    # 周六 -> 周五
    if d.weekday() == 5:
        d -= timedelta(days=1)
    # 周日 -> 周五
    elif d.weekday() == 6:
        d -= timedelta(days=2)
    return d


def last_trading_day_us():
    """美股上一交易日（通常比A股晚一天，考虑时差）"""
    today = datetime.now(BEIJING_TZ)
    d = today - timedelta(days=1)
    # 周六 -> 周四; 周日 -> 周五; 周一 -> 周五
    if d.weekday() == 5:
        d -= timedelta(days=1)
    elif d.weekday() == 6:
        d -= timedelta(days=2)
    elif d.weekday() == 0:
        d -= timedelta(days=3)
    return d


# ============== 一、美股行情 ==============

def fetch_us_market():
    """美股三大指数 + 热门中概"""
    codes = {
        ".DJI":  "道琼斯工业",
        ".IXIC": "纳斯达克综合",
        ".INX":  "标普500",
    }
    items = []
    for code, name in codes.items():
        try:
            url = f"https://qt.gtimg.cn/q={code}"
            resp = _get(url, encoding="gbk")
            if not resp or code not in resp.text:
                items.append(f"| {name} | — | — |")
                continue
            parts = resp.text.split("~")
            if len(parts) < 33:
                items.append(f"| {name} | — | — |")
                continue
            price = float(parts[3]) if parts[3].replace(".", "").replace("-", "").isdigit() else parts[3]
            chg = parts[32]
            try:
                chg_num = float(chg)
                arrow = "🔴" if chg_num >= 0 else "🟢"
                chg_str = f"{arrow} {chg}%"
            except ValueError:
                chg_str = chg + "%"
            items.append(f"| {name} | {price} | {chg_str} |")
        except Exception:
            items.append(f"| {name} | — | — |")
    return items


def fetch_us_cn_stocks():
    """热门中概股表现"""
    stocks = {
        "BABA": "阿里巴巴",
        "JD":   "京东",
        "PDD":  "拼多多",
        "BIDU": "百度",
        "NIO":  "蔚来",
    }
    items = []
    for code, name in stocks.items():
        try:
            url = f"https://qt.gtimg.cn/q=us{code}"
            resp = _get(url, encoding="gbk")
            if not resp or "us" + code not in resp.text:
                continue
            parts = resp.text.split("~")
            chg = parts[32] if len(parts) > 32 else "0"
            try:
                chg_num = float(chg)
                arrow = "🔴" if chg_num >= 0 else "🟢"
                chg_str = f"{arrow}{chg}%"
            except ValueError:
                chg_str = chg + "%"
            items.append(f"{name}: {chg_str}")
        except Exception:
            continue
    return items


# ============== 二、A股指数 ==============

def fetch_a_share_indices():
    codes = {
        "s_sh000001": "上证指数",
        "s_sz399001": "深证成指",
        "s_sz399006": "创业板指",
        "s_sh000688": "科创50",
    }
    items = []
    for code, name in codes.items():
        try:
            url = f"https://hq.sinajs.cn/list={code}"
            resp = _get(url, headers={"Referer": "https://finance.sina.com.cn"}, encoding="gbk")
            if not resp:
                items.append(f"| {name} | — | — | — |")
                continue
            parts = resp.text.split(",")
            if len(parts) < 5:
                items.append(f"| {name} | — | — | — |")
                continue
            price = float(parts[3])
            prev = float(parts[2])
            chg = round(price - prev, 2)
            chg_pct = round(chg / prev * 100, 2)
            sign = "+" if chg >= 0 else ""
            arrow = "🔴" if chg >= 0 else "🟢"
            items.append(f"| {name} | {price:.2f} | {sign}{chg} | {arrow} {sign}{chg_pct}% |")
        except Exception:
            items.append(f"| {name} | — | — | — |")
    return items


# ============== 三、板块 & 资金 ==============

def fetch_hot_sectors():
    """东方财富行业板块涨幅TOP5"""
    try:
        url = "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz=5&po=1&np=1&fields=f2,f3,f4,f14&fid=f3&fs=m:90+t:2&fltt=2"
        resp = _get(url)
        if not resp:
            return []
        data = resp.json()
        items = []
        for row in data.get("data", {}).get("diff", [])[:5]:
            name = row.get("f14", "")
            pct = row.get("f3", 0)
            arrow = "🔴" if pct >= 0 else "🟢"
            items.append(f"{name} {arrow}{pct}%")
        return items
    except Exception:
        return []


def fetch_north_flow():
    """北向资金净流入"""
    try:
        url = "https://push2.eastmoney.com/api/qt/kamt.kline/get?fields1=f1,f2,f3,f4&fields2=f51,f52,f53,f54&klt=101&lmt=1"
        resp = _get(url)
        if not resp:
            return None
        data = resp.json()
        rows = data.get("data", {}).get("klines", [])
        if rows:
            vals = rows[-1].split(",")
            net = float(vals[1]) if len(vals) > 1 else 0
            direction = "净流入" if net >= 0 else "净流出"
            arrow = "🔴" if net >= 0 else "🟢"
            return f"{arrow} {direction} {abs(net):.2f}亿"
    except Exception:
        pass
    return None


def fetch_market_stats():
    """涨跌家数统计"""
    try:
        url = "https://push2.eastmoney.com/api/qt/stock/get?secid=1.000001&fields=f170,f171,f104,f105,f106,f107"
        resp = _get(url)
        if not resp:
            return None
        d = resp.json().get("data", {})
        up = d.get("f104", 0)
        down = d.get("f106", 0)
        flat = d.get("f105", 0)
        return f"上涨 {up} 家 / 下跌 {down} 家 / 平盘 {flat} 家"
    except Exception:
        return None


# ============== 四、财经要闻（多源聚合）==============

def fetch_eastmoney_news():
    """东方财富快讯"""
    items = []
    try:
        url = "https://kuaixun.eastmoney.com/txt_440100000000.html"
        resp = _get(url)
        if not resp:
            return items
        titles = re.findall(r'<a[^>]*title="([^"]*)"[^>]*>', resp.text)
        seen = set()
        for t in titles[:20]:
            t = t.strip()
            if t and len(t) >= 10 and t not in seen and "图解" not in t:
                seen.add(t)
                items.append(t)
    except Exception:
        pass
    return items[:8]


def fetch_cls_news():
    """财联社电报"""
    items = []
    try:
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6"
        payload = {"type": "telegram", "page": 1, "rn": 10}
        headers = {"Content-Type": "application/json"}
        resp = requests.post(url, json=payload, headers={
            **headers, "User-Agent": "Mozilla/5.0"
        }, timeout=10)
        data = resp.json()
        for item in data.get("data", {}).get("roll_data", [])[:10]:
            title = item.get("title", "").strip()
            if title and len(title) >= 8:
                items.append(title)
    except Exception:
        pass
    return items[:5]


def fetch_sina_24h():
    """新浪财经24小时要闻"""
    items = []
    try:
        url = "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num=10&page=1"
        resp = _get(url)
        if not resp:
            return items
        data = resp.json()
        for item in data.get("result", {}).get("data", [])[:10]:
            title = item.get("title", "").strip()
            if title and len(title) >= 10:
                items.append(title)
    except Exception:
        pass
    return items[:5]


def aggregate_financial_news():
    """多源聚合去重"""
    all_news = []
    seen = set()

    def add_section(title, items):
        nonlocal all_news
        added = []
        for item in items:
            key = item[:20]
            if key not in seen:
                seen.add(key)
                added.append(item)
        if added:
            all_news.append((title, added))

    add_section("📰 财联社电报", fetch_cls_news())
    add_section("📊 东方财富快讯", fetch_eastmoney_news())
    add_section("🌐 新浪财经", fetch_sina_24h())
    return all_news


# ============== 五、大宗商品 & 汇率 ==============

def fetch_commodities():
    """大宗商品快照"""
    codes = {
        "CL00Y": "WTI原油",
        "GC00Y": "COMEX黄金",
        "HG00Y": "伦铜",
    }
    items = []
    for code, name in codes.items():
        try:
            url = f"https://qt.gtimg.cn/q={code}"
            resp = _get(url, encoding="gbk")
            if not resp or code not in resp.text:
                continue
            parts = resp.text.split("~")
            price = parts[3] if len(parts) > 3 else "—"
            chg = parts[32] if len(parts) > 32 else "0"
            try:
                chg_num = float(chg)
                arrow = "🔴" if chg_num >= 0 else "🟢"
            except ValueError:
                arrow = ""
            items.append(f"| {name} | {price} | {arrow} {chg}% |")
        except Exception:
            continue
    return items


def fetch_usd_cny():
    """美元兑人民币"""
    try:
        url = "https://qt.gtimg.cn/q=USDCNY"
        resp = _get(url, encoding="gbk")
        if not resp or "USDCNY" not in resp.text:
            return None
        parts = resp.text.split("~")
        rate = parts[3] if len(parts) > 3 else "—"
        chg = parts[32] if len(parts) > 32 else "0"
        chg_num = float(chg) if chg.replace("-", "").replace(".", "").isdigit() else 0
        arrow = "🔴" if chg_num >= 0 else "🟢"
        return f"1 USD = {rate} CNY ({arrow}{chg}%)"
    except Exception:
        return None


# ============== 主生成函数 ==============

def generate_stock_briefing():
    today = datetime.now(BEIJING_TZ)
    date_str = today.strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    us_day = last_trading_day_us()
    a_day = last_trading_day()

    lines = [
        f"# 📈 A股盘前资讯 | {date_str}（{weekday}）",
        "",
    ]

    # ---- 一、隔夜外盘 ----
    lines.append(f"## 一、隔夜外盘（{us_day.strftime('%m月%d日')} 美股收盘）")
    lines.append("")
    lines.append("| 指数 | 收盘价 | 涨跌幅 |")
    lines.append("|------|--------|--------|")
    lines.extend(fetch_us_market())

    cn_stocks = fetch_us_cn_stocks()
    if cn_stocks:
        lines.append("")
        lines.append("**热门中概股**:  " + "  ".join(cn_stocks))

    # ---- 二、A股上一交易日 ----
    lines.append("")
    lines.append(f"## 二、A股回顾（{a_day.strftime('%m月%d日')} 收盘）")
    lines.append("")
    lines.append("| 指数 | 收盘价 | 涨跌 | 涨跌幅 |")
    lines.append("|------|--------|------|--------|")
    lines.extend(fetch_a_share_indices())

    # 涨跌统计
    stats = fetch_market_stats()
    if stats:
        lines.append("")
        lines.append(f"> 📊 {stats}")

    # 北向资金
    north = fetch_north_flow()
    if north:
        lines.append(f"> 💰 北向资金: {north}")

    # 领涨板块
    sectors = fetch_hot_sectors()
    if sectors:
        lines.append(f"> 🔥 领涨板块: {'  '.join(sectors)}")

    # ---- 三、财经要闻 ----
    lines.append("")
    lines.append("## 三、财经要闻")
    lines.append("")

    news_sections = aggregate_financial_news()
    if news_sections:
        for section_title, items in news_sections:
            lines.append(f"**{section_title}**")
            for i, item in enumerate(items, 1):
                lines.append(f"{i}. {item}")
            lines.append("")
    else:
        lines.append("> 暂无最新财经要闻")

    # ---- 四、大宗商品 & 汇率 ----
    lines.append("## 四、大宗商品 & 汇率")
    lines.append("")
    lines.append("| 品种 | 价格 | 涨跌幅 |")
    lines.append("|------|------|--------|")
    commodities = fetch_commodities()
    if commodities:
        lines.extend(commodities)
    else:
        lines.append("| 数据获取中 | — | — |")

    fx = fetch_usd_cny()
    if fx:
        lines.append("")
        lines.append(f"> 💱 {fx}")

    # ---- 尾部 ----
    lines += [
        "",
        "---",
        f"*推送时间: {today.strftime('%Y-%m-%d %H:%M')} (UTC+8) | 云端自动推送*",
        "*数据来源: 东方财富 / 新浪财经 / 财联社 / 腾讯自选股*",
        "*⚠️ 本内容由程序自动生成，仅供参考，不构成投资建议*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_stock_briefing())
