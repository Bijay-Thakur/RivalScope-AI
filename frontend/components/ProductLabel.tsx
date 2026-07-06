interface ProductLabelProps {
  children: React.ReactNode;
  tone?: "default" | "gold" | "bronze" | "muted";
}

const TONE_CLASS = {
  default: "text-neutral-500",
  gold: "text-amber-400",
  bronze: "text-neutral-400",
  muted: "text-neutral-600",
};

export function ProductLabel({ children, tone = "default" }: ProductLabelProps) {
  return (
    <span
      className={`inline-block text-[11px] font-semibold uppercase tracking-[0.14em] ${TONE_CLASS[tone]}`}
    >
      {children}
    </span>
  );
}
