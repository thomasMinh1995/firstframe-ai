import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FirstFrame AI",
  description: "From vague ideas to structured story development.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
