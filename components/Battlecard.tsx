import type { SalesBattlecard } from "@/types/report";
import { ProductLabel } from "./ProductLabel";
import { EMPTY_STATE_CLASS, PANEL_CLASS, PANEL_PADDING } from "./ui/styles";

interface BattlecardProps {
  salesBattlecard: SalesBattlecard;
}

interface BattlecardSectionConfig {
  key: keyof SalesBattlecard;
  title: string;
  description: string;
  icon: React.ReactNode;
}

const SECTIONS: BattlecardSectionConfig[] = [
  {
    key: "talkTracks",
    title: "Talk Tracks",
    description: "Opening angles and positioning statements for discovery and demo calls.",
    icon: <TalkTrackIcon />,
  },
  {
    key: "objectionHandling",
    title: "Objection Handling",
    description: "Responses when the prospect pushes back on fit, price, or switching cost.",
    icon: <ObjectionIcon />,
  },
  {
    key: "landmines",
    title: "Landmines / Watchouts",
    description: "Topics to avoid or handle carefully — credibility killers in competitive deals.",
    icon: <LandmineIcon />,
  },
];

export function Battlecard({ salesBattlecard }: BattlecardProps) {
  const isEmpty =
    salesBattlecard.talkTracks.length === 0 &&
    salesBattlecard.objectionHandling.length === 0 &&
    salesBattlecard.landmines.length === 0;

  return (
    <section className={`${PANEL_CLASS} ${PANEL_PADDING}`}>
      <div className="mb-6 sm:mb-7">
        <ProductLabel tone="gold">Sales Battlecard</ProductLabel>
        <h2 className="mt-2 text-lg font-semibold tracking-tight text-stone-900 sm:text-xl">
          Rep Playbook
        </h2>
        <p className="mt-1.5 text-sm leading-relaxed text-stone-600">
          Quick-reference cards for reps heading into a competitive evaluation.
        </p>
      </div>

      {isEmpty ? (
        <EmptyState />
      ) : (
        <div className="space-y-8 sm:space-y-10">
          {SECTIONS.map((section) => {
            const items = salesBattlecard[section.key];
            if (items.length === 0) return null;

            return (
              <div key={section.key}>
                <div className="mb-4 flex items-start gap-3">
                  <span className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-stone-200 bg-stone-50 text-stone-600">
                    {section.icon}
                  </span>
                  <div>
                    <h3 className="text-sm font-semibold text-stone-800">
                      {section.title}
                    </h3>
                    <p className="mt-0.5 text-xs leading-relaxed text-stone-500">
                      {section.description}
                    </p>
                  </div>
                </div>

                <ul className="space-y-2.5 sm:space-y-3">
                  {items.map((item, index) => (
                    <li
                      key={`${section.key}-${index}`}
                      className="flex gap-3 rounded-lg border border-stone-200 bg-stone-50/50 px-4 py-3.5 sm:px-5 sm:py-4"
                    >
                      <span
                        className="mt-2.5 h-1.5 w-1.5 shrink-0 rounded-full bg-stone-400"
                        aria-hidden="true"
                      />
                      <p className="text-[0.9375rem] leading-[1.65] text-stone-700">
                        {item}
                      </p>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

function EmptyState() {
  return (
    <div className={EMPTY_STATE_CLASS}>
      <p className="text-sm font-medium text-stone-700">No battlecard content yet</p>
      <p className="mt-2 max-w-xs text-xs leading-relaxed text-stone-500">
        Talk tracks, objection responses, and watchouts populate after the agent
        workflow completes.
      </p>
    </div>
  );
}

function TalkTrackIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 8.25h9m-9 3H12m-9.75 1.51c0 1.6 1.123 2.994 2.707 3.227 1.087.16 2.185.283 3.293.369V21l4.184-4.183a1.14 1.14 0 0 1 .778-.332 48.294 48.294 0 0 0 5.83-.498c1.585-.233 2.708-1.626 2.708-3.228V6.741c0-1.602-1.123-2.995-2.707-3.228A48.394 48.394 0 0 0 12 3c-2.392 0-4.744.175-7.043.513C3.373 3.746 2.25 5.14 2.25 6.741v6.018Z" />
    </svg>
  );
}

function ObjectionIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75 11.25 15 15 9.75m-3-7.036A11.959 11.959 0 0 1 3.598 6 11.99 11.99 0 0 0 3 9.749c0 5.592 3.824 10.29 9 11.623 5.176-1.332 9-6.03 9-11.622 0-1.31-.21-2.571-.598-3.751h-.152c-3.196 0-6.1-1.248-8.25-3.285Z" />
    </svg>
  );
}

function LandmineIcon() {
  return (
    <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" aria-hidden="true">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126ZM12 15.75h.007v.008H12v-.008Z" />
    </svg>
  );
}
