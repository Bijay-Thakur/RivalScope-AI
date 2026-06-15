import type {
  EvidenceConfidence,
  EvidenceItem,
  Source,
  SourceType,
} from "@/types/report";
import { ProductLabel } from "./ProductLabel";
import { EMPTY_STATE_CLASS, PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

interface EvidencePanelProps {
  evidence: EvidenceItem[];
  sources: Source[];
}

const CONFIDENCE_STYLES: Record<
  EvidenceConfidence,
  { badge: string; label: string }
> = {
  high: {
    badge: "border-amber-200 bg-amber-50 text-amber-900",
    label: "High",
  },
  medium: {
    badge: "border-stone-300 bg-stone-50 text-stone-700",
    label: "Medium",
  },
  low: {
    badge: "border-stone-200 bg-white text-stone-500",
    label: "Low",
  },
};

const SOURCE_TYPE_LABELS: Record<SourceType, string> = {
  company_page: "Company Page",
  pricing_page: "Pricing Page",
  news: "News",
  blog: "Blog",
  docs: "Docs",
  other: "Other",
};

export function EvidencePanel({ evidence, sources }: EvidencePanelProps) {
  const sourceById = new Map(sources.map((source) => [source.id, source]));

  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <div className="mb-6 sm:mb-7">
        <ProductLabel tone="bronze">Verified Evidence</ProductLabel>
        <h2 className="mt-2 text-lg font-semibold tracking-tight text-stone-900 sm:text-xl">
          Source Citations
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-stone-600">
          Claims in this brief mapped to public sources with confidence ratings.
        </p>
      </div>

      {evidence.length === 0 ? (
        <EmptyState />
      ) : (
        <ul className="space-y-3 sm:space-y-4">
          {evidence.map((item, index) => {
            const source = sourceById.get(item.sourceId);

            return (
              <li
                key={item.id}
                className="rounded-lg border border-stone-200 bg-stone-50/50 p-4 sm:p-5"
              >
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div className="flex min-w-0 flex-1 gap-3">
                    <span className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-md border border-stone-200 bg-white text-xs font-medium tabular-nums text-stone-500">
                      {index + 1}
                    </span>
                    <p className="text-[0.9375rem] leading-[1.65] text-stone-800">
                      {item.claim}
                    </p>
                  </div>
                  <ConfidenceBadge confidence={item.confidence} />
                </div>

                <div className="mt-4 border-t border-stone-200 pt-4 pl-9">
                  {source ? (
                    <div className="space-y-2">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-stone-500">
                          Source
                        </span>
                        <SourceTypeBadge sourceType={source.sourceType} />
                      </div>
                      <p className="text-sm font-medium text-stone-800">
                        {source.title}
                      </p>
                      <p className="break-all font-mono text-xs leading-relaxed text-stone-500">
                        {source.url}
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-stone-500">
                      Source not found ({item.sourceId})
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function ConfidenceBadge({ confidence }: { confidence: EvidenceConfidence }) {
  const { badge, label } = CONFIDENCE_STYLES[confidence];

  return (
    <span
      className={`inline-flex shrink-0 items-center rounded-full border px-2.5 py-1 text-xs font-medium ${badge}`}
    >
      {label} confidence
    </span>
  );
}

function SourceTypeBadge({ sourceType }: { sourceType: SourceType }) {
  return (
    <span className="inline-flex items-center rounded-md border border-stone-200 bg-white px-2 py-0.5 text-xs font-medium text-stone-600">
      {SOURCE_TYPE_LABELS[sourceType]}
    </span>
  );
}

function EmptyState() {
  return (
    <div className={EMPTY_STATE_CLASS}>
      <p className="text-sm font-medium text-stone-700">No evidence yet</p>
      <p className="mt-2 max-w-xs text-xs leading-relaxed text-stone-500">
        Verified claims and source citations appear here after the agent
        workflow completes.
      </p>
    </div>
  );
}
