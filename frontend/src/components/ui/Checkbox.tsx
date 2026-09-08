import { forwardRef, type InputHTMLAttributes } from "react";
import { Check, Minus } from "lucide-react";
import { cn } from "@/lib/utils";

interface Props extends Omit<InputHTMLAttributes<HTMLInputElement>, "type"> {
  /** Visual "some but not all" state for header select-all checkboxes. */
  indeterminate?: boolean;
}

export const Checkbox = forwardRef<HTMLInputElement, Props>(
  ({ className, indeterminate, checked, disabled, ...props }, ref) => (
    <span className={cn("relative inline-flex h-4 w-4 shrink-0", className)}>
      <input
        ref={ref}
        type="checkbox"
        checked={checked}
        disabled={disabled}
        className="peer absolute inset-0 h-4 w-4 cursor-pointer appearance-none rounded border border-slate-600 bg-slate-950 transition-colors checked:border-brand-500 checked:bg-brand-600 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-950 disabled:cursor-not-allowed disabled:opacity-50"
        {...props}
      />
      <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-white opacity-0 peer-checked:opacity-100">
        {indeterminate ? <Minus className="h-3 w-3" /> : <Check className="h-3 w-3" />}
      </span>
    </span>
  )
);
Checkbox.displayName = "Checkbox";
