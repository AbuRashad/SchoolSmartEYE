import { useMemo, useState } from "react";

import type { HeatmapCell } from "../types";

type FloorPlanHeatmapProps = {
  cells: HeatmapCell[];
  availableTimeSlots: string[];
};

const zonePositions = {
  "0-0": { label: "Gate", x: 30, y: 28, width: 150, height: 98 },
  "1-0": { label: "Corridor A", x: 220, y: 28, width: 170, height: 98 },
  "0-1": { label: "Classroom Wing", x: 30, y: 160, width: 150, height: 118 },
  "1-1": { label: "Playground", x: 220, y: 160, width: 170, height: 118 },
};

function riskToColor(risk: number) {
  if (risk >= 0.8) return "#d65a31";
  if (risk >= 0.5) return "#d8a31a";
  return "#3a7d44";
}

export function FloorPlanHeatmap({ cells, availableTimeSlots }: FloorPlanHeatmapProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedTimeSlot = availableTimeSlots[selectedIndex] ?? availableTimeSlots[0];

  const visibleCells = useMemo(
    () => cells.filter((cell) => cell.time_slot === selectedTimeSlot),
    [cells, selectedTimeSlot],
  );

  return (
    <section className="rounded-[2rem] bg-white/80 p-6 shadow-panel backdrop-blur">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-steel/60">Spatio-Temporal Risk Heatmap</p>
          <h2 className="mt-2 text-xl font-semibold text-ink">School Floor Plan Risk Overlay</h2>
          <p className="mt-2 max-w-2xl text-sm text-steel/75">
            Dynamic overlays reflect fused risk intensity from behavioral anomaly and predictive density streams.
          </p>
        </div>
        <div className="min-w-[220px] rounded-[1.3rem] bg-sand px-4 py-3">
          <label className="text-xs uppercase tracking-[0.22em] text-steel/60">Forecast Window</label>
          <input
            type="range"
            min={0}
            max={Math.max(availableTimeSlots.length - 1, 0)}
            value={selectedIndex}
            onChange={(event) => setSelectedIndex(Number(event.target.value))}
            className="mt-3 w-full accent-ink"
          />
          <p className="mt-2 text-sm font-medium text-ink">{selectedTimeSlot?.replace("T", " ")}</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_280px]">
        <div className="overflow-hidden rounded-[1.6rem] border border-steel/10 bg-[#f5f7f2] p-3">
          <svg viewBox="0 0 420 310" className="w-full">
            <rect x="12" y="12" width="396" height="286" rx="24" fill="#fdfcf9" stroke="#d7ddd4" strokeWidth="3" />
            {visibleCells.map((cell) => {
              const position = zonePositions[`${cell.x}-${cell.y}` as keyof typeof zonePositions];
              if (!position) return null;
              const fill = riskToColor(cell.risk_intensity);
              return (
                <g key={`${cell.time_slot}-${cell.x}-${cell.y}`}>
                  <rect
                    x={position.x}
                    y={position.y}
                    width={position.width}
                    height={position.height}
                    rx="20"
                    fill={fill}
                    fillOpacity={0.22 + cell.risk_intensity * 0.55}
                    stroke={fill}
                    strokeWidth="3"
                  >
                    <title>{`${position.label}: ${cell.reason} (${cell.risk_intensity.toFixed(2)})`}</title>
                  </rect>
                  <text x={position.x + 14} y={position.y + 26} className="fill-ink text-[13px] font-semibold">
                    {position.label}
                  </text>
                  <text x={position.x + 14} y={position.y + 46} className="fill-steel text-[11px]">
                    {cell.reason}
                  </text>
                  <text x={position.x + 14} y={position.y + 66} className="fill-steel text-[11px]">
                    Risk {(cell.risk_intensity * 100).toFixed(0)}%
                  </text>
                </g>
              );
            })}
          </svg>
        </div>

        <div className="space-y-3">
          {visibleCells.map((cell) => (
            <div key={`${cell.time_slot}-${cell.x}-${cell.y}-tooltip`} className="rounded-[1.4rem] border border-steel/10 bg-sand p-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <h3 className="text-sm font-semibold text-ink">{cell.label}</h3>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-steel/55">Grid {cell.x}, {cell.y}</p>
                </div>
                <span
                  className="rounded-full px-3 py-1 text-xs font-semibold text-white"
                  style={{ backgroundColor: riskToColor(cell.risk_intensity) }}
                >
                  {(cell.risk_intensity * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-3 text-sm text-steel/80">{cell.reason}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}