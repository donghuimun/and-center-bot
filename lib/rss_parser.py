import feedparser
import requests
import re
from datetime import datetime
from typing import Optional
from email.utils import parsedate_to_datetime


def _first_image(html: str) -> Optional[str]:
    """본문 HTML에서 첫 번째 이미지 URL 추출 (X 포스팅 첨부용)."""
    m = re.search(r'<img[^>]+src="(https?://[^"]+)"', html)
    return m.group(1) if m else None


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"&amp;", "&", text)
    text = re.sub(r"&lt;", "<", text)
    text = re.sub(r"&gt;", ">", text)
    text = re.sub(r"&nbsp;", " ", text)
    text = re.sub(r"&#\d+;", "", text)
    text = re.sub(r"&[a-z]+;", "", text)
    return re.sub(r" {2,}", " ", text).strip()


FEEDS = [
    {"url": "https://www.dailynk.com/english/feed", "lang": "en"},
    {"url": "https://www.dailynk.com/feed", "lang": "ko"},
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; ANDCenterBot/1.0; +https://x-bot-iota.vercel.app)"
}


def _parse_single_feed(feed_url: str, lang: str) -> list[dict]:
    response = requests.get(feed_url, headers=HEADERS, timeout=15, allow_redirects=True)
    response.raise_for_status()
    feed = feedparser.parse(response.content)

    if feed.bozo and not feed.entries:
        raise RuntimeError(f"RSS 파싱 실패 ({feed_url}): {feed.bozo_exception}")

    articles = []
    for entry in feed.entries:
        rss_id = entry.get("id") or entry.get("link", "")
        title = entry.get("title", "")
        url = entry.get("link", "")

        raw = ""
        if hasattr(entry, "content") and entry.content:
            raw = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            raw = entry.summary
        content = _strip_html(raw)
        image_url = _first_image(raw)

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
                "image_url": image_url,
                "lang": lang,
            })

    return articles


def parse_feed() -> list[dict]:
    """
    Parse DailyNK Korean and English RSS feeds and return combined article list.
    Returns: [{"rss_id", "title", "url", "published", "content", "lang"}, ...]
    English feed first (preferred), then Korean.
    """
    articles = []
    errors = []

    for feed_config in FEEDS:
        try:
            results = _parse_single_feed(feed_config["url"], feed_config["lang"])
            articles.extend(results)
        except Exception as e:
            errors.append(f"{feed_config['lang']}: {e}")
            print(f"[rss] feed error ({feed_config['lang']}): {e}")

    if not articles and errors:
        raise RuntimeError(f"All feeds failed: {'; '.join(errors)}")

    return articles
