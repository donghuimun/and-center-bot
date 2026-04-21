/** @type {import('next').NextConfig} */
const nextConfig = {
  // ⚠️ NEXT_PUBLIC_ 접두사가 없는 변수는 브라우저에 노출되지 않음
  // SUPABASE_SERVICE_ROLE_KEY는 절대 NEXT_PUBLIC_ 으로 시작하지 말 것
};

module.exports = nextConfig;
