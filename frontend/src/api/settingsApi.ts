import { request } from "./client";

/* Typed Settings API. Protected values and arbitrary config keys are never
   represented in this client contract. */

export interface AppHealth {
  status: string;
  config_present: boolean;
}

export function getAppHealth(): Promise<AppHealth> {
  return request<AppHealth>("/api/health");
}

export interface CleanupSettings {
  enabled: boolean;
  allow_single_item_execution: boolean;
  allow_batch_execution: boolean;
  require_confirmation_phrase: boolean;
  require_batch_dry_run: boolean;
  max_items_per_request: number;
  max_batch_items: number;
}

export interface StorageSettings {
  critical_free_bytes: number;
  warning_free_bytes: number;
  completed_torrent_count: number;
  retained_bytes: number;
}

export interface SettingsResponse {
  cleanup: CleanupSettings;
  storage: StorageSettings;
  restart_required: boolean;
}

export function getSettings(): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings");
}

export function putCleanupSettings(payload: CleanupSettings): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings/cleanup", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Handoffarr-Expert-Mode": "true",
    },
    body: JSON.stringify(payload),
  });
}

export function putStorageSettings(payload: StorageSettings): Promise<SettingsResponse> {
  return request<SettingsResponse>("/api/settings/storage", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      "X-Handoffarr-Expert-Mode": "true",
    },
    body: JSON.stringify(payload),
  });
}
