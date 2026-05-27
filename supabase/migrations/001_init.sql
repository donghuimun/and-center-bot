-- AND센터 X 자동 포스팅 시스템 초기 스키마
-- Supabase SQL Editor에서 실행

-- ─────────────────────────────────────────
-- articles 테이블
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS articles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rss_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    url TEXT NOT NULL,
    published TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_articles_rss_id ON articles(rss_id);

-- ─────────────────────────────────────────
-- drafts 테이블
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    article_id UUID REFERENCES articles(id) ON DELETE CASCADE,
    draft_text TEXT NOT NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'posted', 'rejected', 'failed')),
    edited_text TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    posted_url TEXT,
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_drafts_article_id ON drafts(article_id);

-- ─────────────────────────────────────────
-- approval_logs 테이블 (승인 히스토리 추적)
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS approval_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    draft_id UUID REFERENCES drafts(id) ON DELETE CASCADE,
    action TEXT NOT NULL CHECK (action IN ('approved', 'rejected', 'edited')),
    approver_email TEXT,
    approved_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    notes TEXT
);

CREATE INDEX IF NOT EXISTS idx_approval_logs_draft_id ON approval_logs(draft_id);
CREATE INDEX IF NOT EXISTS idx_approval_logs_action ON approval_logs(action);

-- ─────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;
ALTER TABLE approval_logs ENABLE ROW LEVEL SECURITY;

-- articles: Service Role 전체 접근, anon/authenticated 읽기 허용
CREATE POLICY "Service role full access on articles" ON articles
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Anon read articles" ON articles
  FOR SELECT USING (true);

-- drafts: Service Role 전체 접근, anon은 pending 상태만 읽기
CREATE POLICY "Service role full access on drafts" ON drafts
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Anon read pending drafts" ON drafts
  FOR SELECT USING (status = 'pending');

-- approval_logs: Service Role만 쓰기, anon은 읽기
CREATE POLICY "Service role full access on approval_logs" ON approval_logs
  FOR ALL USING (auth.role() = 'service_role');

CREATE POLICY "Anon read approval_logs" ON approval_logs
  FOR SELECT USING (true);
