interface FormFieldProps {
  id: string;
  label: string;
  placeholder?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  disabled?: boolean;
}

export function FormField({
  id,
  label,
  placeholder,
  value,
  onChange,
  required = false,
  disabled = false,
}: FormFieldProps) {
  return (
    <div className="space-y-2">
      <label
        htmlFor={id}
        className="block text-sm font-medium text-stone-700"
      >
        {label}
        {required && <span className="ml-1 text-amber-700">*</span>}
      </label>
      <input
        id={id}
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className="w-full rounded-lg border border-stone-300 bg-white px-4 py-2.5 text-sm text-stone-900 placeholder:text-stone-400 transition-colors hover:border-stone-400 focus:border-amber-700 focus:outline-none focus:ring-2 focus:ring-amber-700/15 disabled:cursor-not-allowed disabled:bg-stone-50 disabled:opacity-60"
      />
    </div>
  );
}
