import { REPORT_TYPE_OPTIONS } from "@/data/constants";
import type { ReportType } from "@/types";

interface ReportTypeSelectProps {
  value: ReportType;
  onChange: (value: ReportType) => void;
  disabled?: boolean;
}

export function ReportTypeSelect({
  value,
  onChange,
  disabled = false,
}: ReportTypeSelectProps) {
  const selected = REPORT_TYPE_OPTIONS.find((opt) => opt.value === value);

  return (
    <div className="space-y-2">
      <label
        htmlFor="reportType"
        className="block text-sm font-medium text-neutral-300"
      >
        Report Type
        <span className="ml-1 text-amber-400">*</span>
      </label>
      <select
        id="reportType"
        value={value}
        onChange={(e) => onChange(e.target.value as ReportType)}
        disabled={disabled}
        className="w-full rounded-lg border border-neutral-700 bg-neutral-800/60 px-4 py-2.5 text-sm text-neutral-100 transition-colors hover:border-neutral-600 focus:border-amber-500 focus:outline-none focus:ring-2 focus:ring-amber-500/20 disabled:cursor-not-allowed disabled:bg-neutral-900 disabled:opacity-60"
      >
        {REPORT_TYPE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value} className="bg-neutral-900 text-neutral-100">
            {option.label}
          </option>
        ))}
      </select>
      {selected && (
        <p className="text-xs leading-relaxed text-neutral-500">
          {selected.description}
        </p>
      )}
    </div>
  );
}
