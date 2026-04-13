import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AND센터 X 포스팅 승인",
  description: "AND센터 X 자동 포스팅 승인 시스템",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body
        style={{
          margin: 0,
          fontFamily: "'Pretendard', 'Apple SD Gothic Neo', sans-serif",
          backgroundColor: "#f5f5f5",
          color: "#111",
        }}
      >
        {children}
      </body>
    </html>
  );
}
