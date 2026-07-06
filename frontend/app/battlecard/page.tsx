"use client";

import { useEffect, useState } from "react";
import { Card, DarkCallout, PageHeader } from "@/components/ui/primitives";
import { loadSession } from "@/lib/reportStore";

const COLUMNS = [
  { key: "talkTracks", label: "Talk Tracks", tone: "bg-[#e3ebfd] text-[#3b5bdb]" },
  { key: "objectionHandling", label: "Objection Handling", tone: "bg-[var(--warn-bg)] text-[var(--warn)]" },
  { key: "landmines", label: "Landmines", tone: "bg-[var(--bad-bg)] text-[var(--bad)]" },
] as const;

export default function BattlecardPage() {
  const [items, setItems] = useState<{
    talkTracks: string[];
    objectionHandling: string[];
    landmines: string[];
  } | null>(null);

  useEffect(() => {
    const session = loadSession();
    setItems(session?.report.salesBattlecard ?? null);
  }, []);

  if (!items) {
    return (
      <div className="rs-fade-in">
        <PageHeader badge="Page 5" title="Sales Battlecard" />
        <Card className="px-6 py-16 text-center text-sm text-[var(--muted)]">
          No battlecard yet. Generate a Sales Battlecard research run first.
        </Card>
      </div>
    );
  }

  return (
    <div className="rs-fade-in">
      <PageHeader
        badge="Page 5"
        title="Sales Battlecard"
        subtitle="Turn research into action — fast to scan before a customer call and easy to copy into CRM notes or Slack."
      />

      <div className="grid gap-6 lg:grid-cols-3">
        {COLUMNS.map((col) => {
          const list = items[col.key];
          return (
            <Card key={col.key} className="flex flex-col p-6">
              <span
                className={`inline-flex w-fit rounded-full px-3 py-1 text-xs font-bold ${col.tone}`}
              >
                {col.label}
              </span>
              <div className="mt-4 flex-1 space-y-3">
                {list.length === 0 ? (
                  <p className="text-sm text-[var(--muted)]">No items generated.</p>
                ) : (
                  list.map((text, i) => (
                    <BattlecardItem key={`${col.key}-${i}`} title={titleFor(col.key, text)} body={text} />
                  ))
                )}
              </div>
            </Card>
          );
        })}
      </div>

      <div className="mt-8">
        <DarkCallout>
          Copy talk track · Export battlecard · Send to Slack · Save to run history
        </DarkCallout>
      </div>
    </div>
  );
}

function titleFor(
  key: (typeof COLUMNS)[number]["key"],
  text: string,
): string {
  if (key === "objectionHandling") {
    const m = text.match(/^["'](.+?)["']/);
    return m ? `"${m[1]}"` : text.split(".")[0].slice(0, 40);
  }
  if (key === "landmines") {
    return text.split(".")[0].slice(0, 48) || "Landmine";
  }
  return text.split(".")[0].slice(0, 48) || "Talk track";
}

function BattlecardItem({ title, body }: { title: string; body: string }) {
  const copy = () => navigator.clipboard?.writeText(body).catch(() => {});

  return (
    <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-muted)] p-4">
      <p className="text-sm font-semibold text-[var(--foreground)]">{title}</p>
      <p className="mt-2 text-sm leading-relaxed text-[var(--muted)]">{body}</p>
      <div className="mt-3 flex justify-end">
        <button
          type="button"
          onClick={copy}
          className="rounded-lg bg-[var(--ink)] px-3 py-1.5 text-xs font-semibold text-white hover:bg-black"
        >
          Copy
        </button>
      </div>
    </div>
  );
}
