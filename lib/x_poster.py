import os
import tweepy


class XPostError(Exception):
    """X API 에러 래퍼 — error_code 속성 포함"""
    def __init__(self, message: str, error_code: int | None = None):
        super().__init__(message)
        self.error_code = error_code


def get_client() -> tweepy.Client:
    return tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )


def post_tweet(text: str) -> str:
    """
    X에 트윗을 포스팅하고 트윗 URL을 반환합니다.
    반환: "https://x.com/ANDCenter_NK/status/{tweet_id}"

    에러 코드별 처리:
      187 — 중복 트윗  → XPostError(error_code=187)
      226 — 자동화 스팸 의심 → XPostError(error_code=226)
      429 — Rate limit → XPostError(error_code=429)  (재시도 가능)
      401 — 인증 실패  → XPostError(error_code=401)
    """
    client = get_client()

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        return f"https://x.com/ANDCenter_NK/status/{tweet_id}"

    except tweepy.errors.Forbidden as e:
        code = _first_api_code(e)
        if code == 187:
            raise XPostError("중복 트윗이 감지되었습니다. 동일한 내용이 이미 포스팅되었습니다.", error_code=187)
        if code == 226:
            raise XPostError(
                "X에서 자동화된 스팸 행동으로 감지하였습니다. 잠시 후 수동 포스팅이 필요합니다.",
                error_code=226,
            )
        raise XPostError(f"X API Forbidden (code={code}): {e}", error_code=code)

    except tweepy.errors.Unauthorized as e:
        code = _first_api_code(e)
        raise XPostError(f"X API 인증 실패 — API 키/토큰을 확인해 주세요 (code={code}): {e}", error_code=401)

    except tweepy.errors.TooManyRequests as e:
        raise XPostError("X API Rate limit 초과. 15분 후 재시도 가능합니다.", error_code=429)

    except tweepy.errors.TwitterServerError as e:
        raise XPostError(f"X 서버 오류: {e}", error_code=500)

    except tweepy.errors.TweepyException as e:
        raise XPostError(f"X API 오류: {e}")


def _first_api_code(exc: tweepy.errors.HTTPException) -> int | None:
    """tweepy HTTPException에서 첫 번째 API 에러 코드를 추출합니다."""
    if hasattr(exc, "api_codes") and exc.api_codes:
        return exc.api_codes[0]
    return None
