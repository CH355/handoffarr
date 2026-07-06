import { useDeferredValue, useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { getRecoveryHistory } from "@/api/recoveryAgentApi";
import { PageContainer } from "@/components/PageContainer";

export function RecoveryHistoryPage() {
  const [search,setSearch] = useState(""); const [type,setType] = useState(""); const [recommendation,setRecommendation] = useState(""); const [confidence,setConfidence] = useState(""); const [health,setHealth] = useState(""); const [date,setDate] = useState(""); const [status,setStatus] = useState("");
  const [page,setPage] = useState(1);
  const deferredSearch = useDeferredValue(search);
  useEffect(() => setPage(1), [deferredSearch, type, recommendation, confidence, health, date, status]);
  const history = useQuery({
    queryKey: ["recovery-agent", "history", page, deferredSearch, type, recommendation, confidence, health, date, status],
    queryFn: ({signal}) => getRecoveryHistory({
      limit: 50, offset: (page - 1) * 50, search: deferredSearch,
      media_type: type, recommendation, min_confidence: confidence,
      health, date, status,
    }, signal),
  });
  const rows = history.data?.history ?? [];
  return <PageContainer title="Recovery History" description="Searchable, append-only evaluation history."><div className="flex flex-col gap-4">
    <div className="grid gap-2 rounded-lg bg-surface p-4 shadow-elev-1 sm:grid-cols-2 lg:grid-cols-7"><input placeholder="Search" value={search} onChange={e=>setSearch(e.target.value)} className="rounded-md border border-border bg-surface p-2 text-text"/><Select value={type} set={setType} options={["Movie","Episode"]} label="All media"/><Select value={recommendation} set={setRecommendation} options={["Replace","Monitor","None"]} label="All recommendations"/><input type="number" placeholder="Min confidence" value={confidence} onChange={e=>setConfidence(e.target.value)} className="rounded-md border border-border bg-surface p-2 text-text"/><Select value={health} set={setHealth} options={["dead","stalled","downloading","healthy"]} label="All health"/><Select value={status} set={setStatus} options={["Proposed"]} label="All statuses"/><input type="date" value={date} onChange={e=>setDate(e.target.value)} className="rounded-md border border-border bg-surface p-2 text-text"/></div>
    <a href="/api/recovery-agent/history/export" className="self-end rounded-md border border-border px-3 py-2 text-body">Export CSV</a>
    <div className="overflow-x-auto rounded-lg bg-surface shadow-elev-1"><table className="w-full min-w-[900px] text-left text-body"><thead className="border-b border-border text-meta uppercase text-text-subtle"><tr>{["Timestamp","Media","Type","Health","Recommendation","Confidence","Candidates","Duration","Status"].map(x=><th key={x} className="p-3">{x}</th>)}</tr></thead><tbody className="divide-y divide-border">{rows.map(entry => <tr key={entry.history_id}><td className="p-3">{new Date(entry.timestamp).toLocaleString()}</td><td className="p-3">{entry.media_title ?? entry.torrent_hash}</td><td className="p-3">{entry.media_type ?? "Unknown"}</td><td className="p-3">{String(entry.health.status ?? "Unknown")}</td><td className="p-3">{entry.recommendation}</td><td className="p-3">{entry.confidence}</td><td className="p-3">{entry.candidate_count}</td><td className="p-3">{entry.evaluation_duration_ms} ms</td><td className="p-3">{entry.plan_status ?? "Stored"}</td></tr>)}</tbody></table></div>
    <div className="flex justify-between text-body text-text-muted"><span>{history.data?.pagination.total ?? 0} evaluations</span><div className="flex gap-2"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="rounded-md border border-border px-3 py-1 disabled:opacity-40">Previous</button><span>Page {page}</span><button disabled={!history.data?.pagination.has_more} onClick={()=>setPage(p=>p+1)} className="rounded-md border border-border px-3 py-1 disabled:opacity-40">Next</button></div></div>
  </div></PageContainer>;
}
function Select({value,set,options,label}:{value:string;set:(v:string)=>void;options:string[];label:string}) { return <select value={value} onChange={e=>set(e.target.value)} className="rounded-md border border-border bg-surface p-2 text-text"><option value="">{label}</option>{options.map(x=><option key={x}>{x}</option>)}</select>; }
