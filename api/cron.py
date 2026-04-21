"""
GET /api/cron
Vercel Cron에 의해 평일 5회 호출됩니다.

스케줄 (UTC → KST):
  00:00 → 09:00  한국 오전
  02:00 → 11:00  한국 오전
  05:00 → 14:00  한국 오후
  07:00 → 16:00  한국 오후
  09:00 → 18:00  한국 저녁

파이프라인:
  RSS 파싱 → 중복 체크 → Supabase 저장 → Claude 초안 → Slack 알림
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
                notify_error("Cron 파이프라인 전체 실패", str(e))
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
            )
        except Exception as e:
            notify_error(f"Claude 초안 생성 실패: {article['title']}", str(e))
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
