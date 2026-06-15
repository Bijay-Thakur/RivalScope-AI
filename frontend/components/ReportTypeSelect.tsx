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
        className="block text-sm font-medium text-stone-700"
      >
        Report Type
        <span className="ml-1 text-amber-700">*</span>
      </label>
      <select
        id="reportType"
        value={value}
        onChange={(e) => onChange(e.target.value as ReportType)}
        disabled={disabled}
        className="w-full rounded-lg border border-stone-300 bg-white px-4 py-2.5 text-sm text-stone-900 transition-colors hover:border-stone-400 focus:border-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-700/15 disabled:cursor-not-allowed disabled:bg-stone-50 disabled:opacity-60"
      >
        {REPORT_TYPE_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {selected && (
        <p className="text-xs leading-relaxed text-stone-500">
          {selected.description}
        </p>
      )}
    </div>
  );
}
