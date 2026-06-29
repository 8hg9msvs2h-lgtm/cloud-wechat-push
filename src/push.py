#!/usr/bin/env python3
"""
WeChat 推送模块 — 通过 PushPlus 推送消息到微信

使用前需要:
1. 访问 https://www.pushplus.plus/ 用微信扫码注册
2. 在「发送消息」→「一对一发送」页面获取你的 Token
3. 将 Token 设置为环境变量 PUSHPLUS_TOKEN 或 GitHub Secret
"""

import os
import sys
import requests


def send_wechat(title, content, template="markdown"):
    """
    通过 PushPlus 发送微信消息

    Args:
        title: 消息标题
        content: 消息内容 (支持 markdown/html/txt)
        template: 消息模板类型 (markdown/html/txt)

    Returns:
        bool: 是否发送成功
    """
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token:
        print("错误: 未设置 PUSHPLUS_TOKEN 环境变量")
        print("请访问 https://www.pushplus.plus/ 注册获取 Token")
        sys.exit(1)

    url = "http://www.pushplus.plus/send"

    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": template,
    }

    try:
        resp = requests.post(url, json=payload, timeout=15)
        result = resp.json()
        if result.get("code") == 200:
            print(f"推送成功: {title}")
            return True
        else:
            print(f"推送失败: {result.get('msg', '未知错误')}")
            print(f"详情: {result}")
            return False
    except Exception as e:
        print(f"推送异常: {e}")
        return False


if __name__ == "__main__":
    title = sys.argv[1] if len(sys.argv) > 1 else "测试消息"
    content = sys.argv[2] if len(sys.argv) > 2 else "这是一条来自云端推送的测试消息"
    send_wechat(title, content)
