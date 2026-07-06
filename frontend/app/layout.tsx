import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { TopNav } from "@/components/TopNav";
import { RunProvider } from "@/lib/runContext";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "RivalScope AI",
  description: "Source-grounded competitive intelligence for GTM teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-screen flex-col font-sans antialiased`}
      >
        <RunProvider>
          <TopNav />
          <div className="flex-1 px-4 pb-20 pt-6 sm:px-6">
            <div className="mx-auto max-w-6xl">{children}</div>
          </div>
        </RunProvider>
      </body>
    </html>
  );
}
