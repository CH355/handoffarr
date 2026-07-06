import { useMemo, useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { getPlanComparison, getRecoveryPlan } from "@/api/recoveryAgentApi";
import { ErrorState } from "@/components/ErrorState";
import { LoadingState } from "@/components/LoadingState";
import { PageContainer } from "@/components/PageContainer";

type Alternative = Record<string, unknown>;

export function RecoveryPlanDetailPage() {
  const { planId = "" } = useParams();
  const [sort, setSort] = useState("score");
  const [candidateLimit, setCandidateLimit] = useState(100);
  const plan = useQuery({ queryKey: ["recovery-agent", "plan", planId], queryFn: () => getRecoveryPlan(planId), enabled: Boolean(planId) });
  const comparison = useQuery({ queryKey: ["recovery-agent", "comparison", planId], queryFn: () => getPlanComparison(planId), enabled: Boolean(planId) });
  const alternatives = useMemo(() => [...(plan.data?.replacement_candidates ?? [])].sort((a, b) => {
    if (sort === "seeders") return Number(b.seeders ?? 0) - Number(a.seeders ?? 0);
    if (sort === "age") return Number(a.age_days ?? Infinity) - Number(b.age_days ?? Infinity);
    return Number(b.score ?? 0) - Number(a.score ?? 0);
  }), [plan.data, sort]);
  if (plan.isLoading) return <PageContainer title="Recovery Plan Detail"><LoadingState label="Loading plan" rows={8} /></PageContainer>;
  if (plan.isError || !plan.data) return <PageContainer title="Recovery Plan Detail"><ErrorState title="Plan unavailable" description="This recovery plan could not be loaded." /></PageContainer>;
  const data = plan.data;
  return <PageContainer title="Recovery Plan Detail" description={data.id}>
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap gap-2"><Link to="/recovery-agent/plans" className="text-accent">← All plans</Link><a href={`/api/recovery-agent/plans/${data.id}/export`} className="ml-auto rounded-md border border-border px-3 py-2 text-body">Export Plan JSON</a><a href={`/api/recovery-agent/plans/${data.id}/timeline/export`} className="rounded-md border border-border px-3 py-2 text-body">Export Timeline JSON</a></div>
      <Section title="Summary"><dl className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Metric label={data.media_type === "Episode" ? "Episode" : "Movie"} value={data.media_title ?? "Unknown"} />
        <Metric label="Current Release" value={data.current_release ?? "Unknown"} /><Metric label="Current Health" value={String(data.current_health.status ?? "Unknown")} />
        <Metric label="Confidence" value={data.confidence.toFixed(0)} /><Metric label="Recommendation" value={data.recommendation} />
        <Metric label="Evaluation Duration" value={`${data.evaluation_duration_ms} ms`} />
      </dl></Section>
      <Section title="Signals"><dl className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">{Object.entries(data.signals).map(([key,value]) => <Metric key={key} label={label(key)} value={String(value ?? "—")} />)}</dl></Section>
      <Section title="Policy Matches"><ul className="space-y-2">{data.policy_matches.map(policy => <li key={policy.reason} className="text-body text-text">✓ {policy.policy}<p className="text-meta text-text-muted">{policy.reason}</p></li>)}</ul></Section>
      <Section title="Confidence Breakdown"><div className="space-y-3"><p className="text-title text-text">{data.confidence.toFixed(0)}</p>{data.confidence_breakdown.map(item => <div key={item.signal} className="grid grid-cols-[140px_1fr_auto] items-center gap-3 text-body"><span>{item.signal}</span><div className="h-2 rounded-pill bg-bg"><div className="h-2 rounded-pill bg-accent" style={{width:`${item.weight}%`}} /></div><span>{item.weight}% · +{item.contribution}</span></div>)}</div></Section>
      <Section title="Reasoning"><ol className="list-decimal space-y-2 pl-5 text-body text-text">{data.reasoning.map(reason => <li key={reason}>{reason}</li>)}</ol></Section>
      <Section title="Alternatives"><div className="mb-3 flex justify-end"><select value={sort} onChange={e => setSort(e.target.value)} className="rounded-md border border-border bg-surface px-3 py-2 text-text"><option value="score">Score</option><option value="seeders">Seeders</option><option value="age">Age</option></select></div>
        <div className="overflow-x-auto"><table className="w-full min-w-[1000px] text-left text-body"><thead className="border-b border-border text-meta uppercase text-text-subtle"><tr>{["Recommended","Release","Score","Quality","Seeds","Peers","Availability","Age","Indexer","Reason"].map(x => <th key={x} className="p-3">{x}</th>)}</tr></thead><tbody className="divide-y divide-border">{alternatives.slice(0, candidateLimit).map((candidate,index) => <AlternativeRow key={`${candidate.release_name}:${index}`} candidate={candidate} />)}</tbody></table></div>
        {candidateLimit < alternatives.length && <button onClick={() => setCandidateLimit(limit => limit + 100)} className="mt-3 rounded-md border border-border px-3 py-2 text-body">Load next 100</button>}
      </Section>
      <Section title="Timeline"><ol className="relative ml-3 border-l border-border pl-6">{data.timeline.map((event,index) => <li key={`${event.type}:${index}`} className="pb-5"><span className="absolute -left-1.5 mt-1 h-3 w-3 rounded-full bg-accent" /><time className="text-meta text-text-muted">{new Date(event.timestamp).toLocaleTimeString()}</time><p className="font-semibold text-text">{event.label}</p></li>)}</ol></Section>
      <Section title="Plan Comparison">{comparison.data?.previous ? <div className="grid gap-3 sm:grid-cols-2">{Object.entries(comparison.data.changes).map(([key,change]) => <div key={key} className={`rounded-md border p-3 ${change.previous !== change.current ? "border-caution bg-caution-quiet" : "border-border"}`}><p className="text-meta uppercase text-text-muted">{label(key)}</p><p className="text-body">{String(change.previous ?? "—")} → {String(change.current ?? "—")}</p></div>)}</div> : <p className="text-body text-text-muted">No previous evaluation exists for this torrent.</p>}</Section>
    </div>
  </PageContainer>;
}

function Section({title,children}:{title:string;children:ReactNode}) { return <section className="rounded-lg bg-surface p-5 shadow-elev-1"><h2 className="mb-4 text-subtitle text-text">{title}</h2>{children}</section>; }
function Metric({label:heading,value}:{label:string;value:string}) { return <div><dt className="text-meta uppercase text-text-subtle">{heading}</dt><dd className="mt-1 text-body font-semibold text-text">{value}</dd></div>; }
function label(value:string) { return value.replaceAll("_"," ").replace(/\b\w/g, c => c.toUpperCase()); }
function AlternativeRow({candidate}:{candidate:Alternative}) { return <tr><td className="p-3">{candidate.recommended ? "✓" : "—"}</td><td className="max-w-80 p-3">{String(candidate.release_name ?? "Unknown")}</td><td className="p-3">{String(candidate.score ?? 0)}</td><td className="p-3">{String(candidate.quality ?? "—")}</td><td className="p-3">{String(candidate.seeders ?? 0)}</td><td className="p-3">{String(candidate.peers ?? 0)}</td><td className="p-3">{String(candidate.availability ?? "—")}</td><td className="p-3">{String(candidate.age_days ?? "—")}</td><td className="p-3">{String(candidate.indexer ?? "—")}</td><td className="p-3">{String(candidate.rejection_reason ?? (candidate.recommended ? "Highest accepted score" : "Lower score"))}</td></tr>; }
