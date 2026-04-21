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


def insert_article(rss_id: str, title: str, url: str, published: str | None) -> str:
    result = get_client().table("articles").insert({
        "rss_id": rss_id,
        "title": title,
        "url": url,
        "published": published,
    }).execute()
    return result.data[0]["id"]


# ─────────────────────────────────────────
# drafts
# ─────────────────────────────────────────

def insert_draft(article_id: str, draft_text: str) -> str:
    result = get_client().table("drafts").insert({
        "article_id": article_id,
        "draft_text": draft_text,
        "status": "pending",
    }).execute()
    return result.data[0]["id"]


def get_draft_with_article(draft_id: str) -> dict | None:
    result = (
        get_client().table("drafts")
        .select("*, articles(title, url)")
        .eq("id", draft_id)
        .single()
        .execute()
    )
    return result.data


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
