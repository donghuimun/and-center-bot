"use client";

import { useEffect, useState, FormEvent } from "react";
import { useParams } from "next/navigation";
import Cookies from "js-cookie";

// ─────────────────────────────────────────
// Types
// ─────────────────────────────────────────
interface DraftData {
  id: string;
  draft_text: string;
  status: string;
  articles: {
    title: string;
    url: string;
  } | null;
}

type PageState =
  | { type: "auth" }
  | { type: "loading" }
  | { type: "ready"; draft: DraftData }
  | { type: "done"; message: string; tweetUrl?: string }
  | { type: "error"; message: string };

// ─────────────────────────────────────────
// Helpers
// ─────────────────────────────────────────
const MAX_CHARS = 280;
const AUTH_COOKIE = "approve_token"; // 실제 비밀번호를 저장 (Bearer 토큰으로 사용)
const COOKIE_EXPIRES_DAYS = 7; // 7일

function getAuthHeaders(): HeadersInit {
  const token = Cookies.get(AUTH_COOKIE) ?? "";
  return {
    "Content-Type": "application/json",
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

function charCount(text: string) {
  return text.length;
}

// ─────────────────────────────────────────
// Page Component
// ─────────────────────────────────────────
export default function ApprovePage() {
  const params = useParams<{ id: string }>();
  const draftId = params.id;

  const [pageState, setPageState] = useState<PageState>({ type: "loading" });
  const [editedText, setEditedText] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [authError, setAuthError] = useState("");

  useEffect(() => {
    // 쿠키 인증 상태 확인 (값이 존재하면 로그인된 것)
    if (Cookies.get(AUTH_COOKIE)) {
      fetchDraft();
    } else {
      setPageState({ type: "auth" });
    }
  }, [draftId]);

  async function handleAuth(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setAuthError("");
    const formData = new FormData(e.currentTarget);
    const password = formData.get("password") as string;

    const res = await fetch("/api/verify-password", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (res.ok) {
      // 비밀번호를 쿠키에 저장 → 이후 API 요청의 Authorization Bearer 토큰으로 사용
      Cookies.set(AUTH_COOKIE, password, { expires: COOKIE_EXPIRES_DAYS });
      fetchDraft();
    } else {
      setAuthError("비밀번호가 올바르지 않습니다.");
    }
  }

  async function fetchDraft() {
    setPageState({ type: "loading" });
    try {
      const res = await fetch(`/api/draft/${draftId}`, { headers: getAuthHeaders() });
      if (res.status === 401) {
        // 토큰 만료 또는 비밀번호 불일치 → 쿠키 제거 후 재인증
        Cookies.remove(AUTH_COOKIE);
        setPageState({ type: "auth" });
        setAuthError("세션이 만료되었습니다. 다시 로그인해 주세요.");
        return;
      }
      if (!res.ok) throw new Error("초안을 불러올 수 없습니다.");
      const data: DraftData = await res.json();

      if (data.status !== "pending") {
        setPageState({
          type: "done",
          message: `이미 처리된 초안입니다. (status: ${data.status})`,
        });
        return;
      }

      setEditedText(data.draft_text);
      setPageState({ type: "ready", draft: data });
    } catch (e) {
      setPageState({ type: "error", message: String(e) });
    }
  }

  async function handleAction(action: "approve" | "reject", useEdited = false) {
    if (submitting) return;
    setSubmitting(true);
    try {
      const body: Record<string, string> = { draft_id: draftId, action };
      if (action === "approve" && useEdited) {
        body.edited_text = editedText;
      }
      const res = await fetch("/api/approve", {
        method: "POST",
        headers: getAuthHeaders(),
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.message ?? "처리 실패");

      if (action === "approve") {
        setPageState({
          type: "done",
          message: "포스팅이 완료되었습니다.",
          tweetUrl: data.tweet_url,
        });
      } else {
        setPageState({ type: "done", message: "초안이 거절되었습니다." });
      }
    } catch (e) {
      alert(`오류: ${e}`);
    } finally {
      setSubmitting(false);
    }
  }

  // ─── Renders ─────────────────────────
  if (pageState.type === "auth") {
    return (
      <Wrapper>
        <Card>
          <div style={{ borderBottom: "1px solid #e5e5e5", paddingBottom: 16, marginBottom: 20 }}>
            <h1 style={{ margin: 0, fontSize: 18 }}>AND센터 X 포스팅 승인</h1>
          </div>
          <form onSubmit={handleAuth}>
            <Label>비밀번호</Label>
            <input
              type="password"
              name="password"
              placeholder="승인 페이지 비밀번호 입력"
              required
              autoFocus
              style={{
                width: "100%",
                boxSizing: "border-box",
                padding: "10px 12px",
                fontSize: 14,
                borderRadius: 8,
                border: "1px solid #ccc",
                marginTop: 4,
                marginBottom: 12,
                fontFamily: "inherit",
              }}
            />
            {authError && (
              <p style={{ color: "#c00", fontSize: 13, margin: "0 0 12px" }}>{authError}</p>
            )}
            <button type="submit" style={btnStyle("#1a7f37")}>
              로그인
            </button>
          </form>
        </Card>
      </Wrapper>
    );
  }

  if (pageState.type === "loading") {
    return (
      <Wrapper>
        <Card>
          <p>불러오는 중...</p>
        </Card>
      </Wrapper>
    );
  }

  if (pageState.type === "done") {
    return (
      <Wrapper>
        <Card>
          <h2 style={{ color: "#1a7f37" }}>{pageState.message}</h2>
          {pageState.tweetUrl && (
            <a
              href={pageState.tweetUrl}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#1d9bf0" }}
            >
              트윗 보기 →
            </a>
          )}
        </Card>
      </Wrapper>
    );
  }

  if (pageState.type === "error") {
    return (
      <Wrapper>
        <Card>
          <p style={{ color: "#c00" }}>오류: {pageState.message}</p>
          <button onClick={fetchDraft} style={btnStyle("#555")}>
            다시 시도
          </button>
        </Card>
      </Wrapper>
    );
  }

  const { draft } = pageState;
  const count = charCount(editedText);
  const overLimit = count > MAX_CHARS;

  return (
    <Wrapper>
      <Card>
        {/* 헤더 */}
        <div style={{ borderBottom: "1px solid #e5e5e5", paddingBottom: 16, marginBottom: 20 }}>
          <img src="/logo.png" alt="AND센터" height={40} style={{ marginBottom: 8 }} />
          <h1 style={{ margin: 0, fontSize: 18 }}>X 포스팅 승인</h1>
        </div>

        {/* 기사 정보 */}
        <section style={{ marginBottom: 20 }}>
          <Label>기사 제목</Label>
          <p style={{ margin: "4px 0", fontWeight: 600 }}>{draft.articles?.title ?? "(제목 없음)"}</p>
          {draft.articles?.url && (
            <a
              href={draft.articles.url}
              target="_blank"
              rel="noopener noreferrer"
              style={{ fontSize: 13, color: "#1d9bf0" }}
            >
              원문 보기 →
            </a>
          )}
        </section>

        {/* 초안 */}
        <section style={{ marginBottom: 20 }}>
          <Label>Claude 초안</Label>
          <pre style={{
            background: "#f0f0f0", padding: "12px 14px", borderRadius: 8,
            fontSize: 14, whiteSpace: "pre-wrap", wordBreak: "break-word", margin: "4px 0",
          }}>
            {draft.draft_text}
          </pre>
        </section>

        {/* 수정 textarea */}
        <section style={{ marginBottom: 24 }}>
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 4,
            }}
          >
            <Label>수정 (선택)</Label>
            <span
              style={{
                fontSize: 13,
                color: overLimit ? "#c00" : "#888",
                fontWeight: overLimit ? 700 : 400,
              }}
            >
              {count} / {MAX_CHARS}
            </span>
          </div>
          <textarea
            value={editedText}
            onChange={(e) => setEditedText(e.target.value)}
            rows={6}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px 12px",
              fontSize: 14,
              borderRadius: 8,
              border: `1px solid ${overLimit ? "#c00" : "#ccc"}`,
              resize: "vertical",
              fontFamily: "inherit",
            }}
          />
        </section>

        {/* 버튼 */}
        <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
          <button
            disabled={submitting}
            onClick={() => handleAction("approve", false)}
            style={btnStyle("#1a7f37")}
          >
            {submitting ? "처리 중..." : "승인"}
          </button>
          <button
            disabled={submitting || overLimit || editedText === draft.draft_text}
            onClick={() => handleAction("approve", true)}
            style={btnStyle("#1d9bf0")}
          >
            수정 후 승인
          </button>
          <button
            disabled={submitting}
            onClick={() => handleAction("reject")}
            style={btnStyle("#c00")}
          >
            거절
          </button>
        </div>
      </Card>
    </Wrapper>
  );
}

// ─────────────────────────────────────────
// Sub-components
// ─────────────────────────────────────────
function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "flex-start",
        padding: "40px 16px",
        backgroundColor: "#f5f5f5",
      }}
    >
      {children}
    </div>
  );
}

function Card({ children }: { children: React.ReactNode }) {
  return (
    <div
      style={{
        width: "100%",
        maxWidth: 560,
        background: "#fff",
        borderRadius: 12,
        padding: "28px 24px",
        boxShadow: "0 2px 12px rgba(0,0,0,0.08)",
      }}
    >
      {children}
    </div>
  );
}

function Label({ children }: { children: React.ReactNode }) {
  return (
    <p style={{ margin: 0, fontSize: 12, fontWeight: 600, color: "#666", textTransform: "uppercase", letterSpacing: 0.5 }}>
      {children}
    </p>
  );
}

function btnStyle(bg: string): React.CSSProperties {
  return {
    padding: "10px 20px",
    background: bg,
    color: "#fff",
    border: "none",
    borderRadius: 8,
    fontSize: 14,
    fontWeight: 600,
    cursor: "pointer",
  };
}
