import type { ReactNode } from "react";
import { cn } from "@/lib/utils";

type Tone = "neutral" | "success" | "warning" | "danger" | "info";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-slate-800 text-slate-300 ring-slate-700",
  success: "bg-emerald-500/10 text-emerald-400 ring-emerald-500/30",
  warning: "bg-amber-500/10 text-amber-400 ring-amber-500/30",
  danger: "bg-red-500/10 text-red-400 ring-red-500/30",
  info: "bg-brand-500/10 text-brand-300 ring-brand-500/30",
};

export function Badge({ tone = "neutral", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        toneClasses[tone]
      )}
    >
      {children}
    </span>
  );
}
