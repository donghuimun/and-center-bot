# AND센터 X 자동 포스팅 시스템
## 개발자 에이전트 전달용 기술 기획서

**프로젝트 코드명**: `and-center-bot`  
**작성일**: 2026-04-13  
**기획**: DH (Product Manager)  
**개발**: Claude Developer Agent  

---

## 1. 프로젝트 목표

데일리NK RSS 피드에서 새 기사를 감지하고, Claude API로 X 포스트 초안을 자동 생성한 뒤, Slack으로 담당자 승인을 받아 @ANDCenter_NK 계정에 자동 포스팅하는 서버리스 파이프라인 구축.

**핵심 요구사항**:
- 데스크탑 불필요 (24시간 자동 운영)
- 평일 하루 5건 기사 자동 처리
- 담당자 승인 프로세스 필수
- 중복 포스팅 방지
- 전체 비용 월 $25 이내

---

## 2. 시스템 아키텍처

```
┌─────────────────────────────────────────────────────────────┐
│                    Vercel Cron Job                           │
│  (평일 5회: 08:10, 10:25, 12:40, 15:00, 17:10 KST)         │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  RSS Parser (feedparser)                     │
│          https://www.dailynk.com/feed 체크                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (새 기사 감지시)
┌─────────────────────────────────────────────────────────────┐
│              Supabase articles 테이블 저장                   │
│              (rss_id 중복 체크 via UNIQUE)                   │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│            Claude API (claude-sonnet-4)                      │
│        기사 분석 → X 포스트 초안 작성 (280자)               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│             Supabase drafts 테이블 저장                      │
│              status: 'pending'                               │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                  Slack 알림 전송                             │
│   초안 내용 + 승인 페이지 링크 (Incoming Webhook)           │
└─────────────────────────────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         담당자 승인 (Next.js 웹페이지)                       │
│      https://your-app.vercel.app/approve/[draft_id]         │
│         [✅ 승인] [❌ 거절] [✏️ 수정 후 승인]                │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼ (승인시)
┌─────────────────────────────────────────────────────────────┐
│              X API v2 (tweepy)                               │
│        @ANDCenter_NK 계정 자동 포스팅                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────────┐
│         Supabase 업데이트 + Slack 완료 알림                  │
│    status: 'approved', posted_url: tweet_url                │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 기술 스택

| 레이어 | 기술 | 용도 |
|--------|------|------|
| **프레임워크** | Next.js 14+ (App Router) | 승인 웹페이지 + API Routes |
| **서버리스 런타임** | Vercel Serverless Functions | Python API endpoints |
| **데이터베이스** | Supabase (PostgreSQL) | 기사/초안 저장, 중복 방지 |
| **AI** | Anthropic Claude API | 포스트 초안 작성 |
| **SNS** | X API v2 (tweepy) | 트윗 포스팅 |
| **알림** | Slack Incoming Webhooks | 담당자 알림 |
| **RSS** | feedparser (Python) | 데일리NK 피드 파싱 |
| **배포** | Vercel | 호스팅 + Cron |

---

## 4. 프로젝트 구조

```
and-center-bot/
├── api/
│   ├── cron.py                 # Vercel Cron: RSS → Claude → Slack
│   ├── approve.py              # POST /api/approve (승인 처리)
│   └── reject.py               # POST /api/reject (거절 처리)
│
├── app/
│   ├── layout.tsx              # Next.js App Router 루트 레이아웃
│   └── approve/
│       └── [id]/
│           └── page.tsx        # 승인 웹페이지 (동적 라우트)
│
├── lib/
│   ├── rss_parser.py           # RSS 파싱 로직
│   ├── claude_client.py        # Claude API 호출
│   ├── x_poster.py             # X 포스팅 (tweepy)
│   ├── slack_notifier.py       # Slack 웹훅 전송
│   └── supabase_client.py      # Supabase CRUD
│
├── public/
│   └── logo.png                # AND센터 로고 (승인 페이지용)
│
├── .env.local                  # 로컬 개발용 환경변수 (git 제외)
├── .env.example                # 환경변수 템플릿
├── .gitignore                  # .env.local 반드시 포함
├── next.config.js              # Service Role Key 브라우저 노출 방지
├── vercel.json                 # Cron 설정
├── requirements.txt            # Python 의존성
├── package.json                # Node.js 의존성 (js-cookie 포함)
└── README.md                   # 배포 가이드
```

**`next.config.js` (보안 크리티컬)**:
```javascript
/** @type {import('next').NextConfig} */
const nextConfig = {
  env: {
    // ⚠️ NEXT_PUBLIC_ 접두사 없는 변수는 브라우저에 노출되지 않음
    // SUPABASE_SERVICE_ROLE_KEY는 절대 이곳에 포함하지 말 것
  },
  
  // 서버사이드 환경변수 검증
  serverRuntimeConfig: {
    supabaseServiceKey: process.env.SUPABASE_SERVICE_ROLE_KEY,
  },
}

module.exports = nextConfig
```

---

## 5. 환경변수 목록

`.env.local` / Vercel 환경변수에 다음 키 설정:

```bash
# Supabase (서버사이드 - RLS 우회)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...  # ⚠️ Cron/API 전용, 클라이언트 노출 금지

# Supabase (클라이언트사이드 - RLS 적용)
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...  # 브라우저 노출 허용

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-...

# X API (developer.twitter.com)
X_API_KEY=...
X_API_SECRET=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...

# Slack
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...

# 승인 페이지 보안
APPROVE_PASSWORD=your_secret_password
```

**🔴 보안 크리티컬**: 
- `SUPABASE_SERVICE_ROLE_KEY`는 RLS를 완전히 무시하므로 **절대 브라우저에 노출 금지**
- Python API Routes (`api/cron.py` 등)에서만 사용
- Next.js 클라이언트 코드에서는 `NEXT_PUBLIC_SUPABASE_ANON_KEY` 사용

---

## 6. Supabase 데이터베이스 스키마

### 6.1 `articles` 테이블

```sql
CREATE TABLE articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rss_id TEXT UNIQUE NOT NULL,           -- 중복 방지용 (guid 또는 link)
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_rss_id ON articles(rss_id);
```

### 6.2 `drafts` 테이블

```sql
CREATE TABLE drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    draft_text TEXT NOT NULL,              -- Claude 초안
    status TEXT DEFAULT 'pending',          -- pending / approved / posted / rejected / failed
    edited_text TEXT,                       -- 수정 후 승인된 최종 텍스트
    approved_at TIMESTAMP,
    posted_url TEXT,                        -- 트윗 URL (예: https://x.com/ANDCenter_NK/status/123...)
    error_message TEXT,                     -- X API 에러 메시지 (failed 상태일 때)
    retry_count INTEGER DEFAULT 0,          -- Rate limit 재시도 횟수
    created_at TIMESTAMP DEFAULT NOW(),
    CHECK (status IN ('pending', 'approved', 'posted', 'rejected', 'failed'))
);

CREATE INDEX idx_status ON drafts(status);
CREATE INDEX idx_article_id ON drafts(article_id);
```

### 6.3 `approval_logs` 테이블 (운영 히스토리 추적)

```sql
CREATE TABLE approval_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID REFERENCES drafts(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'edited')),
    approver_email TEXT,                    -- 승인자 식별 (선택)
    approved_at TIMESTAMP DEFAULT NOW(),
    notes TEXT                              -- 거절 사유 등 추가 메모
);

CREATE INDEX idx_draft_id ON approval_logs(draft_id);
CREATE INDEX idx_action ON approval_logs(action);
```

**활용 사례**:
- "누가, 언제, 어떤 수정을 거쳐" 포스팅했는지 히스토리 관리
- 거절된 초안 분석 → Claude 프롬프트 개선
- 월별 승인율 통계

### 6.4 Row Level Security (RLS) 설정

```sql
-- articles 테이블: Service Role은 전체 접근, 인증된 사용자는 읽기만
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON articles
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Authenticated read" ON articles
  FOR SELECT USING (auth.role() = 'authenticated');

-- drafts 테이블: Service Role 전체 접근, 인증된 사용자는 pending만 읽기/수정
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON drafts
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Authenticated read pending only" ON drafts
  FOR SELECT USING (
    auth.role() = 'authenticated' AND 
    status = 'pending'
  );

CREATE POLICY "Authenticated update own drafts" ON drafts
  FOR UPDATE USING (auth.role() = 'authenticated');

-- approval_logs 테이블: Service Role만 쓰기, 인증된 사용자는 읽기
ALTER TABLE approval_logs ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access" ON approval_logs
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Authenticated read logs" ON approval_logs
  FOR SELECT USING (auth.role() = 'authenticated');
```

**보안 강화 포인트**:
- `SUPABASE_SERVICE_ROLE_KEY`: Cron/API에서만 사용 (RLS 우회)
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`: 브라우저에서 사용 (RLS 적용)
- 외부인이 `anon key`를 탈취해도 `pending` 상태 초안만 조회 가능
- `posted`, `failed` 등 민감한 상태 데이터는 접근 불가

---

## 7. Vercel Cron 설정 (`vercel.json`)

데일리NK 발행 시간에 맞춘 5회 체크 (평일만):

```json
{
  "crons": [
    {
      "path": "/api/cron",
      "schedule": "10 8 * * 1-5"
    },
    {
      "path": "/api/cron",
      "schedule": "25 10 * * 1-5"
    },
    {
      "path": "/api/cron",
      "schedule": "40 12 * * 1-5"
    },
    {
      "path": "/api/cron",
      "schedule": "0 15 * * 1-5"
    },
    {
      "path": "/api/cron",
      "schedule": "10 17 * * 1-5"
    }
  ]
}
```

**스케줄 형식**: `분 시 일 월 요일` (UTC 기준 → KST는 -9시간 보정 필요)  
**예시**: `10 8 * * 1-5` = 매주 월~금 08:10 UTC (17:10 KST)

**⚠️ 주의**: Vercel Cron은 UTC 기준이므로 KST 시간대 변환 필요.  
- KST 08:10 = UTC 전날 23:10
- 개발자가 정확한 UTC 변환 수행할 것

**🔴 시간대 전략 이슈** (컨텐츠 가이드라인 참조):
- 현재 설정: 데일리NK 발행 시간 맞춤 (한국 중심)
- 문제점: 미국 정책 관계자 골든 타임 누락 (전부 밤/새벽)
- 개선안: **KST 22:00~24:00** (미 동부 09:00~11:00) 1회 추가 권장
- 상세 전략: `AND_X_Content_Strategy.md` 섹션 13 참조

**Phase 2 확장 계획**:
- 미국 타겟 Cron 1회 추가 (22:30 KST)
- 시간대별 컨텐츠 전략 적용 (국내 vs 글로벌 vs 미국)
- A/B 테스트 결과 기반 스케줄 최적화

---

## 8. Claude API 초안 작성 프롬프트

`lib/claude_client.py`에서 사용할 system prompt:

```python
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
```

---

## 9. API 엔드포인트 명세

### 9.1 `GET /api/cron`

**역할**: Vercel Cron에서 호출. RSS 체크 → Claude 초안 → Slack 알림

**프로세스**:
1. `feedparser`로 https://www.dailynk.com/feed 파싱
2. 각 기사의 `guid` 또는 `link`를 `rss_id`로 Supabase 중복 체크
3. 신규 기사만 `articles` 테이블에 INSERT
4. Claude API 호출하여 초안 생성
5. `drafts` 테이블에 저장 (status='pending')
6. Slack 웹훅으로 알림 전송 (초안 + 승인 링크)

**응답**:
```json
{
  "status": "success",
  "new_articles": 2,
  "drafts_created": 2
}
```

---

### 9.2 `POST /api/approve`

**역할**: 승인 웹페이지에서 호출. 초안 승인 → X 포스팅

**요청**:
```json
{
  "draft_id": "uuid-here",
  "action": "approve",
  "edited_text": "수정된 텍스트 (선택)"
}
```

**프로세스**:
1. `draft_id`로 drafts 조회
2. `action`이 'approve'면:
   - `edited_text` 있으면 사용, 없으면 `draft_text` 사용
   - tweepy로 X 포스팅
   - `status='approved'`, `posted_url=트윗URL` 업데이트
   - Slack에 완료 알림
3. `action`이 'reject'면:
   - `status='rejected'` 업데이트

**응답**:
```json
{
  "status": "success",
  "tweet_url": "https://x.com/ANDCenter_NK/status/123..."
}
```

---

### 9.3 `POST /api/reject`

**역할**: 승인 웹페이지에서 거절 처리

**요청**:
```json
{
  "draft_id": "uuid-here"
}
```

**프로세스**:
1. `status='rejected'` 업데이트
2. Slack에 거절 알림 (선택)

---

## 10. Slack 알림 메시지 포맷

### 10.1 초안 알림 (Cron 후)

```json
{
  "text": "📰 새 기사 감지",
  "blocks": [
    {
      "type": "header",
      "text": {
        "type": "plain_text",
        "text": "📰 새 기사 감지"
      }
    },
    {
      "type": "section",
      "fields": [
        {
          "type": "mrkdwn",
          "text": "*제목:*\n조선, 강제노동 동원 확대"
        },
        {
          "type": "mrkdwn",
          "text": "*링크:*\nhttps://www.dailynk.com/..."
        }
      ]
    },
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "✏️ *Claude 초안:*\n```\n[초안 내용]\n```"
      }
    },
    {
      "type": "actions",
      "elements": [
        {
          "type": "button",
          "text": {
            "type": "plain_text",
            "text": "👉 승인 페이지 열기"
          },
          "url": "https://your-app.vercel.app/approve/[draft_id]",
          "style": "primary"
        }
      ]
    }
  ]
}
```

### 10.2 승인 완료 알림

```json
{
  "text": "✅ 포스팅 완료",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "✅ *포스팅 완료*\n\n트윗 URL: https://x.com/ANDCenter_NK/status/123..."
      }
    }
  ]
}
```

---

## 11. 승인 웹페이지 UI 명세

**경로**: `/approve/[id]` (Next.js Dynamic Route)

**레이아웃**:
```
┌─────────────────────────────────────────────────┐
│         AND센터 로고 [logo.png]                  │
│                                                  │
│  제목: [기사 제목]                                │
│  원문: [기사 URL 링크]                            │
│                                                  │
│  ─────────────────────────────────────────────  │
│                                                  │
│  📝 Claude 초안:                                 │
│  ┌─────────────────────────────────────────┐   │
│  │ [초안 텍스트]                             │   │
│  │                                          │   │
│  │ [기사 URL]                                │   │
│  │ #조선 #ANDCenter #북한인권               │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  ✏️ 수정 (선택):                                │
│  ┌─────────────────────────────────────────┐   │
│  │ [textarea - 280자 제한]                   │   │
│  └─────────────────────────────────────────┘   │
│                                                  │
│  [✅ 승인]  [✏️ 수정 후 승인]  [❌ 거절]         │
└─────────────────────────────────────────────────┘
```

**기능 요구사항**:
- 280자 실시간 카운터 (수정 textarea)
- 버튼 클릭 시 `/api/approve` 또는 `/api/reject` 호출
- 처리 후 완료 메시지 표시
- 로딩 상태 UI (버튼 비활성화)

---

## 12. 보안 요구사항

| 항목 | 조치 | 우선순위 |
|------|------|----------|
| API 키 보호 | Vercel 환경변수 저장 | 🔴 필수 |
| GitHub 레포 | Private 설정 | 🔴 필수 |
| .env.local | .gitignore 추가 | 🔴 필수 |
| Supabase RLS | 활성화 + 정책 설정 | 🔴 필수 |
| 승인 페이지 접근 | 간단한 비밀번호 인증 (환경변수 `APPROVE_PASSWORD`) | 🟡 권장 |
| Slack 이벤트 검증 | Signing Secret 검증 (현재 단계에서는 Webhook만 사용하므로 불필요) | 🟢 선택 |

**승인 페이지 보안 구현 (Form POST 방식)**:

```typescript
// app/approve/[id]/page.tsx
'use client';

import { useState, useEffect } from 'react';
import Cookies from 'js-cookie';

export default function ApprovePage({ params }) {
  const [authenticated, setAuthenticated] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // 쿠키에서 인증 상태 확인
    const authToken = Cookies.get('approve_auth');
    if (authToken === 'authenticated') {
      setAuthenticated(true);
    }
    setLoading(false);
  }, []);

  async function handleAuth(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    const password = formData.get('password');

    const res = await fetch('/api/verify-password', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password })
    });

    if (res.ok) {
      // HttpOnly는 서버에서 설정, 클라이언트는 일반 쿠키 사용
      Cookies.set('approve_auth', 'authenticated', { expires: 1/24 }); // 1시간
      setAuthenticated(true);
    } else {
      alert('비밀번호가 올바르지 않습니다');
    }
  }

  if (loading) return <div>로딩 중...</div>;

  if (!authenticated) {
    return (
      <form onSubmit={handleAuth}>
        <input type="password" name="password" placeholder="승인 페이지 비밀번호" required />
        <button type="submit">로그인</button>
      </form>
    );
  }

  // ... 승인 UI
}
```

```typescript
// api/verify-password/route.ts (Next.js App Router)
import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const { password } = await request.json();
  
  if (password === process.env.APPROVE_PASSWORD) {
    return NextResponse.json({ success: true });
  }
  
  return NextResponse.json({ error: 'Invalid password' }, { status: 401 });
}
```

**보안 강화 포인트**:
- 비밀번호가 URL에 노출되지 않음 (POST Body 전송)
- 쿠키로 인증 상태 유지 (페이지 새로고침 시에도 재로그인 불필요)
- 쿠키 만료 시간 설정 (1시간 후 자동 로그아웃)

---

## 13. 개발 단계별 체크리스트

### Phase 1: 인프라 세팅
- [ ] Supabase 프로젝트 생성
- [ ] `articles`, `drafts` 테이블 생성
- [ ] RLS 정책 설정
- [ ] API 키 전체 발급 (X, Anthropic, Slack, Supabase)

### Phase 2: 로컬 개발
- [ ] Next.js 프로젝트 생성 (`npx create-next-app@latest`)
- [ ] Python 런타임 설정 (Vercel은 자동 감지)
- [ ] `lib/` 모듈 개발:
  - [ ] `rss_parser.py` - feedparser 테스트
  - [ ] `supabase_client.py` - CRUD 테스트
  - [ ] `claude_client.py` - 초안 생성 테스트
  - [ ] `slack_notifier.py` - 웹훅 전송 테스트
  - [ ] `x_poster.py` - tweepy 포스팅 테스트

### Phase 3: API 구현
- [ ] `api/cron.py` 구현 (RSS → Claude → Slack)
- [ ] `api/approve.py` 구현 (승인 → X 포스팅)
- [ ] `api/reject.py` 구현
- [ ] 로컬 테스트 (`vercel dev`)

### Phase 4: 프론트엔드
- [ ] `app/approve/[id]/page.tsx` 구현
- [ ] 280자 카운터 추가
- [ ] 버튼 액션 연결
- [ ] 로딩/완료 상태 UI

### Phase 5: 배포
- [ ] GitHub Private 레포 생성
- [ ] Vercel 프로젝트 연결
- [ ] 환경변수 설정 (Vercel Dashboard)
- [ ] `vercel.json` Cron 설정
- [ ] 배포 후 Cron 동작 확인

### Phase 6: 통합 테스트
- [ ] 테스트 X 계정으로 전체 플로우 검증
- [ ] 중복 방지 테스트 (같은 기사 재처리 시도)
- [ ] 승인/거절/수정 시나리오 테스트
- [ ] Slack 알림 확인

### Phase 7: 프로덕션
- [ ] @ANDCenter_NK 실계정 연동
- [ ] 1주일 모니터링
- [ ] 에러 로그 확인
- [ ] 필요시 Cron 스케줄 조정

---

## 14. 에러 처리 전략

### 14.1 RSS 파싱 실패
- 로그 기록 후 다음 Cron까지 대기
- Slack에 에러 알림 (선택)

### 14.2 Claude API 실패
- 3회 재시도 (exponential backoff)
- 실패 시 기본 템플릿 사용 또는 Slack 알림

### 14.3 X API 실패 (에러 코드별 처리)

**X API 주요 에러 코드**:
- **Error 187**: 중복 게시물 (Status is a duplicate)
- **Error 226**: 자동화 스팸 의심 (Automated behavior detected)
- **Error 403**: Rate limit 초과
- **Error 401**: 인증 실패

**구현 예시** (`lib/x_poster.py`):

```python
import tweepy
from supabase import Client

class XPosterError(Exception):
    """X API 커스텀 에러"""
    pass

async def post_to_x(draft_id: str, text: str, supabase: Client):
    """
    X에 포스팅하고 에러 코드별 처리
    """
    try:
        client = tweepy.Client(
            consumer_key=os.getenv('X_API_KEY'),
            consumer_secret=os.getenv('X_API_SECRET'),
            access_token=os.getenv('X_ACCESS_TOKEN'),
            access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET')
        )
        
        response = client.create_tweet(text=text)
        tweet_id = response.data['id']
        tweet_url = f"https://x.com/ANDCenter_NK/status/{tweet_id}"
        
        # 성공: DB 업데이트
        supabase.table('drafts').update({
            'status': 'posted',
            'posted_url': tweet_url,
            'approved_at': 'NOW()'
        }).eq('id', draft_id).execute()
        
        return {"success": True, "url": tweet_url}
        
    except tweepy.errors.Forbidden as e:
        error_code = e.api_codes[0] if e.api_codes else None
        
        if error_code == 187:
            # 중복 게시물
            supabase.table('drafts').update({
                'status': 'failed',
                'error_message': 'Duplicate tweet detected'
            }).eq('id', draft_id).execute()
            
            await notify_slack_error(
                "⚠️ X API 중복 감지",
                f"이미 포스팅된 내용입니다: {text[:50]}..."
            )
            
        elif error_code == 226:
            # 자동화 스팸 의심
            supabase.table('drafts').update({
                'status': 'failed',
                'error_message': 'Automated behavior flagged'
            }).eq('id', draft_id).execute()
            
            await notify_slack_error(
                "🔴 X 정책 위반 경고",
                f"스팸으로 의심되는 자동화 패턴 감지. 수동 포스팅 필요."
            )
            
        else:
            # 기타 Forbidden 에러
            await notify_slack_error(
                "❌ X API Forbidden",
                f"Error {error_code}: {str(e)}"
            )
            
        raise XPosterError(f"X API Error {error_code}")
        
    except tweepy.errors.TooManyRequests:
        # Rate limit 초과 - 재시도 큐 필요
        supabase.table('drafts').update({
            'status': 'pending',
            'retry_count': 'retry_count + 1'
        }).eq('id', draft_id).execute()
        
        await notify_slack_error(
            "⏱️ X API Rate Limit",
            "15분 후 자동 재시도 예정"
        )
        
    except Exception as e:
        # 예상치 못한 에러
        supabase.table('drafts').update({
            'status': 'failed',
            'error_message': str(e)
        }).eq('id', draft_id).execute()
        
        await notify_slack_error(
            "❌ X 포스팅 실패",
            f"Draft ID: {draft_id}\nError: {str(e)}"
        )
        
        raise
```

**DB 스키마 추가** (drafts 테이블):
```sql
ALTER TABLE drafts 
  ADD COLUMN error_message TEXT,
  ADD COLUMN retry_count INTEGER DEFAULT 0;
```

### 14.4 Supabase 연결 실패
- Vercel 로그에 기록
- 긴급 Slack 알림

---

## 15. 모니터링 및 로깅

### 15.1 Vercel 로그
- 모든 API 응답 로그 활성화
- Cron 실행 이력 확인

### 15.2 Supabase 로그
- Slow query 모니터링
- RLS 정책 위반 확인

### 15.3 커스텀 로그 (선택)
- 각 단계별 타임스탬프 기록
- 에러 발생 시 Slack 알림

---

## 16. 향후 확장 계획

- **다국어 지원**: 영어 포스트 자동 생성 (별도 Claude 호출)
- **이미지 자동 생성**: 기사 내용 기반 데이터 카드 생성
- **분석 대시보드**: 포스팅 성과 추적 (Supabase + Chart.js)
- **X 스레드**: 긴 분석은 스레드로 자동 연결
- **A/B 테스팅**: Claude에 2개 초안 요청 후 담당자 선택

---

## 17. 참고 자료

- Vercel Cron: https://vercel.com/docs/cron-jobs
- Supabase Python: https://supabase.com/docs/reference/python
- Tweepy v2: https://docs.tweepy.org/en/stable/
- Slack Webhooks: https://api.slack.com/messaging/webhooks
- Anthropic API: https://docs.anthropic.com/

---

## 18. 개발자 에이전트 액션 아이템

### 즉시 조치 (제미나이 평가 반영)

1. **보안 강화**:
   - [ ] `next.config.js` 작성 (Service Role Key 브라우저 노출 차단)
   - [ ] 승인 페이지 Form POST 인증 구현 (URL 쿼리 방식 제거)
   - [ ] `js-cookie` 패키지 추가 (세션 유지)

2. **DB 스키마 업데이트**:
   - [ ] `drafts` 테이블에 `error_message`, `retry_count` 컬럼 추가
   - [ ] `approval_logs` 테이블 생성 (히스토리 추적)
   - [ ] RLS 정책 강화 (Service Role vs Anon Key 분리)

3. **에러 처리 구현**:
   - [ ] X API 에러 코드별 처리 (187, 226, 403, 401)
   - [ ] `lib/x_poster.py`에 세분화된 에러 핸들링
   - [ ] Slack 에러 알림 타입별 분류

### 기본 개발 단계

4. **프로젝트 초기화**: Next.js + Python 하이브리드 구조 생성
5. **의존성 설치**: 
   - `requirements.txt`: feedparser, tweepy, anthropic, supabase-py
   - `package.json`: next, react, js-cookie, @supabase/supabase-js
6. **환경변수 템플릿**: `.env.example` 작성
7. **Supabase 스키마**: SQL 마이그레이션 스크립트 작성 (3개 테이블 + RLS)
8. **핵심 모듈 구현**: `lib/` 폴더 우선 개발
9. **API 엔드포인트**: `/api/cron`, `/api/approve`, `/api/reject`
10. **승인 페이지**: Next.js App Router 동적 라우트 + Form 인증
11. **로컬 테스트**: `vercel dev`로 전체 플로우 검증
12. **배포 가이드**: README.md에 배포 절차 문서화
13. **핸드오프**: DH에게 Vercel 프로젝트 URL + 환경변수 설정 가이드 전달

---

## 19. 제미나이 평가 반영 완료

✅ **보안 크리티컬 이슈 해결**:
- 승인 페이지 인증: URL 쿼리 → Form POST + 쿠키 세션
- Supabase RLS: Service Role / Anon Key 분리 + 정책 강화
- Service Role Key 유출 방지: `next.config.js` 설정

✅ **에러 핸들링 강화**:
- Claude API: Exponential backoff 재시도
- X API: 에러 코드별 처리 (187, 226, 403, 401)
- Slack 에러 알림 타입 분류

✅ **DB 스키마 개선**:
- `drafts` 테이블: `error_message`, `retry_count` 추가
- `approval_logs` 테이블: 승인 히스토리 추적
- `status` 필드 CHECK 제약 조건

✅ **RSS 중복 방지**:
- `rss_id` UNIQUE 제약 조건
- 애플리케이션 레벨 필터링
- Cron 안전장치

---

## 20. 최종 질문사항

**개발 착수 전 확인 필요**:
- [ ] UTC 시간대 변환 확인 (KST → UTC for Vercel Cron)
- [ ] X API Free tier 월 500트윗 제한 확인 완료
- [ ] Slack 채널 또는 DM 대상 확인
- [ ] 승인 페이지 접근: 간단 비밀번호 vs Supabase Auth 최종 결정

**예상 개발 시간**: 10~14시간 (제미나이 제안 반영 +2시간)

---

**END OF SPECIFICATION (v2.0 - Gemini Review Applied)**
