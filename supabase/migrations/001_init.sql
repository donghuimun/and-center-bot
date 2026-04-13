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
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected', 'failed', 'edited')),
    edited_text TEXT,
    approved_at TIMESTAMP WITH TIME ZONE,
    posted_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_drafts_status ON drafts(status);
CREATE INDEX IF NOT EXISTS idx_drafts_article_id ON drafts(article_id);

-- ─────────────────────────────────────────
-- Row Level Security
-- ─────────────────────────────────────────
ALTER TABLE articles ENABLE ROW LEVEL SECURITY;
ALTER TABLE drafts ENABLE ROW LEVEL SECURITY;

-- 내부 시스템용 anon key 허용 (프로덕션에선 Service Role Key 권장)
CREATE POLICY "Allow anon access" ON articles FOR ALL USING (true);
CREATE POLICY "Allow anon access" ON drafts FOR ALL USING (true);
