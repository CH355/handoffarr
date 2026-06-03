import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { RecentlyAddedRow } from "./RecentlyAddedRow";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import type { ImportsResponse } from "@/api/importsApi";

interface RecentlyAddedSectionProps {
  state: {
    data: ImportsResponse | undefined;
    isLoading: boolean;
    isError: boolean;
  };
}

export function RecentlyAddedSection({ state }: RecentlyAddedSectionProps) {
  return (
    <section aria-labelledby="recently-added-heading" className="flex flex-col gap-3">
      <header className="flex items-end justify-between gap-3">
        <h2 id="recently-added-heading" className="text-subtitle text-text">
          Recently added
        </h2>
        <Link
          to="/library"
          className="inline-flex items-center gap-1 rounded-sm text-meta text-text-muted transition-colors duration-fast hover:text-text focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
        >
          View
          <ArrowRight size={14} aria-hidden="true" />
        </Link>
      </header>
      <Body state={state} />
    </section>
  );
}

function Body({ state }: RecentlyAddedSectionProps) {
  if (state.isLoading) return <LoadingState label="Loading recently added" rows={5} />;
  if (state.isError || !state.data) {
    return (
      <ErrorState
        title="Couldn't load recent imports"
        description="The imports feed is unreachable right now. Try again shortly."
      />
    );
  }
  const events = state.data.recent_imports.slice(0, 5);
  if (events.length === 0) {
    return (
      <EmptyState
        title="Nothing new yet"
        description="Imports will appear here as they finish."
      />
    );
  }
  return (
    <ul className="flex flex-col">
      {events.map((event, idx) => (
        <li key={`${event.media_id ?? "row"}-${idx}`}>
          <RecentlyAddedRow event={event} />
        </li>
      ))}
    </ul>
  );
}
