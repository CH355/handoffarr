# Debug Fixtures

This directory stores portable snapshots of Handoffarr's persisted lifecycle
state. Fixtures are produced by `GET /api/debug/export` and committed here
when they document a production case worth replaying.

## Capturing a fixture

```
curl http://localhost:8000/api/debug/export > debug-fixtures/$(date -u +%Y%m%dT%H%M%SZ).json
```

The export bundles, for the current poll cycle:

- `imports.json`-equivalent payload under `imports`
- `library.json`-equivalent payload under `library`
- `cleanup.json`-equivalent payload under `cleanup`
- `responsibility.json` under `responsibility`
- `recommendations.json` under `recommendations`
- `timeline.json` under `timeline`
- `decisions.json` under `decisions`
- `storage.json` under `storage`
- The `/api/validation` result that was true at export time

## Replay

Snapshots can be diffed against future exports to confirm an interpreter
change does not regress production behaviour. They can also be attached to a
case study (see `docs/validation/`) so the evidence behind a finding is
reproducible without live API access.

## Hygiene

- Strip API keys before committing — exports do not contain configuration
  but double-check before sharing.
- Name files with a UTC timestamp prefix and a short slug describing the
  scenario (e.g. `20260530T143000Z-library-missing.json`).
