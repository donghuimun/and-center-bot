import os
from datetime import datetime, timezone
from supabase import create_client, Client


_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
        _client = create_client(url, key)
    return _client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────────────────────
# articles
# ─────────────────────────────────────────

def article_exists(rss_id: str) -> bool:
    result = get_client().table("articles").select("id").eq("rss_id", rss_id).execute()
    return len(result.data) > 0


def _is_missing_image_url_error(error: Exception) -> bool:
    message = str(error)
    return (
        "PGRST204" in message
        and "image_url" in message
        and "articles" in message
    )


def insert_article(rss_id: str, title: str, url: str, published: str | None, image_url: str | None = None) -> str:
    payload = {
        "rss_id": rss_id,
        "title": title,
        "url": url,
        "published": published,
    }
    if image_url:
        payload["image_url"] = image_url

    try:
        result = get_client().table("articles").insert(payload).execute()
    except Exception as e:
        if not _is_missing_image_url_error(e):
            raise
        payload.pop("image_url", None)
        result = get_client().table("articles").insert(payload).execute()

    return result.data[0]["id"]


# ─────────────────────────────────────────
# drafts
# ─────────────────────────────────────────

def insert_draft(article_id: str, draft_text: str, hook_type: str | None = None) -> str:
    result = get_client().table("drafts").insert({
        "article_id": article_id,
        "draft_text": draft_text,
        "status": "pending",
        "hook_type": hook_type,
    }).execute()
    return result.data[0]["id"]


def get_draft_with_article(draft_id: str) -> dict | None:
    try:
        result = (
            get_client().table("drafts")
            .select("*, articles(title, url, image_url)")
            .eq("id", draft_id)
            .single()
            .execute()
        )
    except Exception as e:
        if not _is_missing_image_url_error(e):
            raise
        result = (
            get_client().table("drafts")
            .select("*, articles(title, url)")
            .eq("id", draft_id)
            .single()
            .execute()
        )
    return result.data


def claim_draft_for_posting(draft_id: str) -> bool:
    """pending → posting 원자적 전이. 성공하면 True (이 요청만 포스팅 진행 가능)."""
    result = (
        get_client().table("drafts")
        .update({"status": "posting"})
        .eq("id", draft_id)
        .eq("status", "pending")
        .execute()
    )
    return len(result.data) > 0


def reset_draft_to_pending(draft_id: str) -> None:
    """rate limit 등 일시 오류 시 재시도 가능하도록 되돌림."""
    get_client().table("drafts").update({
        "status": "pending",
        "error_message": None,
    }).eq("id", draft_id).execute()


def approve_draft(draft_id: str, posted_url: str, edited_text: str | None = None) -> None:
    payload: dict = {
        "status": "posted",
        "posted_url": posted_url,
        "approved_at": _now_iso(),
    }
    if edited_text:
        payload["edited_text"] = edited_text
    get_client().table("drafts").update(payload).eq("id", draft_id).execute()


def reject_draft(draft_id: str) -> None:
    get_client().table("drafts").update({"status": "rejected"}).eq("id", draft_id).execute()


def fail_draft(draft_id: str, reason: str) -> None:
    get_client().table("drafts").update({
        "status": "failed",
        "error_message": reason,
    }).eq("id", draft_id).execute()


# ─────────────────────────────────────────
# approval_logs
# ─────────────────────────────────────────

def log_approval(draft_id: str, action: str, notes: str | None = None) -> None:
    get_client().table("approval_logs").insert({
        "draft_id": draft_id,
        "action": action,
        "notes": notes,
    }).execute()
