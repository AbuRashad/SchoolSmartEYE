import { useEffect, useMemo, useState } from "react";

import type { DashboardSnapshot } from "../types";
import { authFetch, getToken } from "../auth";

const disconnectedSnapshot: DashboardSnapshot = {
  schoolName: "Smart School Safety System",
  ssi: 0,
  benchmark: 75,
  websocketStatus: "offline",
  fetchedFromBackend: false,
  availableTimeSlots: ["live", "prediction_15m"],
  liveAlerts: [],
  heatmapCells: [],
  backendError: "Backend disconnected. Live data unavailable.",
};

type BackendResponse = Partial<DashboardSnapshot>;

export function useSafetyDashboardSocket(
  url = `${window.location.protocol === "https:" ? "wss:" : "ws:"}//${window.location.host}/api/v1/dashboard/ws`,
) {
  const [snapshot, setSnapshot] = useState<DashboardSnapshot>(disconnectedSnapshot);

  useEffect(() => {
    let cancelled = false;

    async function fetchDashboardState() {
      try {
        const [summaryResponse, alertsResponse, heatmapResponse] = await Promise.all([
          authFetch("/api/v1/dashboard/summary"),
          authFetch("/api/v1/dashboard/alerts"),
          authFetch("/api/v1/dashboard/heatmap"),
        ]);

        if (!summaryResponse.ok || !alertsResponse.ok || !heatmapResponse.ok) {
          throw new Error("backend unavailable");
        }

        const summary = (await summaryResponse.json()) as BackendResponse;
        const alerts = await alertsResponse.json();
        const heatmap = await heatmapResponse.json();

        if (!cancelled) {
          setSnapshot((current) => ({
            ...current,
            ...summary,
            liveAlerts: Array.isArray(alerts) ? alerts : current.liveAlerts,
            heatmapCells: Array.isArray(heatmap?.cells) ? heatmap.cells : current.heatmapCells,
            availableTimeSlots: Array.isArray(heatmap?.availableTimeSlots)
              ? heatmap.availableTimeSlots
              : current.availableTimeSlots,
            fetchedFromBackend: true,
            backendError: undefined,
          }));
        }
      } catch {
        if (!cancelled) {
          setSnapshot({
            ...disconnectedSnapshot,
            websocketStatus: "offline",
            backendError: "Backend disconnected. REST dashboard endpoints are unavailable.",
          });
        }
      }
    }

    void fetchDashboardState();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!url) {
      return undefined;
    }

    let socket: WebSocket | null = null;
    try {
      const token = getToken();
      if (!token) throw new Error("Authentication required");
      const separator = url.includes("?") ? "&" : "?";
      socket = new WebSocket(`${url}${separator}access_token=${encodeURIComponent(token)}`);

      socket.onopen = () => {
        setSnapshot((current) => ({ ...current, websocketStatus: "connected", backendError: undefined }));
      };

      socket.onclose = () => {
        setSnapshot((current) => ({
          ...current,
          websocketStatus: "reconnecting",
          backendError: current.fetchedFromBackend ? undefined : "Backend disconnected. WebSocket stream unavailable.",
        }));
      };

      socket.onerror = () => {
        setSnapshot((current) => ({
          ...current,
          websocketStatus: "offline",
          backendError: current.fetchedFromBackend ? undefined : "Backend disconnected. WebSocket stream unavailable.",
        }));
      };

      socket.onmessage = (event) => {
        try {
          const nextSnapshot = JSON.parse(event.data) as DashboardSnapshot;
          setSnapshot((current) => ({ ...current, ...nextSnapshot, fetchedFromBackend: true, backendError: undefined }));
        } catch {
          setSnapshot((current) => ({
            ...current,
            websocketStatus: "offline",
            backendError: "Dashboard stream returned malformed data.",
          }));
        }
      };
    } catch {
      setSnapshot((current) => ({
        ...current,
        websocketStatus: "offline",
        backendError: "Backend disconnected. Unable to initialize WebSocket stream.",
      }));
    }

    return () => {
      socket?.close();
    };
  }, [url]);

  return useMemo(() => snapshot, [snapshot]);
}