import { useMemo, useState } from "react";
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

export function LibraryPage() {
  const query = useLibraryData();
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState<LibraryFilter>("all");
  const [sort, setSort] = useState<LibrarySort>("recent");

  const allItems: LibraryItem[] = useMemo(
    () => (query.data?.artifacts ?? []).map(toLibraryItem),
    [query.data],
  );

  const counts = useMemo(() => {
    const c: Record<LibraryFilter, number> = {
      all: allItems.length,
      movie: 0,
      show: 0,
      music: 0,
      other: 0,
    };
    for (const item of allItems) c[item.mediaType] = (c[item.mediaType] ?? 0) + 1;
    return c;
  }, [allItems]);

  const visibleItems = useMemo(() => {
    const needle = search.trim().toLowerCase();
    const filtered = allItems.filter((item) => {
      if (filter !== "all" && item.mediaType !== filter) return false;
      if (needle && !item.title.toLowerCase().includes(needle)) return false;
      return true;
    });
    const sorted = [...filtered];
    sorted.sort((a, b) => {
      if (sort === "title_asc") return a.title.localeCompare(b.title);
      if (sort === "size_desc") return (b.sizeBytes ?? 0) - (a.sizeBytes ?? 0);
      return (b.observedAt ?? "").localeCompare(a.observedAt ?? "");
    });
    return sorted;
  }, [allItems, search, filter, sort]);

  return (
    <>
      <PageContainer title="Library">
        <div className="flex flex-col gap-4">
          <LibrarySearchInput value={search} onChange={setSearch} />
          <div className="flex flex-wrap items-center justify-between gap-3">
            <FilterChipRow value={filter} onChange={setFilter} counts={counts} />
            <SortDropdown value={sort} onChange={setSort} />
          </div>

          <Body
            isLoading={query.isLoading}
            isError={query.isError}
            onRetry={() => query.refetch()}
            totalCount={allItems.length}
            visibleItems={visibleItems}
            search={search}
          />
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
      <ul className="flex flex-col gap-2">
        {visibleItems.map((item) => (
          <li key={item.mediaId || item.title}>
            <LibraryItemRow item={item} />
          </li>
        ))}
      </ul>
      <p className="text-meta text-text-muted">
        Showing {visibleItems.length} of {totalCount}
      </p>
    </>
  );
}
