-- 이미지 첨부 + 훅 유형 기록
-- Supabase SQL Editor에서 실행 (배포 전 필수)

-- articles: RSS 본문에서 추출한 첫 이미지 (X 포스팅 첨부용)
ALTER TABLE articles ADD COLUMN IF NOT EXISTS image_url TEXT;

-- drafts: Claude가 선택한 훅 유형 (scene/contradiction/number/quote/observation)
-- 훅 유형별 engagement 분석용
ALTER TABLE drafts ADD COLUMN IF NOT EXISTS hook_type TEXT;
