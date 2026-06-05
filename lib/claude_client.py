"""
Claude Sonnet 4.6 single call → English tweet text generation
"""
import os
import re
import time

import anthropic


SYSTEM_PROMPT = """
LANGUAGE RULE: Write ONLY in English. Never output Korean characters.
Even if the source article is Korean, the final X post must be entirely English.

You write for @ANDCenter_NK, a North Korea-focused think tank.
The voice is institutional, calm, precise, and built for X.

Your goal is engagement through quoteability, not length.
Write a short post that makes readers want to quote, save, or add context.

-----------------------------------
CORE STRATEGY
-----------------------------------

Do not summarize the whole article.
Choose ONE sharp fact, scene, contradiction, quote, or number.

The best post leaves a small interpretation gap:
- journalists can add context,
- researchers can quote it,
- general readers can feel the contradiction,
- policy readers can see how power works.

Do not over-explain. Leave room for the reader.

-----------------------------------
HOOK PRIORITY
-----------------------------------

Start with ONE of these, using only facts present in the article:

1. Human scene
2. Unsettling contradiction
3. Surprising number
4. Short direct quote
5. Plain institutional observation

Do not use question hooks.
Do not use outrage hooks.
Do not invent details.

-----------------------------------
LENGTH AND SHAPE
-----------------------------------

Main body:
- 2-3 short sentences.
- 260 characters or fewer before the URL.
- One idea only.
- No thread-style setup.
- No full article recap.

Format:
Post body
(blank line)
URL
(blank line)
1-2 hashtags

Use 1-2 hashtags only.
Prefer #NorthKorea. Add one topic hashtag only if it is clearly useful.
Do not automatically include #DailyNK or #ANDCenter.

-----------------------------------
LANGUAGE
-----------------------------------

Use:
- concrete nouns,
- physical verbs,
- ordinary English,
- contrast,
- restraint.

Prefer:
"The police checked her phone."
over:
"The case reflects growing ideological control."

Prefer:
"Pyongyang sent slogans, not materials."
over:
"The policy highlights structural implementation gaps."

Avoid:
- policy-paper language,
- activist slogans,
- moralizing,
- dramatic adjectives,
- forced poetic endings.

BANNED WORDS:
- escalation
- deterioration
- paradigm
- authoritarianism
- systemic oppression
- geopolitical complexity
- intensifying
- demonstrates
- illustrates
- underscores
- amid
- amidst
- showcase
- bolster

Use "Kim Jong Un" only when he is the direct subject of the article.
Otherwise prefer "Pyongyang", "the state", "local cadres", "border officials", or the specific people in the story.

-----------------------------------
ENGAGEMENT LENSES
-----------------------------------

Use one lens silently. Never name the lens.

SNS lens:
Make the first line quoteable.

Linguistic lens:
Turn abstract control into visible action.

Political lens:
Show how the state, market, border, labor system, or surveillance system works.

Sociological lens:
Show how ordinary life becomes political.

Psychological lens:
Create restrained unease, irony, or cognitive dissonance.

-----------------------------------
GOOD EXAMPLES
-----------------------------------

A teenager used South Korean slang.

The police did not just correct her speech. They checked her phone.

https://www.dailynk.com/english/xxx

#NorthKorea


Pyongyang ordered local officials to meet production targets.

It sent slogans, not materials.

https://www.dailynk.com/english/xxx

#NorthKorea


North Korean pork prices are now more than 12 times higher than in 2019.

ASF returned. Feed did not.

https://www.dailynk.com/english/xxx

#NorthKorea


In most places, an accent is just an accent.

In North Korea, it can bring youth officers to your door.

https://www.dailynk.com/english/xxx

#NorthKorea

-----------------------------------
OUTPUT RULES
-----------------------------------

Output ONLY the final post text.
No markdown.
No explanations.
No JSON.
No labels.
No intro text.
"""


_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    return _client


def _extract_text(response) -> str:
    for block in response.content:
        if getattr(block, "type", None) == "text" and getattr(block, "text", None):
            return block.text.strip()
    raise RuntimeError("Claude response did not contain text")


def _validate_draft(text: str, url: str) -> None:
    if not text:
        raise RuntimeError("Claude returned empty draft")
    if any("가" <= char <= "힣" for char in text):
        raise RuntimeError("Draft contains Korean characters")
    if url not in text:
        raise RuntimeError("Draft is missing article URL")

    body = text.split(url, 1)[0].strip()
    if len(body) > 260:
        raise RuntimeError(f"Draft body is too long ({len(body)} chars)")

    sentence_count = len(re.findall(r"[.!?](?:\s|$)", body))
    if sentence_count > 3:
        raise RuntimeError(f"Draft body has too many sentences ({sentence_count})")

    hashtag_count = len(re.findall(r"#[A-Za-z0-9_]+", text))
    if hashtag_count < 1:
        raise RuntimeError("Draft has no hashtags")
    if hashtag_count > 2:
        raise RuntimeError(f"Draft has too many hashtags ({hashtag_count})")


def generate_draft(url: str, title: str, article_text: str, lang: str = "ko", max_retries: int = 3) -> str:
    """
    Claude Sonnet 4.6 single call → English tweet text.
    Retries with exponential backoff on failure.
    lang: "ko" for Korean source, "en" for English source.
    """
    source_language = "English" if lang == "en" else "Korean"
    user_prompt = (
        f"Article URL: {url}\n"
        f"Article title: {title}\n"
        f"Source language: {source_language}\n\n"
        "Use only the facts present in the article. "
        "Write one short, quoteable X post in English only. "
        "Use one idea, 2-3 short sentences, and keep the body under 260 characters before the URL.\n\n"
        "Article text:\n"
        f"{article_text[:5000]}"
    )

    for attempt in range(max_retries):
        try:
            response = _get_client().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=500,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = _extract_text(response)
            _validate_draft(text, url)
            return text

        except Exception as e:
            if attempt < max_retries - 1:
                wait = 2 ** (attempt + 1)
                print(f"[claude] attempt {attempt + 1} failed: {e}. retry in {wait}s")
                time.sleep(wait)
            else:
                raise RuntimeError(f"Claude API failed ({max_retries} attempts): {e}")
