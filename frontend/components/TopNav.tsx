"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";

const NAV_ITEMS = [
  { label: "Research", href: "/" },
  { label: "Runs", href: "/runs" },
  { label: "Evidence", href: "/evidence" },
  { label: "Evaluations", href: "/evaluations" },
  { label: "Settings", href: "/settings" },
];

const RESEARCH_TABS = ["/", "/workflow", "/report", "/battlecard", "/overview"];

function isActive(href: string, pathname: string): boolean {
  if (href === "/") return RESEARCH_TABS.includes(pathname);
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function TopNav() {
  const pathname = usePathname();
  const router = useRouter();

  return (
    <div className="sticky top-0 z-40 px-4 pt-4 sm:px-6">
      <nav className="mx-auto flex max-w-6xl items-center justify-between gap-4 rounded-2xl border border-[var(--border)] bg-[var(--surface)]/90 px-4 py-3 shadow-[0_8px_24px_-18px_rgba(28,27,26,0.35)] backdrop-blur">
        <Link href="/overview" className="flex items-center gap-2.5">
          <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--ink)] text-[var(--accent)]">
            <CompassIcon />
          </span>
          <span className="text-[15px] font-bold tracking-tight text-[var(--foreground)]">
            RivalScope AI
          </span>
        </Link>

        <div className="hidden items-center gap-1 md:flex">
          {NAV_ITEMS.map((item) => {
            const active = isActive(item.href, pathname);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition-colors ${
                  active
                    ? "bg-[var(--accent)]/45 text-[#6f5512]"
                    : "text-[var(--muted)] hover:bg-[var(--surface-muted)] hover:text-[var(--foreground)]"
                }`}
              >
                {item.label}
              </Link>
            );
          })}
        </div>

        <button
          type="button"
          onClick={() => router.push("/")}
          className="inline-flex items-center gap-1.5 rounded-xl bg-[var(--ink)] px-3.5 py-2 text-sm font-semibold text-white transition-colors hover:bg-black"
        >
          <span className="text-base leading-none">+</span> New Research
        </button>
      </nav>
    </div>
  );
}

function CompassIcon() {
  return (
    <svg className="h-5 w-5" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.8" />
      <path
        d="M15.5 8.5L13 13l-4.5 2.5L11 11l4.5-2.5z"
        fill="currentColor"
      />
    </svg>
  );
}
