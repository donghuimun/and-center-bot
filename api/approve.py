"""
POST /api/approve
승인 웹페이지에서 호출됩니다.

요청 바디:
  {
    "draft_id": "uuid",
    "action": "approve" | "reject",
    "edited_text": "수정된 텍스트 (선택)"
  }

인증:
  Authorization: Bearer <APPROVE_PASSWORD>
  APPROVE_PASSWORD 미설정 시 인증 건너뜀 (개발 환경).
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from http.server import BaseHTTPRequestHandler
import json

from lib.supabase_client import get_draft_with_article, approve_draft, reject_draft, fail_draft, log_approval
from lib.x_poster import post_tweet, XPostError
from lib.slack_notifier import notify_posted, notify_rejected, notify_error

MAX_TWEET_CHARS = 280


def _verify_auth(headers) -> bool:
    """
    Authorization: Bearer <password> 헤더를 APPROVE_PASSWORD 환경변수와 비교합니다.
    APPROVE_PASSWORD 미설정이면 항상 통과 (개발 환경 편의).
    """
    required = os.environ.get("APPROVE_PASSWORD", "")
    if not required:
        return True

    auth_header = headers.get("Authorization") or headers.get("authorization") or ""
    if not auth_header.startswith("Bearer "):
        return False

    token = auth_header[len("Bearer "):].strip()
    return token == required


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # ── 인증 검사 ──────────────────────────────────────
        if not _verify_auth(self.headers):
            self._respond(401, {"status": "error", "message": "인증 실패: 올바른 Authorization 헤더가 필요합니다."})
            return

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
        except ValueError as e:
            self._respond(400, {"status": "error", "message": str(e)})
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
        origin = os.environ.get("NEXT_PUBLIC_APP_URL", "")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

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
        log_approval(draft_id, "rejected")
        article_title = (draft.get("articles") or {}).get("title", "")
        try:
            notify_rejected(article_title)
        except Exception:
            pass
        return {"status": "success", "action": "rejected"}

    # action == "approve"
    final_text = edited_text or draft["draft_text"]

    # ── 서버사이드 글자수 검증 ──────────────────────────────
    if len(final_text) > MAX_TWEET_CHARS:
        raise ValueError(
            f"포스트가 {MAX_TWEET_CHARS}자를 초과합니다 (현재 {len(final_text)}자). "
            "수정 후 다시 시도해 주세요."
        )

    try:
        tweet_url = post_tweet(final_text)
    except XPostError as e:
        fail_draft(draft_id, str(e))
        hint = " (rate_limit)" if e.error_code == 429 else ""
        raise RuntimeError(f"X 포스팅 실패{hint}: {e}")
    except Exception as e:
        fail_draft(draft_id, str(e))
        raise RuntimeError(f"X 포스팅 실패: {e}")

    approve_draft(draft_id, tweet_url, edited_text)
    log_approval(draft_id, "edited" if edited_text else "approved")

    try:
        notify_posted(tweet_url, final_text)
    except Exception:
        pass

    return {"status": "success", "action": "approved", "tweet_url": tweet_url}
