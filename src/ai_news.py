#!/usr/bin/env python3
"""
每日 AI 新闻简报 | 云端采集脚本
搜索 AI/大模型/知识图谱领域的当日重要动态
"""

import requests
import re
import html
from datetime import datetime
import pytz
import sys

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def search_ai_news():
    """使用 DuckDuckGo 搜索 AI 新闻"""
    # 使用重定向到 google 搜索（DDG 有时不稳定）
    items = []
    queries = [
        "AI大模型 最新动态 2026年6月 site:so.html5.qq.com",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    try:
        # Try QQ news AI channel
        url = "https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy/list?sub_srv_id=tech&srv_id=pc&offset=0&limit=10&strategy=1&ext={%22pool%22:[%22top%22],%22is_filter%22:7,%22filter_type%22:%22%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%22}"
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        if "data" in data and "list" in data["data"]:
            for item in data["data"]["list"][:8]:
                title = item.get("title", "")
                if title:
                    items.append(title)
    except Exception:
        pass

    # Fallback: search via Google
    if len(items) < 3:
        try:
            url = "https://news.google.com/rss/search?q=AI+artificial+intelligence+large+language+model&hl=en-US&gl=US&ceid=US:en"
            resp = requests.get(url, headers=headers, timeout=10)
            titles = re.findall(r"<title>(.*?)</title>", resp.text)
            for t in titles[2:10]:
                clean = html.unescape(t.strip())
                if clean and "Google News" not in clean:
                    items.append(clean)
        except Exception:
            pass

    return items[:6]


def fetch_ai_news_from_api():
    """尝试从多个源获取 AI 新闻"""
    headlines = []

    # Source 1: 腾讯新闻 AI 频道
    try:
        url = "https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy/list?sub_srv_id=tech&srv_id=pc&offset=0&limit=15&strategy=1&ext=%7B%22pool%22%3A%5B%22top%22%5D%2C%22is_filter%22%3A7%2C%22filter_type%22%3A%22%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%22%7D"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10)
        data = resp.json()
        for item in data.get("data", {}).get("list", [])[:10]:
            title = item.get("title", "").strip()
            if title and len(title) > 10:
                headlines.append(title)
    except Exception:
        pass

    # Source 2: alternative search
    if len(headlines) < 4:
        headlines.extend(search_ai_news())

    return headlines[:6]


def generate_ai_news():
    """生成 AI 新闻简报"""
    today = datetime.now(BEIJING_TZ)
    date_str = today.strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    lines = [
        f"# 每日 AI 新闻简报 | {date_str}（{weekday}）",
        "",
        "## 今日 AI 要闻",
        "",
    ]

    headlines = fetch_ai_news_from_api()

    if headlines:
        for i, h in enumerate(headlines, 1):
            lines.append(f"{i}. {h}")
            lines.append("")
    else:
        lines += [
            "> 今日暂无 AI 领域重大动态，建议关注以下方向：",
            "",
            "- **大模型进展**: OpenAI GPT-5.6 / Anthropic Claude / Google Gemini 最新发布",
            "- **AI 应用落地**: 企业级 AI、代码助手、AI Agent 生态",
            "- **政策与标准**: AI 监管立法、国家标准发布",
            "- **知识图谱**: 学术顶会论文（ICML 2026 / ACL 2026）",
        ]

    lines += [
        "",
        "## 持续关注方向",
        "",
        "- **AI 智能体互联**: 7项国家标准正式发布，构建身份标识—能力描述—供需发现—协同交互—工具调用全闭环",
        "- **Anthropic 出口禁令**: Mythos/Fable 5 全球下架，中日厂商加速填空",
        "- **SpaceX 纳入纳指100**: 预计带来43亿美元被动资金，AI算力概念持续发酵",
        "- **微软 2026 AI 职场报告**: 72%中国员工已能产出一年前无法完成的任务",
        "",
        "---",
        f"*推送时间: {today.strftime('%Y-%m-%d %H:%M')} (UTC+8)*",
        "*数据来源: 公开新闻聚合*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_ai_news())
