import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { getRecoveryQueue } from "@/api/recoveryAgentApi";
import { PageContainer } from "@/components/PageContainer";

export function RecoveryActivityPage() {
  const [params] = useSearchParams();
  const [status,setStatus] = useState(params.get("status") ?? "");
  const [page,setPage] = useState(1);
  const query = useQuery({
    queryKey: ["recovery-agent","queue",status,page],
    queryFn: ({signal}) => getRecoveryQueue({
      limit: 50, offset: (page - 1) * 50, status,
    }, signal),
  });
  const jobs = query.data?.jobs ?? [];
  return <PageContainer title="Recovery Activity" description="Live and historical Recovery Agent queue activity."><div className="flex flex-col gap-4">
    <div className="flex flex-wrap gap-2">{["","Queued","Running","Completed","Failed","Cancelled"].map(value=><button key={value} onClick={()=>{setStatus(value);setPage(1);}} className={`rounded-pill px-3 py-2 text-body ${status===value?"bg-accent text-accent-on":"bg-surface text-text"}`}>{value||"All"}</button>)}</div>
    <div className="overflow-x-auto rounded-lg bg-surface shadow-elev-1"><table className="w-full min-w-[800px] text-left text-body"><thead className="border-b border-border text-meta uppercase text-text-subtle"><tr>{["Job","Torrent","Status","Created","Duration","Progress","Error"].map(x=><th key={x} className="p-3">{x}</th>)}</tr></thead><tbody className="divide-y divide-border">{jobs.map(job=><tr key={job.job_id}><td className="p-3 font-mono text-meta">{job.job_id}</td><td className="p-3 font-mono text-meta">{job.torrent_hash}</td><td className="p-3">{job.status}</td><td className="p-3">{new Date(job.created_at).toLocaleString()}</td><td className="p-3">{duration(job.started_at,job.completed_at)}</td><td className="p-3">{job.status==="Completed"?"100%":job.status==="Running"?"In progress":"—"}</td><td className="p-3 text-critical">{job.error??"—"}</td></tr>)}</tbody></table></div>
    <div className="flex justify-between text-body text-text-muted"><span>{query.data?.pagination.total ?? 0} jobs</span><div className="flex gap-2"><button disabled={page===1} onClick={()=>setPage(p=>p-1)} className="rounded-md border border-border px-3 py-1 disabled:opacity-40">Previous</button><span>Page {page}</span><button disabled={!query.data?.pagination.has_more} onClick={()=>setPage(p=>p+1)} className="rounded-md border border-border px-3 py-1 disabled:opacity-40">Next</button></div></div>
  </div></PageContainer>;
}
function duration(start:string|null,end:string|null) { if(!start)return "—"; return `${Math.max(0,Math.round((Date.parse(end??new Date().toISOString())-Date.parse(start))))} ms`; }
