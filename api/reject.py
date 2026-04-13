"""
POST /api/reject
승인 웹페이지 거절 버튼에서 호출됩니다.

요청 바디:
  { "draft_id": "uuid" }
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler
import json

from lib.supabase_client import get_draft_with_article, reject_draft
from lib.slack_notifier import notify_rejected


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body = json.loads(self.rfile.read(length))
        except Exception:
            self._respond(400, {"status": "error", "message": "잘못된 요청 형식"})
            return

        draft_id = body.get("draft_id", "").strip()
        if not draft_id:
            self._respond(400, {"status": "error", "message": "draft_id 누락"})
            return

        try:
            draft = get_draft_with_article(draft_id)
            if not draft:
                self._respond(404, {"status": "error", "message": "초안을 찾을 수 없음"})
                return

            reject_draft(draft_id)
            article_title = draft.get("articles", {}).get("title", "")
            try:
                notify_rejected(article_title)
            except Exception:
                pass
            self._respond(200, {"status": "success"})
        except Exception as e:
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
