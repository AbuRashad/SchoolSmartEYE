import { useMemo, useState } from "react";
import { Clock3, MapPinned } from "lucide-react";

import type { HeatmapCell } from "../types";

type RiskHeatmapProps = {
  cells: HeatmapCell[];
  availableTimeSlots: string[];
};

const floorPlan = {
  "0-0": { label: "Main Gate", x: 26, y: 26, width: 152, height: 96 },
  "1-0": { label: "Corridor A", x: 206, y: 26, width: 178, height: 96 },
  "0-1": { label: "Learning Commons", x: 26, y: 152, width: 152, height: 122 },
  "1-1": { label: "Playground", x: 206, y: 152, width: 178, height: 122 },
};

function riskColor(risk: number) {
  const red = Math.round(55 + risk * 177);
  const green = Math.round(192 - risk * 120);
  return `rgb(${red}, ${green}, 90)`;
}

function viewLabel(slot: string) {
  return slot === "live" ? "Live View" : "15-min Prediction View";
}

export function RiskHeatmap({ cells, availableTimeSlots }: RiskHeatmapProps) {
  const [selectedIndex, setSelectedIndex] = useState(0);
  const selectedSlot = availableTimeSlots[selectedIndex] ?? availableTimeSlots[0] ?? "live";

  const visibleCells = useMemo(
    () => cells.filter((cell) => cell.time_slot === selectedSlot),
    [cells, selectedSlot],
  );

  return (
    <section className="rounded-[2rem] border border-white/10 bg-panel/90 p-6 shadow-panel backdrop-blur">
      <div className="mb-5 flex flex-wrap items-start justify-between gap-5">
        <div>
          <p className="text-xs uppercase tracking-[0.28em] text-mist/55">Risk Heatmap</p>
          <h2 className="mt-2 text-xl font-semibold text-white">SVG School Floor Plan</h2>
          <p className="mt-2 max-w-2xl text-sm text-mist/75">
            Heatmap cells are mapped from the backend `generate_heatmap_data` API and fused into live versus 15-minute predictive overlays.
          </p>
        </div>
        <div className="rounded-[1.4rem] border border-white/10 bg-white/5 px-4 py-3 text-mist">
          <div className="flex items-center gap-2 text-xs uppercase tracking-[0.24em] text-mist/60">
            <Clock3 className="h-4 w-4" />
            Time Slider
          </div>
          <p className="mt-2 text-sm font-medium text-white">{viewLabel(selectedSlot)}</p>
        </div>
      </div>

      <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
        <div className="rounded-[1.6rem] border border-white/10 bg-[#081222] p-4">
          <svg viewBox="0 0 410 300" className="w-full">
            <rect x="8" y="8" width="394" height="284" rx="24" fill="#0a172c" stroke="#1f4678" strokeWidth="2.5" />
            {visibleCells.map((cell) => {
              const box = floorPlan[`${cell.x}-${cell.y}` as keyof typeof floorPlan];
              if (!box) {
                return null;
              }
              const fill = riskColor(cell.risk_intensity);
              return (
                <g key={`${cell.time_slot}-${cell.x}-${cell.y}`}>
                  <rect
                    x={box.x}
                    y={box.y}
                    width={box.width}
                    height={box.height}
                    rx="18"
                    fill={fill}
                    fillOpacity={0.18 + cell.risk_intensity * 0.65}
                    stroke={fill}
                    strokeWidth="2.5"
                  >
                    <title>{`${box.label}: ${cell.reason} | ${Math.round(cell.risk_intensity * 100)}%`}</title>
                  </rect>
                  <text x={box.x + 14} y={box.y + 24} className="fill-white text-[12px] font-semibold">
                    {box.label}
                  </text>
                  <text x={box.x + 14} y={box.y + 46} className="fill-[#a9c2e8] text-[11px]">
                    {cell.reason}
                  </text>
                </g>
              );
            })}
          </svg>

          <div className="mt-5 rounded-[1.2rem] border border-white/10 bg-white/5 px-4 py-4">
            <div className="flex items-center justify-between gap-3 text-sm text-mist/75">
              <span>{viewLabel(selectedSlot)}</span>
              <span>{selectedIndex + 1}/{Math.max(availableTimeSlots.length, 1)}</span>
            </div>
            <input
              type="range"
              min={0}
              max={Math.max(availableTimeSlots.length - 1, 0)}
              value={selectedIndex}
              onChange={(event) => setSelectedIndex(Number(event.target.value))}
              className="mt-3 w-full accent-sky"
            />
            <div className="mt-2 flex justify-between text-xs text-mist/55">
              <span>Live View</span>
              <span>15-min Prediction View</span>
            </div>
          </div>
        </div>

        <div className="space-y-3">
          {visibleCells.map((cell) => (
            <div key={`${cell.time_slot}-${cell.x}-${cell.y}-card`} className="rounded-[1.4rem] border border-white/10 bg-white/5 p-4 text-mist">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2 text-sm font-semibold text-white">
                    <MapPinned className="h-4 w-4 text-sky" />
                    {cell.label}
                  </div>
                  <p className="mt-1 text-xs uppercase tracking-[0.18em] text-mist/50">Cell {cell.x}, {cell.y}</p>
                </div>
                <span
                  className="rounded-full px-3 py-1 text-xs font-semibold text-night"
                  style={{ backgroundColor: riskColor(cell.risk_intensity) }}
                >
                  {(cell.risk_intensity * 100).toFixed(0)}%
                </span>
              </div>
              <p className="mt-3 text-sm text-mist/80">{cell.reason}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}