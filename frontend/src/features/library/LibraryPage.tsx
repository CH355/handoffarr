import { useEffect, useMemo, useState } from "react";
import { Outlet } from "react-router-dom";
import { PageContainer } from "@/components/PageContainer";
import { LoadingState } from "@/components/LoadingState";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { LibrarySearchInput } from "./components/LibrarySearchInput";
import { FilterChipRow, type LibraryFilter } from "./components/FilterChipRow";
import { SortDropdown, type LibrarySort } from "./components/SortDropdown";
import { LibraryItemRow } from "./components/LibraryItemRow";
import { useLibraryData } from "./hooks/useLibraryData";
import { toLibraryItem, type LibraryItem } from "./types";
import { AuditProfiler, auditMark, measureSync, useRouteAudit } from "@/perf/audit";

export function LibraryPage() {
  const query = useLibraryData();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<LibraryFilter>("all");
  const [sort, setSort] = useState<LibrarySort>("recent");
  useRouteAudit("Library", !query.isLoading, {
    query_status: query.status,
    artifact_count: query.data?.artifacts?.length,
  });

  const allItems: LibraryItem[] = useMemo(
    () =>
      measureSync(
        "transform",
        "Library.mapArtifacts",
        () => (query.data?.artifacts ?? []).map(toLibraryItem),
        { input_count: query.data?.artifacts?.length ?? 0 },
      ),
    [query.data],
  );

  const counts = useMemo(() => {
    return measureSync("transform", "Library.countByType", () => {
      const c: Record<LibraryFilter, number> = {
        all: allItems.length,
        movie: 0,
        show: 0,
        music: 0,
        other: 0,
      };
      for (const item of allItems) c[item.mediaType] = (c[item.mediaType] ?? 0) + 1;
      return c;
    }, { input_count: allItems.length });
  }, [allItems]);

  const visibleItems = useMemo(() => {
    return measureSync("transform", "Library.filterSort", () => {
      const needle = search.trim().toLowerCase();
      const filterStartedAt = performance.now();
      const filtered = allItems.filter((item) => {
        if (filter !== "all" && item.mediaType !== filter) return false;
        if (needle && !item.title.toLowerCase().includes(needle)) return false;
        return true;
      });
      const sortStartedAt = performance.now();
      const sorted = [...filtered];
      sorted.sort((a, b) => {
        if (sort === "title_asc") return a.title.localeCompare(b.title);
        if (sort === "size_desc") return (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
        return (b.observedAt ?? "").localeCompare(a.observedAt ?? "");
      });
      auditMark("payload_processing", "Library.filterSort.breakdown", {
        input_count: allItems.length,
        filtered_count: filtered.length,
        filter_ms: sortStartedAt - filterStartedAt,
        sort_ms: performance.now() - sortStartedAt,
        search_length: search.length,
        filter,
        sort,
      });
      return sorted;
    }, { input_count: allItems.length });
  }, [allItems, search, filter, sort]);

  return (
    <>
      <PageContainer title="Library">
        <div className="flex flex-col gap-4">
          <AuditProfiler id="Library.SearchInput">
            <LibrarySearchInput value={search} onChange={setSearch} />
          </AuditProfiler>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <AuditProfiler id="Library.FilterChipRow">
              <FilterChipRow value={filter} onChange={setFilter} counts={counts} />
            </AuditProfiler>
            <AuditProfiler id="Library.SortDropdown">
              <SortDropdown value={sort} onChange={setSort} />
            </AuditProfiler>
          </div>

          <AuditProfiler id="Library.Body">
            <Body
              isLoading={query.isLoading}
              isError={query.isError}
              onRetry={() => query.refetch()}
              totalCount={allItems.length}
              visibleItems={visibleItems}
              search={search}
            />
          </AuditProfiler>
        </div>
      </PageContainer>
      {/* Item Detail mounts here as a drawer on ≥md; the route renders a
          full-screen surface below md. */}
      <Outlet />
    </>
  );
}

interface BodyProps {
  isLoading: boolean;
  isError: boolean;
  onRetry: () => void;
  totalCount: number;
  visibleItems: LibraryItem[];
  search: string;
}

function Body({
  isLoading,
  isError,
  onRetry,
  totalCount,
  visibleItems,
  search,
}: BodyProps) {
  if (isLoading) return <LoadingState label="Loading library" rows={6} />;
  if (isError) {
    return (
      <ErrorState
        title="Couldn't load your library"
        description="The library feed is unreachable right now. Try again shortly."
        action={
          <button
            type="button"
            onClick={onRetry}
            className="rounded-md bg-surface px-3 py-1.5 text-meta text-text shadow-elev-1 hover:bg-surface-raised focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent focus-visible:ring-offset-2 focus-visible:ring-offset-bg"
          >
            Try again
          </button>
        }
      />
    );
  }
  if (totalCount === 0) {
    return (
      <EmptyState
        title="Your library is empty"
        description="As items are imported, they will appear here."
      />
    );
  }
  if (visibleItems.length === 0) {
    return (
      <EmptyState
        title="No matches"
        description={
          search
            ? `Nothing in your library matches "${search}".`
            : "No items match the current filter."
        }
      />
    );
  }
  return (
    <>
      <WindowedLibraryList items={visibleItems} />
      <p className="text-meta text-text-muted">
        Showing {visibleItems.length} of {totalCount}
      </p>
    </>
  );
}

function WindowedLibraryList({ items }: { items: LibraryItem[] }) {
  const [limit, setLimit] = useState(100);
  useEffect(() => setLimit(100), [items]);
  const rendered = items.slice(0, limit);
  return (
    <>
      <ul className="flex flex-col gap-2">
        {rendered.map((item) => (
          <li key={item.mediaId || item.title}>
            <AuditProfiler id="Library.LibraryItemRow">
              <LibraryItemRow item={item} />
            </AuditProfiler>
          </li>
        ))}
      </ul>
      {rendered.length < items.length ? (
        <button
          type="button"
          onClick={() => setLimit((value) => value + 100)}
          className="self-start rounded-md border border-border px-4 py-2 text-body text-text"
        >
          Load next 100
        </button>
      ) : null}
    </>
  );
}
