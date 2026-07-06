import { describe, expect, it } from "vitest";
import type { RecoveryPlan } from "@/api/recoveryAgentApi";
import { filterPlans, sortPlans, timelineLabels } from "./utils";

const plan = (overrides: Partial<RecoveryPlan>): RecoveryPlan => ({
  id: "plan-1", torrent_hash: "abc", media_id: "1", media_title: "Movie",
  media_type: "Movie", current_release: "Movie.1080p", created_at: "2026-07-06T10:00:00Z",
  status: "Proposed", current_health: { status: "dead" }, recommendation: "Replace",
  confidence: 90, reasoning: [], replacement_candidates: [], planned_action: "Replace",
  evaluation_duration_ms: 10, signals: {}, policy_matches: [],
  confidence_breakdown: [], timeline: [], ...overrides,
});

describe("Recovery Agent table utilities", () => {
  it("filters plans by search and recommendation", () => {
    const plans = [plan({}), plan({ id: "plan-2", media_title: "Episode", recommendation: "Monitor" })];
    expect(filterPlans(plans, "episode", "Monitor").map(item => item.id)).toEqual(["plan-2"]);
  });

  it("sorts plans by confidence", () => {
    const plans = [plan({ confidence: 40 }), plan({ id: "plan-2", confidence: 95 })];
    expect(sortPlans(plans, "confidence")[0]?.id).toBe("plan-2");
  });

  it("renders timeline events in persisted order", () => {
    expect(timelineLabels([
      { type: "started", label: "Evaluation started", timestamp: "2026-07-06T10:00:00Z" },
      { type: "stored", label: "Plan stored", timestamp: "2026-07-06T10:00:01Z" },
    ])).toEqual(["Evaluation started", "Plan stored"]);
  });
});
