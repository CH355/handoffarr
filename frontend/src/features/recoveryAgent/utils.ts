import type { RecoveryPlan, TimelineEvent } from "@/api/recoveryAgentApi";

export type PlanSort = "created" | "confidence" | "media" | "recommendation";

export function filterPlans(
  plans: RecoveryPlan[],
  search: string,
  recommendation: string,
): RecoveryPlan[] {
  const needle = search.trim().toLowerCase();
  return plans.filter(
    (plan) =>
      (!recommendation || plan.recommendation === recommendation) &&
      (!needle ||
        `${plan.id} ${plan.media_title ?? ""} ${plan.current_release ?? ""} ${plan.torrent_hash}`
          .toLowerCase()
          .includes(needle)),
  );
}

export function sortPlans(plans: RecoveryPlan[], sort: PlanSort): RecoveryPlan[] {
  return [...plans].sort((left, right) => {
    if (sort === "confidence") return right.confidence - left.confidence;
    if (sort === "media")
      return (left.media_title ?? "").localeCompare(right.media_title ?? "");
    if (sort === "recommendation")
      return left.recommendation.localeCompare(right.recommendation);
    return Date.parse(right.created_at) - Date.parse(left.created_at);
  });
}

export function timelineLabels(events: TimelineEvent[]): string[] {
  return events.map((event) => event.label);
}
