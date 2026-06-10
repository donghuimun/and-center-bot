# AND센터 X 봇 점검 계획서
작성일: 2026-05-27

---

## 1. 프로젝트 개요

**목적:** DailyNK RSS 기사를 자동으로 수집해 영어 X(Twitter) 포스트 초안을 생성하고, 담당자 승인 후 @ANDCenter_NK 계정에 게시

**배포 환경:** Vercel (Next.js + Python 서버리스)  
**DB:** Supabase (PostgreSQL)  
**외부 API:** Anthropic Claude API, X API v2, Slack Webhook

---

## 2. 현재 기술 스택

```
Vercel Cron (5회/평일)
    ↓
api/cron.py
    ↓ RSS 파싱
lib/rss_parser.py  ← DailyNK /feed (KO) + /english/feed (EN)
    ↓ 중복 체크
lib/supabase_client.py  ← articles 테이블
    ↓ 초안 생성
lib/claude_client.py  ← Claude Sonnet 4.6
    ↓ Slack 알림
lib/slack_notifier.py  ← 승인 링크 포함
    ↓ 담당자 승인
app/approve/[id]/page.tsx  ← 웹 승인 UI
    ↓
api/approve.py  ← X 포스팅
lib/x_poster.py  ← X API v2
```

### 파일별 역할 요약

| 파일 | 역할 |
|------|------|
| `api/cron.py` | 파이프라인 진입점. MAX 2개/회 제한 |
| `lib/rss_parser.py` | KO/EN 피드 파싱, HTML strip |
| `lib/supabase_client.py` | articles / drafts / approval_logs CRUD |
| `lib/claude_client.py` | 시스템 프롬프트 + 초안 생성 + 검증 |
| `lib/x_poster.py` | X API OAuth 1.0a 포스팅 |
| `lib/slack_notifier.py` | 승인 요청 / 완료 / 에러 알림 |
| `api/approve.py` | 승인/거절 처리, atomic 상태 전이 |
| `app/approve/[id]/page.tsx` | 승인 웹 UI (Next.js) |

### Supabase 스키마

```
articles: id, rss_id(unique), title, url, published, created_at
drafts: id, article_id, draft_text, status, edited_text, approved_at, posted_url, error_message, retry_count, created_at
  status: pending → posting → posted | rejected | failed
approval_logs: id, draft_id, action, approver_email, approved_at, notes
```

### 크론 스케줄 (UTC → KST)

| UTC | KST |
|-----|-----|
| 23:10 (일-목) | 08:10 (월-금) |
| 01:25 (월-금) | 10:25 (월-금) |
| 03:40 (월-금) | 12:40 (월-금) |
| 06:00 (월-금) | 15:00 (월-금) |
| 08:10 (월-금) | 17:10 (월-금) |

---

## 3. Claude 프롬프트 전략

### 훅 유형 (4개로 정리)
1. **Scene** — 인간 장면 우선
2. **Shock Number** — 수치가 있을 때
3. **Direct Quote** — 강한 인용문이 있을 때
4. **Contradiction** — 국가 주장 vs 현실 괴리

### 훅 선택 우선순위
Scene → Number → Quote → Contradiction 순으로 기사 내용에 맞는 것 선택

### 검증 로직
- 한글 문자 포함 → 재시도
- 기사 URL 누락 → 재시도
- 해시태그 3개 미만 → 재시도
- 최대 3회 재시도, 지수 백오프

---

## 4. X 계정 현황 분석 (데이터 기반)

### 4.1 계정 전체 개요 (2025-06-11 ~ 2026-06-10, 365일)

| 지표 | 값 |
|------|-----|
| 총 Impressions | 21,264 |
| 일평균 Impressions | 58.3 |
| 총 New Follows | 68 |
| 팔로워 획득률 | 0.19명/일 |

**진단:** 1년간 총 68명 신규 팔로워. 일평균 58.3 impressions는 활성 계정 기준 매우 낮은 수치.

---

### 4.2 4월 콘텐츠 분석 (2026-04-01 ~ 2026-04-30)

**포스트 구성 (총 98개)**

| 유형 | 수 | 평균 Impressions |
|------|-----|-----------------|
| 한국어 오리지널 | 83개 | 29.2 |
| 영어 오리지널 | 8개 | 30.9 |
| 영어 리플라이 (@멘션) | 7개 | **153.7** |

**4월 전체 합계**

| 지표 | 값 |
|------|-----|
| 총 Impressions | 4,726 |
| 평균 imp/포스트 | 48.2 |
| Likes | 6 |
| Bookmarks | 1 |
| Shares | 3 |
| Engagements | 86 |

**상위 5개 포스트**

| Impressions | 유형 | 내용 요약 |
|------------|------|----------|
| 992 | 영어 리플라이 @AJENews | 영변 핵단지 확장 관련 |
| 609 | 영어 리플라이 @Reuters | 북한 전술 변화 관련 |
| 176 | 영어 리플라이 @Reuters | 왕이 평양 방문 분석 |
| 150 | 영어 리플라이 @AFP | 한국 안보 커뮤니티 관련 |
| 113 | 한국어 | 영변 위성 분석 |

---

### 4.3 핵심 인사이트

1. **리플라이 전략이 가장 효과적**  
   7개 리플라이 평균 153.7 imp vs 오리지널 포스트 ~30 imp. 대형 미디어 계정(@Reuters, @AJENews, @AFP) 스레드에 달린 리플라이가 압도적으로 높은 노출을 기록.

2. **한국어 vs 영어 오리지널은 성과 차이 없음**  
   한국어 29.2 vs 영어 30.9 — 현재 팔로워 기반이 약해서 언어보다 네트워크 효과가 더 큰 영향.

3. **참여 지표가 극히 낮음**  
   98개 포스트에서 Likes 6, Bookmarks 1, Shares 3. 콘텐츠 퀄리티 또는 타겟 오디언스 도달 문제.

4. **영어 전환은 방향은 맞지만 단독으로는 부족**  
   RSS 기반 오리지널 포스팅만으로는 노출 한계. 리플라이 전략 병행 필요.

---

## 5. 점검 요청 사항

### 5.1 파이프라인 안정성

- [ ] 크론 → RSS → Claude → Slack → X 전체 파이프라인에서 단일 장애점(SPOF)은 어디인가
- [ ] `MAX_ARTICLES_PER_RUN = 2` 제한이 Vercel Free 10초 제한 안에서 실제로 안전한가
- [ ] Claude API 실패 시 해당 기사가 영구적으로 누락될 수 있는가 (rss_id는 이미 articles에 저장됨)
- [ ] `article_exists()` 체크와 `insert_article()` 사이의 race condition 가능성

### 5.2 초안 품질

- [ ] 현재 시스템 프롬프트(훅 4개 + 선택 우선순위)가 일관된 톤을 만드는지
- [ ] `article_text[:5000]`이 RSS summary일 때 사실 왜곡 가능성
- [ ] 영어 피드 기사와 한국어 피드 기사가 같은 사건을 다룰 때 중복 초안이 생성되는지

### 5.3 콘텐츠 전략

- [ ] 현재 오리지널 포스팅 중심 전략 vs 리플라이 병행 전략의 효과 비교
- [ ] 4월 데이터 기준 어떤 훅 유형이 실제로 높은 engagement를 만들었는지
- [ ] 영어 전환 이후 타겟 오디언스(영어권 NK 관심층) 도달 가능성 평가
- [ ] 해시태그 전략 (#NorthKorea #DPRK #ANDCenter)이 노출 확장에 실제로 기여하는지

### 5.4 보안 및 운영

- [ ] 비밀번호 원문 쿠키 저장 → 실제 위험 수준 평가 및 대안
- [ ] `APPROVE_PASSWORD` 미설정 시 인증 우회 → 운영 환경 보호 방안
- [ ] Supabase RLS가 현재 서비스 역할 키 사용 구조와 충돌하지 않는지

---

## 6. 현재 알려진 미해결 이슈

| 이슈 | 상태 |
|------|------|
| GitHub → Vercel 자동 배포 미작동 | 수동 `vercel --prod`로 우회 중 |
| `api/reject.py` 중복 (approve.py와 기능 겹침) | 미정리 |
| 승인 비밀번호 쿠키 평문 저장 | 미수정 |
| `/logo.png` 파일 없음 | 미수정 |
| GitHub PAT 노출 (채팅) | 교체 필요 |

---

## 7. 참고 파일 목록

```
api/cron.py
api/approve.py
api/reject.py
lib/rss_parser.py
lib/claude_client.py
lib/supabase_client.py
lib/slack_notifier.py
lib/x_poster.py
app/approve/[id]/page.tsx
app/api/draft/[id]/route.ts
vercel.json
supabase/migrations/001_init.sql ~ 004_add_posting_status.sql
```
