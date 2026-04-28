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

export type NavPage = "dashboard" | "ssi" | "units" | "reports" | "portal" | "analytics" | "cameras" | "control";

export type LiveCameraInfo = {
  camera_id: string;
  zone_id: string;
  label: string;
  source_url: string;
  anonymize_faces: boolean;
  status: "active" | "degraded" | "offline";
  is_running: boolean;
  last_frame_at: string | null;
  total_frames_captured: number;
  drop_rate: number;
  last_error: string | null;
};

export type AnalyticsOverview = {
  attendance_rate: number;
  total_students: number;
  active_cameras: number;
  total_units: number;
  incidents_today: number;
  incidents_week: number;
  avg_crowd_density: number;
  peak_density_zone: string;
  uptime_percent: number;
  alerts_resolved_today: number;
  patrol_efficiency: number;
  compliance_score: number;
};

export type ReportItem = {
  id: string;
  title: string;
  type: "operational" | "analytical" | "supervisory" | "ministerial";
  period: string;
  generated_at: string;
  status: "ready" | "generating" | "scheduled";
};

export type ReportStats = {
  weekly_incidents_by_day: { day: string; count: number }[];
  top_risk_zones: { zone: string; risk: number; incidents: number }[];
  attendance_by_week: { week: string; rate: number }[];
  incident_types: { type: string; count: number; color: string }[];
};

export type PortalNotification = {
  id: string;
  type: "attendance" | "safety" | "info";
  message: string;
  time: string;
  read: boolean;
};

export type StudentPortalData = {
  name: string;
  grade: string;
  student_id: string;
  photo_initial: string;
  attendance_today: "present" | "absent" | "late";
  arrival_time: string;
  last_seen_zone: string;
  dismissal_status: string;
  safety_status: "safe" | "warning" | "unknown";
  attendance_streak: number;
  monthly_attendance: number;
  notifications: PortalNotification[];
  weekly_attendance: { day: string; present: boolean }[];
};

// ── Control Panel ────────────────────────────────────────────────────────────

export type StudentRecord = {
  student_id: string;
  name: string;
  grade: string;
  class_section: string;
  parent_id: string;
  photo_initial: string;
  is_active: boolean;
};

export type StudentCreatePayload = {
  student_id: string;
  name: string;
  grade: string;
  class_section: string;
  parent_id: string;
  photo_initial?: string;
  is_active?: boolean;
};

export type ZoneRecord = {
  zone_id: string;
  label: string;
  zone_type: string;
  capacity: number;
  floor: number;
};

export type BraceletRecord = {
  bracelet_id: string;
  student_id: string;
  student_name: string | null;
  mac_address: string;
  battery_level: number;
  is_active: boolean;
  last_seen_zone: string | null;
  last_seen_at: string | null;
  firmware_version: string;
  notes: string;
  low_battery: boolean;
};

export type BraceletCreatePayload = {
  bracelet_id: string;
  student_id: string;
  mac_address: string;
  battery_level?: number;
  firmware_version?: string;
  notes?: string;
  is_active?: boolean;
};

export type CameraCreatePayload = {
  camera_id: string;
  zone_id: string;
  label: string;
  source_url: string;
  anonymize_faces: boolean;
};

export type SystemSettings = {
  camera_max_fps: number;
  camera_jpeg_quality: number;
  camera_reconnect_seconds: number;
  camera_anonymize_faces: boolean;
  ssi_benchmark: number;
  video_ttl_hours: number;
  bracelet_low_battery_percent: number;
};

// ── Student Profile ──────────────────────────────────────────────────────────

export type AttendanceDay = {
  date: string;
  status: "present" | "absent" | "late" | "unknown";
  arrival_time: string | null;
  departure_time: string | null;
  last_seen_zone: string | null;
  last_seen_zone_label: string | null;
};

export type BraceletSummary = {
  bracelet_id: string;
  mac_address: string;
  battery_level: number;
  is_active: boolean;
  last_seen_zone: string | null;
  last_seen_zone_label: string | null;
  last_seen_at: string | null;
  firmware_version: string;
  notes: string;
  low_battery: boolean;
};

export type ProfileNotification = {
  notification_id: string;
  message: string;
  notification_type: string;
  sent_at: string;
  read: boolean;
};

export type StudentProfile = {
  student_id: string;
  name: string;
  grade: string;
  class_section: string;
  parent_id: string;
  photo_initial: string;
  is_active: boolean;

  safety_status: "safe" | "warning" | "critical" | "unknown";
  today_status: "present" | "absent" | "late" | "unknown";
  arrival_time: string | null;
  departure_time: string | null;
  last_seen_zone: string | null;
  last_seen_zone_label: string | null;

  attendance_streak: number;
  monthly_attendance_pct: number;
  last_30_days_present: number;
  last_30_days_total: number;

  weekly_attendance: AttendanceDay[];
  recent_attendance: AttendanceDay[];

  bracelet: BraceletSummary | null;
  notifications: ProfileNotification[];
  unread_notifications: number;

  open_incidents_in_last_zone: number;
};

export type StudentUpdatePayload = {
  name?: string;
  grade?: string;
  class_section?: string;
  parent_id?: string;
  photo_initial?: string;
  is_active?: boolean;
};
