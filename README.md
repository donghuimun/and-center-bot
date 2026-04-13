# AND센터 X 자동 포스팅 봇

데일리NK RSS → Claude AI 초안 → Slack 승인 → @ANDCenter_NK 자동 포스팅

## 아키텍처

```
Vercel Cron → RSS 파싱 → Claude 초안 → Slack 알림
                                              ↓
                                    담당자 승인 페이지
                                              ↓
                                      X API 포스팅
```

## 로컬 개발

### 1. 의존성 설치

```bash
npm install
pip install -r requirements.txt
```

### 2. 환경변수 설정

```bash
cp .env.example .env.local
# .env.local 파일을 열어 실제 값 입력
```

### 3. 개발 서버 실행

```bash
npx vercel dev
```

## Supabase 스키마 초기화

Supabase Dashboard > SQL Editor에서 아래 파일 내용을 실행:

```
supabase/migrations/001_init.sql
```

## Vercel 배포

### 1. GitHub Private 레포 생성 후 push

```bash
git init
git remote add origin https://github.com/your-org/and-center-bot.git
git add .
git commit -m "initial commit"
git push -u origin main
```

### 2. Vercel 연결

- vercel.com에서 Import Git Repository
- Framework: Next.js 자동 감지

### 3. 환경변수 설정 (Vercel Dashboard > Settings > Environment Variables)

| 변수명 | 설명 |
|--------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_ANON_KEY` | Supabase anon key |
| `ANTHROPIC_API_KEY` | Claude API key |
| `X_API_KEY` | X API consumer key |
| `X_API_SECRET` | X API consumer secret |
| `X_ACCESS_TOKEN` | X access token |
| `X_ACCESS_TOKEN_SECRET` | X access token secret |
| `SLACK_WEBHOOK_URL` | Slack Incoming Webhook URL |
| `APPROVE_PASSWORD` | 승인 페이지 접근 비밀번호 |
| `NEXT_PUBLIC_APP_URL` | 배포된 앱 URL (예: https://and-center-bot.vercel.app) |

### 4. Cron 스케줄 확인

`vercel.json`의 Cron은 **UTC 기준**으로 설정되어 있습니다.

| UTC | KST | 설명 |
|-----|-----|------|
| 일~목 23:10 | 월~금 08:10 | 1차 |
| 월~금 01:25 | 월~금 10:25 | 2차 |
| 월~금 03:40 | 월~금 12:40 | 3차 |
| 월~금 06:00 | 월~금 15:00 | 4차 |
| 월~금 08:10 | 월~금 17:10 | 5차 |

## 승인 페이지 사용법

Slack 알림에서 "승인 페이지 열기" 버튼 클릭 →

`https://your-app.vercel.app/approve/{draft_id}?password=YOUR_PASSWORD`

- **승인**: 초안 그대로 X 포스팅
- **수정 후 승인**: textarea 수정 후 포스팅
- **거절**: 해당 초안 폐기

## 프로젝트 구조

```
and-center-bot/
├── api/
│   ├── cron.py          # Vercel Cron 엔드포인트
│   ├── approve.py       # 승인/거절 처리
│   └── reject.py        # 거절 처리 (deprecated → approve.py로 통합 가능)
├── app/
│   ├── layout.tsx
│   ├── api/draft/[id]/route.ts   # 초안 조회 API
│   └── approve/[id]/page.tsx     # 승인 웹페이지
├── lib/
│   ├── rss_parser.py
│   ├── supabase_client.py
│   ├── claude_client.py
│   ├── slack_notifier.py
│   └── x_poster.py
├── supabase/migrations/001_init.sql
├── vercel.json
├── requirements.txt
└── package.json
```
