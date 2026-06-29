#!/usr/bin/env python3
"""
每日 AI 新闻简报 | 云端采集脚本（升级版）
多源聚合：机器之心/量子位/36氪/GoogleNews/腾讯科技
"""

import requests
import re
import html
from datetime import datetime
import pytz

BEIJING_TZ = pytz.timezone("Asia/Shanghai")


def _get(url, headers=None, timeout=12):
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    }
    if headers:
        default_headers.update(headers)
    try:
        resp = requests.get(url, headers=default_headers, timeout=timeout)
        return resp
    except Exception:
        return None


def _rss_parse(url, limit=6):
    """通用 RSS 解析"""
    items = []
    try:
        resp = _get(url)
        if not resp or resp.status_code != 200:
            return items
        # <item>...</item>  or <entry>...</entry>
        text = resp.text
        # Try RSS 2.0
        item_blocks = re.findall(r"<item>(.*?)</item>", text, re.DOTALL)
        for block in item_blocks[:limit]:
            title_m = re.search(r"<title><!\[CDATA\[(.*?)\]\]></title>", block)
            if not title_m:
                title_m = re.search(r"<title>(.*?)</title>", block)
            if title_m:
                title = html.unescape(title_m.group(1).strip())
                if title and len(title) > 8:
                    items.append(title)
        if items:
            return items
        # Try Atom feed
        entry_blocks = re.findall(r"<entry>(.*?)</entry>", text, re.DOTALL)
        for block in entry_blocks[:limit]:
            title_m = re.search(r"<title[^>]*>(.*?)</title>", block)
            if title_m:
                title = html.unescape(title_m.group(1).strip())
                if title and len(title) > 8:
                    items.append(title)
    except Exception:
        pass
    return items


# ============== 数据源 ==============

def fetch_jiqizhixin():
    """机器之心 RSS"""
    return _rss_parse("https://feeds.feedburner.com/jiqizhixin", limit=5)


def fetch_liangziwei():
    """量子位 RSS"""
    return _rss_parse("https://www.qbitai.com/feed", limit=5)


def fetch_36kr_ai():
    """36氪 AI频道"""
    items = []
    try:
        url = "https://gateway.36kr.com/api/mis/nav/home/nav/ai-prompt"
        resp = _get(url)
        if not resp:
            return items
        data = resp.json()
        for item in data.get("data", {}).get("itemList", [])[:6]:
            title = _extract_text(item.get("templateMaterial", {}).get("widgetTitle", ""))
            if title and len(title) > 8:
                items.append(title)
    except Exception:
        pass
    return items


def fetch_google_ai():
    """Google News AI 话题"""
    items = []
    try:
        url = "https://news.google.com/rss/search?q=artificial+intelligence+LLM+AI+model&hl=zh-CN&gl=CN&ceid=CN:zh-Hans"
        resp = _get(url)
        if not resp:
            return items
        titles = re.findall(r"<title>(.*?)</title>", resp.text)
        for t in titles[2:10]:
            clean = html.unescape(t.strip())
            parts = clean.rsplit(" - ", 1)
            title = parts[0] if len(parts) > 1 else clean
            if title and "Google News" not in title and len(title) > 10:
                items.append(title)
    except Exception:
        pass
    return items[:5]


def fetch_tencent_tech():
    """腾讯科技频道"""
    items = []
    try:
        url = "https://i.news.qq.com/trpc.qqnews_web.kv_srv.kv_srv_http_proxy/list?sub_srv_id=tech&srv_id=pc&offset=0&limit=15&strategy=1&ext=%7B%22pool%22%3A%5B%22top%22%5D%2C%22is_filter%22%3A7%2C%22filter_type%22%3A%22%E4%BA%BA%E5%B7%A5%E6%99%BA%E8%83%BD%22%7D"
        resp = _get(url)
        if not resp:
            return items
        data = resp.json()
        for item in data.get("data", {}).get("list", [])[:8]:
            title = item.get("title", "").strip()
            if title and len(title) > 10:
                items.append(title)
    except Exception:
        pass
    return items


def _extract_text(mixed):
    """36kr format: extract plain text from mixed array"""
    if isinstance(mixed, str):
        return mixed.strip()
    if isinstance(mixed, list):
        return "".join(p.get("text", "") if isinstance(p, dict) else str(p) for p in mixed).strip()
    return str(mixed)


# ============== 主函数 ==============

def generate_ai_news():
    today = datetime.now(BEIJING_TZ)
    date_str = today.strftime("%Y年%m月%d日")
    weekday = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][today.weekday()]

    lines = [
        f"# 🤖 AI 新闻简报 | {date_str}（{weekday}）",
        "",
    ]

    # 聚合所有来源
    all_sources = [
        ("机器之心", fetch_jiqizhixin()),
        ("量子位",   fetch_liangziwei()),
        ("36氪 AI",  fetch_36kr_ai()),
        ("腾讯科技",  fetch_tencent_tech()),
        ("Google News", fetch_google_ai()),
    ]

    idx = 1
    total_items = 0
    seen = set()
    source_lines = []

    for source_name, items in all_sources:
        if not items:
            continue
        added = []
        for item in items:
            # 去重（用前30个字符作为key）
            key = re.sub(r"\s+", "", item)[:30]
            if key not in seen and len(item) >= 8:
                seen.add(key)
                added.append(item)
                total_items += 1
        if added:
            source_lines.append((source_name, added))

    if source_lines:
        for source_name, items in source_lines:
            lines.append(f"**📌 {source_name}**")
            for item in items:
                lines.append(f"{idx}. {item}")
                idx += 1
            lines.append("")

    # 如果没有获取到任何新闻
    if total_items == 0:
        lines += [
            "> 今日各源数据获取异常，请稍后查看。",
            "",
            "### 日常关注方向",
            "",
            "- **大模型前沿**: OpenAI / Anthropic / Google / DeepSeek / 智谱 等最新发布",
            "- **AI 应用落地**: 企业级 AI、AI Agent、多模态、AI 搜索",
            "- **政策与标准**: AI 监管立法、国家标准、数据安全",
            "- **知识图谱**: ICML 2027 / ACL 2027 / NeurIPS 论文",
            "- **算力与芯片**: NVIDIA / 国产GPU / 算力基建",
        ]

    # ---- 尾部 ----
    lines += [
        "---",
        f"*推送时间: {today.strftime('%Y-%m-%d %H:%M')} (UTC+8) | 云端自动推送*",
        f"*数据来源: 机器之心 / 量子位 / 36氪 / 腾讯科技 / Google News*",
        "*⚠️ 本内容由程序自动生成，仅供参考*",
    ]

    return "\n".join(lines)


if __name__ == "__main__":
    print(generate_ai_news())
