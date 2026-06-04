import { request } from "./client";

export interface EventsResponse {
  events: Array<Record<string, unknown>>;
}

export interface TracesResponse {
  traces: Array<Record<string, unknown>>;
}

export function getEvents(): Promise<EventsResponse> {
  return request<EventsResponse>("/api/events?limit=200");
}

export function getTraces(): Promise<TracesResponse> {
  return request<TracesResponse>("/api/traces");
}
