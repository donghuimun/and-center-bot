import { NextRequest, NextResponse } from "next/server";

export async function POST(request: NextRequest) {
  const { password } = await request.json();

  const correctPassword = process.env.APPROVE_PASSWORD;

  // APPROVE_PASSWORD 미설정 시: 프로덕션은 차단(fail-closed), 그 외 환경은 통과
  if (!correctPassword) {
    if (process.env.VERCEL_ENV === "production") {
      return NextResponse.json({ error: "APPROVE_PASSWORD가 설정되지 않았습니다." }, { status: 401 });
    }
    return NextResponse.json({ success: true });
  }

  if (password === correctPassword) {
    return NextResponse.json({ success: true });
  }

  return NextResponse.json({ error: "비밀번호가 올바르지 않습니다." }, { status: 401 });
}
