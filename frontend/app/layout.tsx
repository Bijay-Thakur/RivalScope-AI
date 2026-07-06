import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Header } from "@/components/Header";
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
  description:
    "Source-grounded competitive intelligence briefs for GTM teams",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} flex min-h-screen flex-col bg-neutral-950 font-sans text-neutral-200 antialiased`}
      >
        <Header />
        <div className="flex-1">{children}</div>
        <footer className="border-t border-neutral-800 bg-neutral-950 py-8 text-center">
          <p className="text-xs text-neutral-500">
            RivalScope AI — Portfolio demo · Mock data via local backend
          </p>
        </footer>
      </body>
    </html>
  );
}
