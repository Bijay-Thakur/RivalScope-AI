import type { ReactNode } from "react";

/* ---------------------------------------------------------------- Card ---- */

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-2xl border border-[var(--border)] bg-[var(--surface)] shadow-[0_1px_2px_rgba(28,27,26,0.04),0_8px_24px_-16px_rgba(28,27,26,0.18)] ${className}`}
    >
      {children}
    </section>
  );
}

/* ------------------------------------------------------------- Page tags -- */

export function PageBadge({ children }: { children: ReactNode }) {
  return (
    <span className="inline-flex items-center rounded-md bg-[var(--accent)]/35 px-2 py-1 text-[10px] font-bold uppercase tracking-[0.14em] text-[#7a5f16]">
      {children}
    </span>
  );
}

export function PageHeader({
  badge,
  title,
  subtitle,
}: {
  badge?: string;
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-8">
      {badge && <PageBadge>{badge}</PageBadge>}
      <h1 className="mt-3 text-3xl font-bold tracking-tight text-[var(--foreground)] sm:text-4xl">
        {title}
      </h1>
      {subtitle && (
        <p className="mt-2 max-w-2xl text-sm leading-relaxed text-[var(--muted)]">
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function SectionTitle({
  title,
  subtitle,
}: {
  title: string;
  subtitle?: string;
}) {
  return (
    <div className="mb-5">
      <h2 className="text-lg font-bold tracking-tight text-[var(--foreground)]">
        {title}
      </h2>
      {subtitle && (
        <p className="mt-1 text-sm leading-relaxed text-[var(--muted)]">{subtitle}</p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ Dot --- */

const DOT_COLORS: Record<string, string> = {
  blue: "var(--dot-blue)",
  green: "var(--dot-green)",
  yellow: "var(--dot-yellow)",
  purple: "var(--dot-purple)",
  pink: "var(--dot-pink)",
};

export function Dot({ color = "blue" }: { color?: keyof typeof DOT_COLORS | string }) {
  return (
    <span
      className="inline-block h-3 w-3 shrink-0 rounded-full"
      style={{ backgroundColor: DOT_COLORS[color] ?? color }}
      aria-hidden="true"
    />
  );
}

/* ------------------------------------------------------------- Stat card -- */

const ACCENT_BARS: Record<string, string> = {
  gold: "var(--accent-strong)",
  green: "var(--ok)",
  red: "var(--bad)",
  purple: "#8b5cf6",
  blue: "var(--dot-blue)",
};

export function StatCard({
  label,
  value,
  hint,
  accent = "gold",
}: {
  label: string;
  value: ReactNode;
  hint?: string;
  accent?: keyof typeof ACCENT_BARS;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex">
        <span
          className="w-1 shrink-0"
          style={{ backgroundColor: ACCENT_BARS[accent] ?? ACCENT_BARS.gold }}
          aria-hidden="true"
        />
        <div className="px-5 py-4">
          <p className="text-xs font-medium text-[var(--muted)]">{label}</p>
          <p className="mt-1.5 text-3xl font-bold tracking-tight text-[var(--foreground)] tabular-nums">
            {value}
          </p>
          {hint && <p className="mt-0.5 text-xs text-[var(--muted-2)]">{hint}</p>}
        </div>
      </div>
    </Card>
  );
}

/* ---------------------------------------------------------------- Badge ---- */

type BadgeTone = "ok" | "warn" | "bad" | "neutral" | "info";

const BADGE_TONES: Record<BadgeTone, string> = {
  ok: "bg-[var(--ok-bg)] text-[var(--ok)]",
  warn: "bg-[var(--warn-bg)] text-[var(--warn)]",
  bad: "bg-[var(--bad-bg)] text-[var(--bad)]",
  neutral: "bg-[var(--surface-muted)] text-[var(--muted)] border border-[var(--border)]",
  info: "bg-[#e9eefb] text-[#3b5bdb]",
};

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: BadgeTone;
}) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-xs font-semibold ${BADGE_TONES[tone]}`}
    >
      {children}
    </span>
  );
}

/* ---------------------------------------------------------- Callout bar --- */

export function DarkCallout({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-2xl bg-[var(--ink)] px-6 py-4 text-center text-sm font-semibold text-neutral-100">
      {children}
    </div>
  );
}

/* ------------------------------------------------------------- Button ------ */

export function PrimaryButton({
  children,
  onClick,
  type = "button",
  disabled = false,
  className = "",
}: {
  children: ReactNode;
  onClick?: () => void;
  type?: "button" | "submit";
  disabled?: boolean;
  className?: string;
}) {
  return (
    <button
      type={type}
      onClick={onClick}
      disabled={disabled}
      className={`inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--ink)] px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-black focus:outline-none focus-visible:ring-2 focus-visible:ring-[var(--accent-strong)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 disabled:active:scale-100 ${className}`}
    >
      {children}
    </button>
  );
}
