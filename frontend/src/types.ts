export type AlertSeverity = "critical" | "warning" | "stable";

export type AlertFeedItem = {
  id: string;
  title: string;
  message: string;
  severity: AlertSeverity;
  stream: "coherence" | "anomaly" | "density";
  timestamp: string;
};

export type HeatmapCell = {
  x: number;
  y: number;
  time_slot: string;
  risk_intensity: number;
  reason: string;
  label: string;
};

export type HeatmapView = "live" | "prediction";

export type DashboardSnapshot = {
  schoolName: string;
  ssi: number;
  benchmark: number;
  liveAlerts: AlertFeedItem[];
  heatmapCells: HeatmapCell[];
  availableTimeSlots: string[];
  websocketStatus: "connected" | "reconnecting" | "offline";
  fetchedFromBackend: boolean;
  backendError?: string;
};

export type UnitInfo = {
  unit_id: number;
  name: string;
  category: string;
  status: "active" | "degraded" | "offline";
};

export type SSIHistoryPoint = {
  day: number;
  ssi: number;
};

export type SSIHistoryData = {
  school: string;
  period: string;
  benchmark: number;
  scores: SSIHistoryPoint[];
  average: number;
  trend: "improving" | "stable" | "declining";
};

export type DensityForecast = {
  location: string;
  predicted_density: number;
  safety_threshold: number;
  risk_level: string;
  warning: boolean;
  model: string;
};

export type SSILiveData = {
  ssi: number;
  benchmark: number;
  status: string;
  inputs: {
    anomaly_coefficient: number;
    coherence_score: number;
    attendance_discrepancy: number;
    predictive_risk_level: number;
  };
  density_forecast: DensityForecast;
  weights: Record<string, number>;
  computed_at: string;
};

export type NavPage = "dashboard" | "ssi" | "units" | "reports" | "portal";
