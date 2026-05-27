-- drafts.status에 'posting' 추가 (원자적 중복 포스팅 방지용)
ALTER TABLE drafts DROP CONSTRAINT IF EXISTS drafts_status_check;
ALTER TABLE drafts ADD CONSTRAINT drafts_status_check
  CHECK (status IN ('pending', 'posting', 'posted', 'rejected', 'failed'));
