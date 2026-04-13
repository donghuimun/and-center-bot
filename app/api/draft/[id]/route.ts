import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function getSupabase() {
  const url = process.env.SUPABASE_URL!;
  const key = process.env.SUPABASE_ANON_KEY!;
  return createClient(url, key);
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  const draftId = params.id;
  const password = request.nextUrl.searchParams.get("password") ?? "";

  // 비밀번호 검증
  const approvePassword = process.env.APPROVE_PASSWORD;
  if (approvePassword && password !== approvePassword) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const supabase = getSupabase();
  const { data, error } = await supabase
    .from("drafts")
    .select("*, articles(title, url)")
    .eq("id", draftId)
    .single();

  if (error || !data) {
    return NextResponse.json(
      { error: "초안을 찾을 수 없습니다." },
      { status: 404 }
    );
  }

  return NextResponse.json(data);
}
