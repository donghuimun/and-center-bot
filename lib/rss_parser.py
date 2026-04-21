import feedparser
import requests
from datetime import datetime
from typing import Optional
from email.utils import parsedate_to_datetime


RSS_URL = "https://www.dailynk.com/feed"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ANDCenterBot/1.0; +https://x-bot-iota.vercel.app)"
}


def parse_feed() -> list[dict]:
    """
    데일리NK RSS 피드를 파싱하여 기사 목록을 반환합니다.
    반환값: [{"rss_id", "title", "url", "published", "content"}, ...]
    """
    response = requests.get(RSS_URL, headers=HEADERS, timeout=15, allow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"RSS 파싱 실패: {feed.bozo_exception}")

    articles = []
    for entry in feed.entries:
        rss_id = entry.get("id") or entry.get("link", "")
        title = entry.get("title", "")
        url = entry.get("link", "")

        # 본문 추출 (summary 또는 content)
        content = ""
        if hasattr(entry, "content") and entry.content:
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary

        # 발행일 파싱
        published: Optional[datetime] = None
        if hasattr(entry, "published"):
            try:
                published = parsedate_to_datetime(entry.published)
            except Exception:
                published = None

        if rss_id and title and url:
            articles.append({
                "rss_id": rss_id,
                "title": title,
                "url": url,
                "published": published.isoformat() if published else None,
                "content": content,
            })

    return articles
