# Sprint 8.4 Frontend Performance Rendering Audit

Date: 2026-06-12
Branch: `audit/frontend-performance-rendering`
Mode: audit only. No optimizations, redesigns, behavior changes, memoization, or virtualization were implemented.

## Measurement Method

- Production route/query/payload timings were captured from the CasaOS deployment at `http://192.168.55.12:8099`.
- React component render costs were captured from a local Vite dev build proxied to the same CasaOS API because the production React bundle did not emit `Profiler` duration events.
- Audit mode is opt-in via `?perfAudit=1` or `localStorage.handoffarr.perfAudit`.
- Raw captures:
  - `frontend-performance-audit-events.json`
  - `frontend-performance-audit-item-events.json`
  - `frontend-performance-audit-dev-events.json`
  - `frontend-performance-audit-dev-item-events.json`
  - `frontend-performance-audit-summary.json`

## Route Timing

| Route | First render | Data ready | Fully rendered | Route renders | Note |
| --- | ---: | ---: | ---: | ---: | --- |
| Home | 4.5 ms | 58,604.6 ms | 58,621.1 ms | 5 | Blocked by `/api/validation` |
| Library | 10.8 ms | 3,445.6 ms | 3,495.5 ms | 3 | Blocked by `/api/library` |
| Item Detail | 5.1 ms | 38,739.8 ms | 38,755.7 ms | 4 | Direct route `/library/309`; blocked by detail/import APIs |
| Health | 31.5 ms | 36.1 ms | 54.9 ms | 1 | Fast after cache warm |
| Settings | 3.0 ms | 26.6 ms | 42.5 ms | 2 | Fast after cache warm |
| Recover | 8.6 ms | 426.3 ms | 442.8 ms | 2 | Cleanup review is acceptable in this run |
| Diagnostics | n/a | n/a | n/a | n/a | Route is not present in current router |

## Query Timing

| Query | Count | Max | Avg | Max payload | JSON parse | Body read | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `/api/validation` | 1 | 58,559.3 ms | 58,559.3 ms | 1.0 KB | 0.1 ms | 0.2 ms | 200 |
| `/api/imports/309` | 1 | 38,670.0 ms | 38,670.0 ms | 3.5 KB | 0.1 ms | 0.1 ms | 200 |
| `/api/library/309` | 1 | 38,651.9 ms | 38,651.9 ms | 2.0 KB | 0.0 ms | 0.2 ms | 200 |
| `/api/library` | 1 | 3,388.8 ms | 3,388.8 ms | 492.2 KB | 1.3 ms | 6.2 ms | 200 |
| `/api/imports` | 1 | 730.5 ms | 730.5 ms | 244.0 KB | 0.6 ms | 2.3 ms | 200 |
| `/api/cleanup` | 1 | 721.4 ms | 721.4 ms | 903.7 KB | 3.0 ms | 685.9 ms | 200 |
| `/api/storage` | 1 | 708.4 ms | 708.4 ms | 3.0 KB | 0.0 ms | 0.2 ms | 200 |
| `/api/cleanup/review` | 1 | 393.8 ms | 393.8 ms | 624.9 KB | 3.3 ms | 7.3 ms | 200 |
| `/api/health` | 1 | 10.4 ms | 10.4 ms | 0.0 KB | 0.0 ms | 0.7 ms | 200 |
| `/api/cleanup/executions?limit=1` | 1 | 10.3 ms | 10.3 ms | 1.6 KB | 0.0 ms | 1.2 ms | 200 |

## Rerender Counts

Production route-level render counts:

| Scope | Render events | Max render count |
| --- | ---: | ---: |
| `route:Home` | 5 | 5 |
| `route:Item Detail` | 4 | 4 |
| `route:Library` | 3 | 2 |
| `route:Settings` | 2 | 2 |
| `route:Recover` | 2 | 2 |
| `route:Health` | 1 | 1 |

Dev build render counts are higher because React dev mode adds overhead. The highest counts were `route:Home` and `route:Item Detail` at 9 renders each.

## Largest Payloads

| Query | Payload | Duration |
| --- | ---: | ---: |
| `/api/cleanup` | 903.7 KB | 721.4 ms |
| `/api/cleanup/review` | 624.9 KB | 393.8 ms |
| `/api/library` | 492.2 KB | 3,388.8 ms |
| `/api/imports` | 244.0 KB | 730.5 ms |
| `/api/imports/309` | 3.5 KB | 38,670.0 ms |
| `/api/storage` | 3.0 KB | 708.4 ms |
| `/api/library/309` | 2.0 KB | 38,651.9 ms |
| `/api/cleanup/executions?limit=1` | 1.6 KB | 10.3 ms |

## Most Expensive Components

Measured in local React dev build with CasaOS API proxy.

| Component | Renders | Total actual | Max actual | Avg actual |
| --- | ---: | ---: | ---: | ---: |
| `route:Library` | 8 | 305.7 ms | 127.4 ms | 38.2 ms |
| `Library.Body` | 4 | 238.5 ms | 120.7 ms | 59.6 ms |
| `Library.LibraryItemRow` | 366 | 176.3 ms | 5.1 ms | 0.5 ms |
| `route:Health` | 4 | 34.2 ms | 19.0 ms | 8.6 ms |
| `route:ItemDetail` | 5 | 33.7 ms | 14.5 ms | 6.7 ms |
| `route:Home` | 5 | 27.3 ms | 10.2 ms | 5.5 ms |
| `Home.RecentlyAddedSection` | 5 | 11.5 ms | 5.8 ms | 2.3 ms |
| `route:Settings` | 3 | 10.8 ms | 7.6 ms | 3.6 ms |

## Most Expensive Transforms

| Transform | Count | Max | Avg | Input count |
| --- | ---: | ---: | ---: | ---: |
| `Library.filterSort` | 3 | 6.5 ms | 2.3 ms | 183 |
| `ItemDetail.deriveEntries` | 4 | 6.1 ms | 1.6 ms | n/a |
| `Health.buildIntegrations` | 1 | 0.7 ms | 0.7 ms | n/a |
| `Home.deriveBanner` | 3 | 0.3 ms | 0.2 ms | n/a |
| `Library.mapArtifacts` | 3 | 0.2 ms | 0.1 ms | 183 |
| `Recover.computeTotals` | 2 | 0.1 ms | 0.1 ms | n/a |

Library payload processing breakdown for 183 items:

| Step | Time |
| --- | ---: |
| Filter | 0.1 ms |
| Sort | 6.2 ms |

## Root Cause Ranking

1. Backend/API latency still dominates perceived route readiness. Home waited 58.6 s on `/api/validation`; Item Detail waited 38.7 s on `/api/library/309` and `/api/imports/309`.
2. Library has the highest frontend render cost. The route and body are expensive because all 183 rows render, with 366 row render events in the dev component pass.
3. Large payload transfer remains meaningful but is not the primary parse bottleneck. `/api/cleanup`, `/api/cleanup/review`, `/api/library`, and `/api/imports` are the largest payloads; JSON parse stayed under 3.3 ms.
4. Query transforms are not currently the main bottleneck. The worst measured transform was `Library.filterSort` at 6.5 ms.
5. Rerender counts are moderate in production route scopes. No route-level runaway rerender loop was observed in this pass.

## Recommended Optimization Roadmap

1. Re-audit backend detail endpoints before frontend rewrites. `/api/validation`, `/api/library/:id`, and `/api/imports/:id` dominate route readiness in this measurement.
2. For Library, evaluate row virtualization or incremental rendering next, but only after a dedicated optimization sprint. This audit indicates the full row tree is the largest frontend component cost.
3. Reduce or split large route payloads where behavior allows. Prioritize `/api/cleanup`, `/api/cleanup/review`, `/api/library`, and `/api/imports`.
4. Add targeted query staleness/cache policy review. Health and Settings are fast when cache-warm, which suggests route-to-route latency may improve by avoiding unnecessary refetches.
5. Keep transform optimization low priority for now. Current transform costs are below user-perceptible thresholds compared with API waits and Library tree render cost.

## Validation

- `npm run typecheck`: passed.
- `npm run build`: passed when rerun outside the sandbox because esbuild needed permission to read the Vite config path.
