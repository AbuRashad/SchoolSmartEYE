import { useEffect, useState } from "react";
import { fetchJson } from "../auth";
import type { SSILiveData, SSIHistoryData, UnitInfo, AnalyticsOverview, ReportItem, ReportStats, StudentPortalData, AgentSessionInsights, EngagementSnapshotRecord } from "../types";

const BASE = "/api/v1";

export function useSSILive() {
  const [data, setData] = useState<SSILiveData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<SSILiveData>(`${BASE}/ssi/live`)
      .then((d) => setData(d))
      .catch(() => setError("SSI live endpoint unavailable."));
  }, []);

  return { data, error };
}

export function useSSIHistory() {
  const [data, setData] = useState<SSIHistoryData | null>(null);

  useEffect(() => {
    fetchJson<SSIHistoryData>(`${BASE}/ssi/history`)
      .then((d) => setData(d))
      .catch(() => null);
  }, []);

  return data;
}

export function useUnits() {
  const [units, setUnits] = useState<UnitInfo[]>([]);

  useEffect(() => {
    fetchJson<UnitInfo[]>(`${BASE}/units`)
      .then((d) => setUnits(d))
      .catch(() => null);
  }, []);

  return units;
}

export function useAnalyticsOverview() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<AnalyticsOverview>(`${BASE}/analytics/overview`)
      .then((d) => setData(d))
      .catch(() => setError("Analytics endpoint unavailable."));
  }, []);

  return { data, error };
}

export function useReportsList() {
  const [data, setData] = useState<ReportItem[]>([]);

  useEffect(() => {
    fetchJson<ReportItem[]>(`${BASE}/reports/list`)
      .then((d) => setData(d))
      .catch(() => null);
  }, []);

  return data;
}

export function useReportsStats() {
  const [data, setData] = useState<ReportStats | null>(null);

  useEffect(() => {
    fetchJson<ReportStats>(`${BASE}/reports/stats`)
      .then((d) => setData(d))
      .catch(() => null);
  }, []);

  return data;
}

export function useStudentPortal() {
  const [data, setData] = useState<StudentPortalData | null>(null);

  useEffect(() => {
    fetchJson<StudentPortalData>(`${BASE}/portal/student`)
      .then((d) => setData(d))
      .catch(() => null);
  }, []);

  return data;
}

export function useAgentInsights() {
  const [data, setData] = useState<AgentSessionInsights | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchJson<AgentSessionInsights>(`${BASE}/agent/insights`)
      .then((d) => setData(d))
      .catch(() => setError("Agent insights endpoint unavailable."));
  }, []);

  return { data, error };
}

export function useStudentBehavioralHistory(studentId: string, days = 30) {
  const [data, setData] = useState<EngagementSnapshotRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchJson<EngagementSnapshotRecord[]>(`${BASE}/students/${encodeURIComponent(studentId)}/behavioral-history?days=${days}`)
      .then((d) => setData(d))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [studentId, days]);

  return { data, loading, error };
}
