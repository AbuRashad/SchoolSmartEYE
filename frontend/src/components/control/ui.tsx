import type { ReactNode } from "react";

export type Flash = (kind: "ok" | "err", message: string) => void;

export const inputCls =
  "w-full rounded-xl border border-white/10 bg-black/30 px-3 py-2 text-sm text-white outline-none transition focus:border-cobalt/60 focus:bg-black/40";

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <label className="block space-y-1">
      <span className="text-xs uppercase tracking-wider text-mist/60">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-mist/50">{hint}</span>}
    </label>
  );
}
