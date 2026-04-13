import os
import httpx


def _get_webhook_url() -> str:
    return os.environ["SLACK_WEBHOOK_URL"]


def _post(payload: dict) -> None:
    response = httpx.post(_get_webhook_url(), json=payload, timeout=10)
    response.raise_for_status()


def notify_new_draft(
    title: str,
    article_url: str,
    draft_text: str,
    draft_id: str,
) -> None:
    """새 초안 생성 알림 (승인 링크 포함)"""
    app_url = os.environ.get("NEXT_PUBLIC_APP_URL", "https://your-app.vercel.app")
    password = os.environ.get("APPROVE_PASSWORD", "")
    approve_url = f"{app_url}/approve/{draft_id}?password={password}"

    payload = {
        "text": "📰 새 기사 감지 — AND센터 X 포스팅 승인 요청",
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📰 새 기사 감지"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*제목:*\n{title}"},
                    {"type": "mrkdwn", "text": f"*원문 링크:*\n{article_url}"},
                ],
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✏️ *Claude 초안:*\n```\n{draft_text}\n```",
                },
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "👉 승인 페이지 열기"},
                        "url": approve_url,
                        "style": "primary",
                    }
                ],
            },
        ],
    }
    _post(payload)


def notify_posted(tweet_url: str, draft_text: str) -> None:
    """X 포스팅 완료 알림"""
    payload = {
        "text": "✅ X 포스팅 완료",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"✅ *포스팅 완료*\n\n트윗 URL: {tweet_url}\n\n```{draft_text}```",
                },
            }
        ],
    }
    _post(payload)


def notify_rejected(title: str) -> None:
    """초안 거절 알림"""
    payload = {
        "text": f"❌ 초안 거절됨: {title}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"❌ *초안 거절됨*\n기사: {title}",
                },
            }
        ],
    }
    _post(payload)


def notify_error(context: str, error: str) -> None:
    """에러 알림"""
    payload = {
        "text": f"🚨 에러 발생: {context}",
        "blocks": [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🚨 *에러 발생*\n*상황:* {context}\n*오류:* ```{error}```",
                },
            }
        ],
    }
    _post(payload)
