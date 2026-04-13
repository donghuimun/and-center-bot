import os
import time
import anthropic


SYSTEM_PROMPT = """
당신은 데일리NK AND센터(@ANDCenter_NK) X 계정 운영자입니다.

**작성 규칙**:
1. 280자 이내 (필수)
2. '북한' 대신 '조선' 표기
3. 체제 비판 배제, 사실 전달 중심
4. 신뢰감 있는 기관 계정 톤
5. 마지막 줄에 기사 원문 링크 포함
6. 해시태그 2~3개 (#조선 #ANDCenter #북한인권 등)

**독자층**: 해외체류 조선 주민 + 북한 연구자·언론인·정책 관계자

**출력 형식**:
[포스트 본문]

[기사 URL]

#조선 #해시태그2 #해시태그3
"""

USER_PROMPT_TEMPLATE = """
아래 기사를 분석하고 X 포스트 초안을 작성하세요.

제목: {title}
본문: {content}
URL: {url}
"""

MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def generate_draft(title: str, content: str, url: str) -> str:
    """
    Claude API를 호출하여 X 포스트 초안을 생성합니다.
    실패 시 최대 3회 재시도 (exponential backoff).
    """
    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    user_prompt = USER_PROMPT_TEMPLATE.format(
        title=title,
        content=content[:2000],  # 토큰 절약: 본문 2000자 제한
        url=url,
    )

    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5",
                max_tokens=512,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text.strip()
        except Exception as e:
            last_error = e
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY * (2 ** attempt))

    raise RuntimeError(f"Claude API 실패 ({MAX_RETRIES}회 시도): {last_error}")
