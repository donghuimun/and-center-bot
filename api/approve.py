"""
POST /api/approve
승인 웹페이지에서 호출됩니다.

요청 바디:
  {
    "draft_id": "uuid",
    "action": "approve" | "reject",
    "edited_text": "수정된 텍스트 (선택)"
  }
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler
import json

from lib.supabase_client import get_draft_with_article, approve_draft, reject_draft, fail_draft
from lib.x_poster import post_tweet
from lib.slack_notifier import notify_posted, notify_rejected, notify_error


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._respond(400, {"status": "error", "message": "잘못된 요청 형식"})
            return

        draft_id = body.get("draft_id", "").strip()
        action = body.get("action", "").strip()
        edited_text = body.get("edited_text", "").strip() or None

        if not draft_id or action not in ("approve", "reject"):
            self._respond(400, {"status": "error", "message": "draft_id 또는 action 누락"})
            return

        try:
            result = handle_action(draft_id, action, edited_text)
            self._respond(200, result)
        except Exception as e:
            notify_error(f"승인 처리 실패 (draft_id={draft_id})", str(e))
            self._respond(500, {"status": "error", "message": str(e)})

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def _respond(self, status: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, format, *args):
        pass


def handle_action(draft_id: str, action: str, edited_text: str | None) -> dict:
    draft = get_draft_with_article(draft_id)
    if not draft:
        raise ValueError(f"draft_id를 찾을 수 없음: {draft_id}")

    if draft["status"] not in ("pending",):
        raise ValueError(f"이미 처리된 초안입니다 (status={draft['status']})")

    if action == "reject":
        reject_draft(draft_id)
        article_title = draft.get("articles", {}).get("title", "")
        try:
            notify_rejected(article_title)
        except Exception:
            pass
        return {"status": "success", "action": "rejected"}

    # action == "approve"
    final_text = edited_text or draft["draft_text"]

    try:
        tweet_url = post_tweet(final_text)
    except Exception as e:
        fail_draft(draft_id, str(e))
        raise RuntimeError(f"X 포스팅 실패: {e}")

    approve_draft(draft_id, tweet_url, edited_text)

    try:
        notify_posted(tweet_url, final_text)
    except Exception:
        pass

    return {"status": "success", "action": "approved", "tweet_url": tweet_url}
