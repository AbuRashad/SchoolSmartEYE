import { motion } from "framer-motion";
import { AlertTriangle, ShieldAlert, Siren } from "lucide-react";

import type { AlertFeedItem } from "../types";

type LiveAlertFeedProps = {
  alerts: AlertFeedItem[];
};

const severityClasses = {
  critical: "border-critical/35 bg-critical/10 text-critical",
  warning: "border-warning/35 bg-warning/10 text-warning",
  stable: "border-safe/35 bg-safe/10 text-safe",
};

const severityIcon = {
  critical: Siren,
  warning: AlertTriangle,
  stable: ShieldAlert,
};

export function LiveAlertFeed({ alerts }: LiveAlertFeedProps) {
  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="mb-5 flex items-center justify-between">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">Live Alert Feed</p>
          <h2 className="mt-2 text-xl font-semibold text-white">Backend Alert Stream</h2>
        </div>
        <span className="rounded-full bg-cobalt px-3 py-1 text-xs uppercase tracking-[0.22em] text-white">Realtime</span>
      </div>
      <div className="space-y-3">
        {alerts.map((alert) => (
          <motion.article
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.28 }}
            key={alert.id}
            className={`rounded-[1.4rem] border px-4 py-4 ${severityClasses[alert.severity]}`}
          >
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs uppercase tracking-[0.22em] text-white/60">{alert.stream}</p>
                <h3 className="mt-1 flex items-center gap-2 text-base font-semibold text-white">
                  {(() => {
                    const Icon = severityIcon[alert.severity];
                    return <Icon className="h-4 w-4" />;
                  })()}
                  {alert.title}
                </h3>
              </div>
              <div className="flex items-center gap-2">
                <span className="rounded-full bg-white/10 px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.2em] text-white/90">
                  {alert.severity}
                </span>
                <span className="rounded-full bg-white/10 px-3 py-1 text-xs font-medium text-white/85">{alert.timestamp}</span>
              </div>
            </div>
            <p className="mt-3 text-sm text-white/82">{alert.message}</p>
          </motion.article>
        ))}
      </div>
    </section>
  );
}