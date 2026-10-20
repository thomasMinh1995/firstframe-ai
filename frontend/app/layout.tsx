import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FirstFrame AI",
  description: "Phát triển và sửa câu chuyện đầu tiên của bạn cùng FirstFrame.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
