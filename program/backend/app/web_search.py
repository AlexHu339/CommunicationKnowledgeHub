from __future__ import annotations

import html
import re
from typing import Any
from urllib.parse import urlencode, urlparse
from xml.etree import ElementTree

import httpx

from .ai import AiError

_TAG_RE = re.compile(r"<[^>]+>")


def _plain(value: str, limit: int) -> str:
    return html.unescape(_TAG_RE.sub(" ", value or "")).strip()[:limit]


async def search_public_web(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Low-frequency public web search used when a provider has no native search tool."""
    query = query.strip()[:500]
    if not query:
        raise AiError("联网搜索词为空")
    url = "https://www.bing.com/search?" + urlencode({"q": query, "format": "rss", "setlang": "zh-Hans"})
    headers = {"User-Agent": "CommunicationKnowledgeHub/1.0 (+local learning assistant)"}
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
        root = ElementTree.fromstring(response.content)
    except Exception as exc:
        raise AiError(f"公开网页检索失败：{type(exc).__name__}") from exc

    results: list[dict[str, Any]] = []
    for item in root.findall(".//item"):
        link = (item.findtext("link") or "").strip()
        parsed = urlparse(link)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            continue
        results.append({
            "title": _plain(item.findtext("title") or "", 200),
            "url": link,
            "snippet": _plain(item.findtext("description") or "", 600),
        })
        if len(results) >= max(1, min(limit, 8)):
            break
    if not results:
        raise AiError("公开网页检索没有返回可用结果")
    return results


def search_context(results: list[dict[str, Any]]) -> str:
    lines = [
        "以下是网站后端刚刚检索到的公开网页结果。请结合用户问题作答，标注所依据的来源；"
        "网页摘要可能不完整，不确定时必须说明，不要把摘要当作完整原文。"
    ]
    for index, result in enumerate(results, 1):
        lines.append(f"[{index}] {result['title']}\n网址：{result['url']}\n摘要：{result['snippet']}")
    return "\n\n".join(lines)
