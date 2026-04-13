import os
import tweepy


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
    """
    client = get_client()
    response = client.create_tweet(text=text)
    tweet_id = response.data["id"]
    return f"https://x.com/ANDCenter_NK/status/{tweet_id}"
