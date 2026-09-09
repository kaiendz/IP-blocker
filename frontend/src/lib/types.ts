export type UserRole = "admin" | "analyst" | "viewer";

export interface Me {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
}

export interface UserOut {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
}

export type LogSource = "device_api" | "forticloud";

export interface DeviceOut {
  id: string;
  name: string;
  host: string;
  port: number;
  vdom: string;
  verify_tls: boolean;
  site_tag: string;
  poll_enabled: boolean;
  log_source: LogSource;
  forticloud_credential_id: string | null;
  forticloud_serial: string;
  last_polled_at: string | null;
  last_poll_status: string;
  created_at: string;
}

export interface ForticloudCredentialOut {
  id: string;
  name: string;
  api_gateway: string;
  created_at: string;
}

export interface AuthEventOut {
  id: string;
  device_id: string;
  event_time: string;
  src_ip: string;
  username: string;
  vpn_type: string;
  action: string;
  reason_text: string;
}

export type BlacklistReason = "brute_force" | "threat_intel" | "manual";
export type BlacklistStatus = "active" | "expired" | "removed";

export interface BlacklistOut {
  id: string;
  ip_or_cidr: string;
  reason_type: BlacklistReason;
  reason_detail: string;
  source_name: string;
  device_id: string | null;
  created_by: string;
  created_at: string;
  expires_at: string | null;
  status: BlacklistStatus;
  hit_count: number;
}

export interface AllowlistOut {
  id: string;
  ip_or_cidr: string;
  note: string;
  created_by: string;
  created_at: string;
}

export type ThreatIntelFormat = "plain_ip_list" | "csv" | "json";

export interface ThreatIntelSourceOut {
  id: string;
  name: string;
  url: string;
  format: ThreatIntelFormat;
  enabled: boolean;
  refresh_interval_minutes: number;
  last_fetch_at: string | null;
  last_fetch_status: string;
  indicator_count: number;
}

export interface DetectionRuleOut {
  id: string;
  name: string;
  scope: string;
  device_id: string | null;
  event_types: string[];
  threshold_count: number;
  window_minutes: number;
  ttl_hours: number;
  enabled: boolean;
}

export interface AzurePublishConfigOut {
  container_name: string;
  blob_prefix: string;
  chunk_size: number;
  sas_expiry_days: number;
  publish_interval_minutes: number;
  generate_sas: boolean;
  enabled: boolean;
  has_connection_string: boolean;
  has_sas_url: boolean;
}

export interface PublishedFeedPartOut {
  part_index: number;
  blob_name: string;
  entry_count: number;
  blob_url: string;
  sas_expires_at: string | null;
  updated_at: string;
}

export interface AuditLogOut {
  id: string;
  actor_label: string;
  action: string;
  target_type: string;
  target_id: string;
  detail: Record<string, unknown>;
  ip_address: string;
  created_at: string;
}

export interface DashboardStats {
  active_blacklist_count: number;
  blacklist_by_reason: Record<string, number>;
  devices_total: number;
  devices_healthy: number;
  events_last_24h: number;
  top_offenders_last_24h: { src_ip: string; fail_count: number }[];
  published_parts: number;
  published_entries: number;
  threat_intel_sources_enabled: number;
}

export interface Page<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}
