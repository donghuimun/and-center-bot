import os
from supabase import create_client, Client


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_ANON_KEY"]
    return create_client(url, key)


# ─────────────────────────────────────────
# articles
# ─────────────────────────────────────────

def article_exists(rss_id: str) -> bool:
    """rss_id로 중복 기사 여부 확인"""
    client = get_client()
    result = client.table("articles").select("id").eq("rss_id", rss_id).execute()
    return len(result.data) > 0


def insert_article(rss_id: str, title: str, url: str, published: str | None) -> str:
    """articles 테이블에 삽입, 생성된 id 반환"""
    client = get_client()
    result = client.table("articles").insert({
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
    """drafts 테이블에 초안 삽입, 생성된 id 반환"""
    client = get_client()
    result = client.table("drafts").insert({
        "article_id": article_id,
        "draft_text": draft_text,
        "status": "pending",
    }).execute()
    return result.data[0]["id"]


def get_draft_with_article(draft_id: str) -> dict | None:
    """draft + 연관 article 정보 반환"""
    client = get_client()
    result = (
        client.table("drafts")
        .select("*, articles(title, url)")
        .eq("id", draft_id)
        .single()
        .execute()
    )
    return result.data


def approve_draft(draft_id: str, posted_url: str, edited_text: str | None = None) -> None:
    client = get_client()
    payload: dict = {
        "status": "approved",
        "posted_url": posted_url,
        "approved_at": "now()",
    }
    if edited_text:
        payload["edited_text"] = edited_text
    client.table("drafts").update(payload).eq("id", draft_id).execute()


def reject_draft(draft_id: str) -> None:
    client = get_client()
    client.table("drafts").update({"status": "rejected"}).eq("id", draft_id).execute()


def fail_draft(draft_id: str, reason: str) -> None:
    client = get_client()
    client.table("drafts").update({
        "status": "failed",
        "edited_text": reason,
    }).eq("id", draft_id).execute()
