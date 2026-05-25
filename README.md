# Handoffarr

**See who passed the bad torrent.**

Handoffarr is a tiny, **read-only** Docker dashboard that traces a single media
automation handoff path and helps you answer one question:

> *Who passed the bad torrent?*

It correlates what your request manager asked for, what Radarr selected, and what
qBittorrent is actually doing — then gives each item a plain-language diagnosis.

## What it does

- Polls the official APIs of **Seerr / Jellyseerr / Overseerr**, **Radarr**, and
  **qBittorrent** on an interval.
- Correlates the **Seerr request → Radarr selected release → qBittorrent torrent
  state** passthrough.
- Renders a simple server-rendered HTML table with a diagnosis per item.
- Stores raw events and correlated traces in a local SQLite database.

## What it does NOT do

- It does **not** modify anything. No adding, deleting, pausing, resuming, or
  changing torrents. No changes to Radarr, Seerr/Jellyseerr/Overseerr, or
  qBittorrent. It is strictly read-only.
- No Sonarr yet (the code is structured so it can be added later).
- No authentication (V1 is intended for trusted local networks only).
- No React, Redis, Celery, Kafka, Prometheus, or Grafana. One small container.

## ⚠️ Safety warning — do not commit secrets or private data

This is a **public-safe** repository. Never commit:

- Real API keys, URLs, IPs, domains, usernames, or passwords
- Real `config/config.yaml` (it is git-ignored on purpose)
- Logs, screenshots, raw API responses
- SQLite databases (`data/`, `*.sqlite3`, etc.)
- Real torrent hashes or media titles / history

Only `config.example.yaml` (with placeholders) belongs in version control. The
`.gitignore` is set up to keep `config/config.yaml`, `data/`, `logs/`, `.env*`,
and database files out of git — keep it that way.

## Quick start

1. **Copy the example config to a local, git-ignored file:**

   ```bash
   mkdir -p config data
   cp config.example.yaml config/config.yaml
   ```

2. **Add your API keys locally** by editing `config/config.yaml`:

   - `services.seerr.api_key` — from Jellyseerr/Overseerr settings
   - `services.radarr.api_key` — from Radarr → Settings → General
   - `services.qbittorrent.username` / `password` — your qBittorrent Web UI login
   - Update each `base_url` to point at your services.

   Set `enabled: false` for any service you do not want to poll.

3. **Run it:**

   ```bash
   docker compose up -d
   ```

4. **Open the dashboard:**

   ```
   http://localhost:8099
   ```

   If `config/config.yaml` is missing, the dashboard starts anyway and shows a
   clear setup message instead of crashing.

## Routes

| Route             | Method | Purpose                                  |
| ----------------- | ------ | ---------------------------------------- |
| `/`               | GET    | HTML dashboard                           |
| `/health`         | GET    | Health check + whether config is present |
| `/api/traces`     | GET    | Correlated handoff traces as JSON        |
| `/api/events`     | GET    | Recent raw events (`?source=`, `?limit=`)|
| `/api/poll-now`   | POST   | Trigger an immediate poll + correlation  |

## Diagnosis labels

| Diagnosis | Meaning |
| --------- | ------- |
| **Healthy / no issue detected** | The handoff looks fine. |
| **Possible stale indexer/tracker metadata or qBittorrent connectivity issue** | The indexer reported plenty of seeds, but qBittorrent sees zero peers and the torrent is stalled. |
| **Likely bad low-availability release selected upstream** | The indexer reported few seeds and there are no actual peers — a poor release was probably chosen upstream. |
| **Possible qBittorrent/VPN/network issue** | Many active torrents show zero peers at once — points at qBittorrent, a VPN, or the network rather than any single release. |
| **Possible queue, disk, or peer choking issue** | There are peers but download speed is zero. |
| **Request not yet handed to Radarr or correlation failed** | A Seerr request has no matching Radarr grab (yet). |
| **Radarr selected a release but qBittorrent did not receive or expose it** | Radarr grabbed something, but no matching torrent is visible in qBittorrent. |

Thresholds (`low_reported_seeds`, `healthy_reported_seeds`, etc.) are
configurable in `config.yaml`.

## How correlation works

Each item is matched across services in priority order:

1. **Torrent hash** (most reliable)
2. **Download ID**
3. **Normalized title** within a configurable time window

This is intentionally simple. It is good enough to spot the obvious "who passed
the bad torrent" cases without trying to be a full provenance system.

## V1 scope

Exactly one lifecycle path:

```
Seerr / Jellyseerr / Overseerr  →  Radarr  →  qBittorrent
```

## Future scope

- Sonarr (TV)
- Prowlarr (indexer-level visibility)
- Jellyfin (playback / library confirmation)
- A proper timeline view per item
- Better release scoring and confidence on matches

## License / disclaimer

Handoffarr only reads from APIs you configure. You are responsible for keeping
your local config, data, and any exported information private.
