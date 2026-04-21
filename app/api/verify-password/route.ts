import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const { password } = await request.json();

  const correctPassword = process.env.APPROVE_PASSWORD;

  // APPROVE_PASSWORD 미설정 시 인증 불필요 (개발 환경)
  if (!correctPassword || password === correctPassword) {
    return NextResponse.json({ success: true });
  }

  return NextResponse.json({ error: "비밀번호가 올바르지 않습니다." }, { status: 401 });
}
