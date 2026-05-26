"""
GET /api/cron
Called 5x per weekday by Vercel Cron.

Schedule (UTC → DC/London):
  12:00 → DC 08:00 / London 12:00  (core slot)
  14:00 → DC 10:00 / EU 14:00
  17:00 → DC 13:00 / EU 17:00
  21:00 → DC 17:00                  (core slot)
  00:00 → DC 20:00 (casual browsing)

Pipeline:
  RSS parse → dedup check → Supabase insert → Claude draft → Slack notify
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler
import json

from lib.rss_parser import parse_feed
from lib.supabase_client import article_exists, insert_article, insert_draft
from lib.claude_client import generate_draft
from lib.slack_notifier import notify_new_draft, notify_error


MAX_ARTICLES_PER_RUN = 2  # Vercel Free 티어 10초 제한 대응


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # ── CRON_SECRET 인증 ──────────────────────────────
        cron_secret = os.environ.get("CRON_SECRET", "")
        if cron_secret:
            auth = self.headers.get("Authorization", "")
            if auth != f"Bearer {cron_secret}":
                self._respond(401, {"error": "Unauthorized"})
                return

        try:
            result = run_pipeline()
            self._respond(200, result)
        except Exception as e:
            try:
                notify_error("Cron pipeline failed", str(e))
            except Exception:
                pass
            self._respond(500, {"status": "error", "message": str(e)})

    def _respond(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


def run_pipeline() -> dict:
    print("[cron] pipeline started")

    articles = parse_feed()
    new_count = 0
    draft_count = 0

    for article in articles:
        if new_count >= MAX_ARTICLES_PER_RUN:
            break

        rss_id = article["rss_id"]
        if article_exists(rss_id):
            continue

        article_id = insert_article(
            rss_id=rss_id,
            title=article["title"],
            url=article["url"],
            published=article.get("published"),
        )
        new_count += 1

        try:
            draft_text = generate_draft(
                url=article["url"],
                article_text=article.get("content", ""),
                lang=article.get("lang", "ko"),
            )
        except Exception as e:
            notify_error(f"Claude draft failed: {article['title']}", str(e))
            continue

        draft_id = insert_draft(
            article_id=article_id,
            draft_text=draft_text,
        )
        draft_count += 1

        try:
            notify_new_draft(
                title=article["title"],
                article_url=article["url"],
                draft_text=draft_text,
                draft_id=draft_id,
            )
        except Exception as e:
            print(f"[WARN] Slack 알림 실패: {e}")

    return {
        "status": "success",
        "new_articles": new_count,
        "drafts_created": draft_count,
    }
