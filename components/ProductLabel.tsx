interface ProductLabelProps {
  children: React.ReactNode;
  tone?: "default" | "gold" | "bronze" | "muted";
}

const TONE_CLASS = {
  default: "text-stone-500",
  gold: "text-amber-800",
  bronze: "text-stone-600",
  muted: "text-stone-400",
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
