"""
GET /api/cron
Called 4x per weekday by Vercel Cron.

Schedule (UTC → KST / US ET):
  Sun-Thu 23:10 → Mon-Fri 08:10 KST (한국 아침 뉴스 사이클)
  Mon-Fri 03:40 → Mon-Fri 12:40 KST
  Mon-Fri 11:00 → Mon-Fri 20:00 KST = 07:00 ET (미국 동부 아침)
  Mon-Fri 13:30 → Mon-Fri 22:30 KST = 09:30 ET (미국 동부 오전)

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
        # 프로덕션에서 미설정 시 차단 (fail-closed) — Vercel 환경변수에 CRON_SECRET 필수
        cron_secret = os.environ.get("CRON_SECRET", "")
        if not cron_secret:
            if os.environ.get("VERCEL_ENV") == "production":
                self._respond(401, {"error": "CRON_SECRET not configured"})
                return
        else:
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

        new_count += 1

        # 초안 생성 성공 후에만 article 저장 — 실패 시 다음 런에서 재시도됨
        try:
            draft_text, hook_type = generate_draft(
                url=article["url"],
                title=article["title"],
                article_text=article.get("content", ""),
                lang=article.get("lang", "ko"),
            )
        except Exception as e:
            notify_error(f"Claude draft failed: {article['title']}", str(e))
            continue

        article_id = insert_article(
            rss_id=rss_id,
            title=article["title"],
            url=article["url"],
            published=article.get("published"),
            image_url=article.get("image_url"),
        )

        draft_id = insert_draft(
            article_id=article_id,
            draft_text=draft_text,
            hook_type=hook_type,
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
