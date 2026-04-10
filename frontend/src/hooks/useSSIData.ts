import { useEffect, useState } from "react";
import type { SSILiveData, SSIHistoryData, UnitInfo } from "../types";

const BASE = "http://127.0.0.1:8000/api/v1";

export function useSSILive() {
  const [data, setData] = useState<SSILiveData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${BASE}/ssi/live`)
      .then((r) => r.json())
      .then((d) => setData(d as SSILiveData))
      .catch(() => setError("SSI live endpoint unavailable."));
  }, []);

  return { data, error };
}

export function useSSIHistory() {
  const [data, setData] = useState<SSIHistoryData | null>(null);

  useEffect(() => {
    fetch(`${BASE}/ssi/history`)
      .then((r) => r.json())
      .then((d) => setData(d as SSIHistoryData))
      .catch(() => null);
  }, []);

  return data;
}

export function useUnits() {
  const [units, setUnits] = useState<UnitInfo[]>([]);

  useEffect(() => {
    fetch(`${BASE}/units`)
      .then((r) => r.json())
      .then((d) => setUnits(d as UnitInfo[]))
      .catch(() => null);
  }, []);

  return units;
}
