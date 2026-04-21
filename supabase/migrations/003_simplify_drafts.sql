-- 003: KR/EN 이중 초안 → 한국어 전용으로 단순화
-- drafts 테이블에서 002에서 추가한 불필요 컬럼 제거

ALTER TABLE drafts
  DROP COLUMN IF EXISTS draft_text_en,
  DROP COLUMN IF EXISTS tags_kr,
  DROP COLUMN IF EXISTS tags_en,
  DROP COLUMN IF EXISTS frame,
  DROP COLUMN IF EXISTS slot;
