import type { SSILiveData } from "../types";

type Props = { data: SSILiveData };

const INPUTS = [
  { key: "anomaly_coefficient", label: "Anomaly Coefficient", desc: "SBM anomaly from Unit 05", invert: true },
  { key: "coherence_score", label: "Coherence Score", desc: "CBC alignment from Unit 06", invert: false },
  { key: "attendance_discrepancy", label: "Attendance Discrepancy", desc: "Gap from Unit 08", invert: true },
  { key: "predictive_risk_level", label: "Predictive Risk Level", desc: "Density forecast from Unit 07", invert: true },
] as const;

const WEIGHTS = [
  { key: "w1_anomaly", label: "W1 – Anomaly" },
  { key: "w2_coherence", label: "W2 – Coherence" },
  { key: "w3_attendance", label: "W3 – Attendance" },
  { key: "w4_density", label: "W4 – Density" },
];

function barColor(value: number, isRisk: boolean): string {
  const risk = isRisk ? value : 1 - value;
  if (risk >= 0.7) return "#e84d5b";
  if (risk >= 0.4) return "#ffb84d";
  return "#46c37b";
}

export function SSILivePanel({ data }: Props) {
  const ssiColor = data.ssi >= data.benchmark ? "#46c37b" : data.ssi >= data.benchmark - 10 ? "#ffb84d" : "#e84d5b";

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {/* SSI Score Card */}
      <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/55">Live Computed SSI</p>
        <div className="mt-4 flex items-end gap-4">
          <span className="text-7xl font-bold leading-none" style={{ color: ssiColor }}>{data.ssi}</span>
          <div className="mb-1">
            <p className="text-sm text-mist/60">/ 100</p>
            <p className="text-xs text-mist/40">Benchmark: {data.benchmark}</p>
          </div>
        </div>
        <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-white/10">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${data.ssi}%`, backgroundColor: ssiColor }}
          />
        </div>
        <p className="mt-3 text-sm text-mist/60">
          Status: <span className="font-medium text-white">{data.status.replace("_", " ")}</span>
        </p>
        <p className="mt-1 text-xs text-mist/40">Computed at {data.computed_at.replace("T", " ")}</p>

        {/* Density Forecast Badge */}
        <div className={`mt-5 rounded-[1.2rem] border px-4 py-3 ${data.density_forecast.warning ? "border-critical/35 bg-critical/10" : "border-safe/35 bg-safe/10"}`}>
          <p className="text-[10px] uppercase tracking-[0.22em] text-white/55">15-min Density Forecast · {data.density_forecast.model}</p>
          <div className="mt-2 flex items-center justify-between">
            <span className="text-sm text-white">
              {data.density_forecast.location} — {(data.density_forecast.predicted_density * 100).toFixed(1)}% density
            </span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase text-white ${data.density_forecast.warning ? "bg-critical" : "bg-safe"}`}>
              {data.density_forecast.risk_level}
            </span>
          </div>
        </div>
      </section>

      {/* Input Signals */}
      <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
        <p className="text-xs uppercase tracking-[0.28em] text-mist/55">Input Signals</p>
        <h2 className="mt-2 text-xl font-semibold text-white">SSI Component Breakdown</h2>
        <div className="mt-5 space-y-4">
          {INPUTS.map(({ key, label, desc, invert }) => {
            const value = data.inputs[key];
            const fill = barColor(value, invert);
            return (
              <div key={key}>
                <div className="flex items-center justify-between text-sm">
                  <div>
                    <span className="font-medium text-white">{label}</span>
                    <span className="ml-2 text-xs text-mist/45">{desc}</span>
                  </div>
                  <span className="font-semibold" style={{ color: fill }}>{(value * 100).toFixed(1)}%</span>
                </div>
                <div className="mt-1.5 h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${value * 100}%`, backgroundColor: fill }}
                  />
                </div>
              </div>
            );
          })}
        </div>

        <div className="mt-6 border-t border-white/10 pt-4">
          <p className="text-xs uppercase tracking-[0.22em] text-mist/45">Weight Distribution</p>
          <div className="mt-3 flex gap-2">
            {WEIGHTS.map(({ key, label }) => (
              <div key={key} className="flex-1 rounded-[1rem] border border-white/10 bg-white/5 p-2 text-center">
                <p className="text-[10px] text-mist/45">{label}</p>
                <p className="mt-1 text-sm font-semibold text-white">{((data.weights[key] ?? 0) * 100).toFixed(0)}%</p>
              </div>
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
