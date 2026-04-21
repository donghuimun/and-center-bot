import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@supabase/supabase-js";

function getSupabase() {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) throw new Error("Missing Supabase env vars");
  return createClient(url, key);
}

function verifyAuth(request: NextRequest): boolean {
  const password = process.env.APPROVE_PASSWORD;
  if (!password) return true; // 미설정 시 통과 (개발 환경)
  const auth = request.headers.get("Authorization") ?? "";
  return auth === `Bearer ${password}`;
}

export async function GET(
  request: NextRequest,
  { params }: { params: { id: string } }
) {
  if (!verifyAuth(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const draftId = params.id;
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
