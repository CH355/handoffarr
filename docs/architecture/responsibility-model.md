# Responsibility Attribution Model

This is the canonical V3 model for answering the operator's next question after
Handoffarr explains what happened:

- "Who is responsible?"
- "Why is that conclusion reached?"
- "What should I fix next?"

Handoffarr is evolving from torrent observability into cross-application media
lifecycle observability. Responsibility attribution is the model that connects a
plain diagnosis to an accountable domain and an operational next step.

The model does not redesign Handoffarr:

```
Collectors -> Persistence -> Interpreters -> Dashboard
```

Collectors still gather read-only facts. Persistence still stores observations
and derived state in local SQLite. Interpreters derive judgments from already
collected data. The Dashboard renders the conclusion, confidence, evidence,
impact, and recommended action.

No microservice, Redis, Kafka, Celery, event bus, external database, or new
orchestration layer is part of this model.

## Purpose

Responsibility attribution exists because "what happened?" is not enough during
operations.

A real-world investigation showed:

- Downloads succeeded.
- Imports succeeded.
- Library files existed.
- qBittorrent retained completed torrents.
- 352 completed torrents consumed 535 GB.

The useful operational question was not only "what happened?" The useful
question was "who caused this state, and what should be fixed?"

Handoffarr should therefore answer four questions for a lifecycle issue:

| Question | Meaning |
|----------|---------|
| What happened? | The observed lifecycle diagnosis, such as Cleanup Failure or Storage Critical. |
| Who is responsible? | The domain most likely accountable for the condition. |
| Why is that conclusion reached? | The evidence and rules used to assign responsibility. |
| What should be investigated next? | The safest next action for the operator. |

Responsibility is a read-only interpretation. It is not blame, mutation, or
automation. Handoffarr should never delete torrents, rewrite application
settings, or change upstream services in response to a responsibility
assessment.

## Canonical Entity: ResponsibilityAssessment

`ResponsibilityAssessment` is the derived explanation of which domain is most
likely accountable for a lifecycle diagnosis.

It may be derived from requests, decisions, runtime state, import events,
cleanup events, storage artifacts, configuration observations, and filesystem
observations. It does not require a dedicated upstream event.

Minimum canonical fields:

| Field | Meaning |
|-------|---------|
| `assessment_id` | Stable derived id for the assessment, usually based on the correlated lifecycle entity, attribution category, and observation time bucket. |
| `lifecycle_stage` | Stage where the issue is observed, such as Request, Decision, Runtime, Import, Cleanup, or Storage. |
| `diagnosis` | The lifecycle diagnosis being attributed, such as Selection Failure, Cleanup Failure, or Storage Failure. |
| `responsible_domain` | The domain most likely accountable for the diagnosis. Must use one of the canonical responsibility domains. |
| `confidence` | Strength of the attribution: Certain, High, Medium, or Low. |
| `evidence` | Structured observations supporting the conclusion, including source system, fields, correlation keys, and rule matches. |
| `impact` | Operational effect of the issue, such as bytes retained, torrents affected, imports blocked, downloads stalled, or user-visible risk. |
| `recommended_action` | The next operator investigation or configuration review suggested by the assessment. |
| `observed_at` | Poll time when the assessment was derived. |

`ResponsibilityAssessment` is interpreter output. It may be persisted as derived
state or recomputed for presentation, but the canonical boundary remains the
same: collectors do not assign responsibility, and the dashboard does not invent
responsibility.

## Responsibility Domains

Responsibility domains are the canonical owners Handoffarr can name. A domain
does not always map one-to-one to an application. Some domains represent the
operator, the environment, or insufficient evidence.

### User

Scope:

- Operator choices and intentional policies.
- Manual configuration decisions.
- Human actions outside Handoffarr.

Examples:

- Queue limits set too low.
- Ratio limits intentionally retaining torrents.
- Root folders configured to a nearly full disk.
- A manual choice to keep long-term seeding content.

Evidence required:

- Explicit configuration evidence, policy evidence, or user-visible setting.
- Strong indication that the observed state matches configured intent.
- Absence of application error evidence contradicting that intent.

### Filesystem

Scope:

- Local paths, permissions, disk capacity, mounts, and file existence.
- Conditions outside media applications but visible through their errors or
  filesystem observations.

Examples:

- Permission denied during import.
- Missing destination path.
- Invalid or unavailable root folder.
- Disk full or critically low.
- Library file exists but download artifact also remains.

Evidence required:

- Filesystem collector evidence, application path errors, disk free-space
  observations, or explicit permission/path failure messages.
- Path-level correlation to the affected lifecycle item when item-specific.

### Network

Scope:

- Connectivity between qBittorrent and peers, trackers, DHT, VPN, or the public
  internet.

Examples:

- VPN disconnected.
- No DHT nodes.
- No tracker connectivity.
- Fleet-wide zero peers or zero throughput.

Evidence required:

- qBittorrent connection status, DHT node count, tracker status, or broad
  runtime correlation across multiple torrents.
- Evidence should distinguish network-wide failure from one bad release when
  possible.

### Indexer

Scope:

- Search results, release availability claims, seed metadata, and release
  discoverability.

Examples:

- Bad release selected from stale metadata.
- Reported seeds are high but actual peers are zero.
- Low availability torrent chosen.
- Metadata inconsistency in selected release attributes.

Evidence required:

- Decision evidence from Radarr history, selected release metadata, indexer name,
  reported seed count, and runtime observations from qBittorrent.
- Because Handoffarr does not see the full candidate set, attribution to Indexer
  is usually Medium unless explicit metadata contradiction is strong.

### Seerr

Scope:

- Request creation and user request metadata from Seerr, Jellyseerr, or
  Overseerr.

Examples:

- Duplicate or unexpected request.
- Request metadata that cannot be correlated to a downstream decision.
- User-requested title that leads to ambiguous matching.

Evidence required:

- Request observation from the Seerr collector.
- Correlation evidence showing the request is the source of the lifecycle path
  being assessed.
- Missing downstream evidence should be attributed to Seerr only when the request
  itself is malformed, ambiguous, or inconsistent.

### Radarr

Scope:

- Movie release decisions, grabs, imports, movie root folders, import policy,
  and Radarr download-client integration.

Examples:

- Bad movie release selected.
- Import failed because Radarr root folder is invalid.
- Remove imported downloads behavior did not remove completed content.
- Radarr grabbed a release but no qBittorrent artifact can be found.

Evidence required:

- Radarr history, queue, movie file, root folder, import, or configuration
  evidence.
- Correlation to qBittorrent through torrent hash, download id, or normalized
  title when the issue crosses the handoff boundary.

### Sonarr

Scope:

- Series release decisions, episode imports, series root folders, import policy,
  and Sonarr download-client integration.

Examples:

- Episode import failed due to invalid path.
- Completed episode retained after import.
- Remove imported downloads policy does not match operator expectation.

Evidence required:

- Sonarr history, queue, episode file, root folder, import, or configuration
  evidence.
- Correlation to qBittorrent through torrent hash, download id, or normalized
  title when the issue crosses the handoff boundary.

### Lidarr

Scope:

- Music release decisions, artist or album imports, root folders, import policy,
  and Lidarr download-client integration.

Examples:

- Album import failed due to path or metadata mismatch.
- Completed music download retained after import.
- Lidarr download-client settings conflict with expected cleanup.

Evidence required:

- Lidarr history, queue, track or album file, root folder, import, or
  configuration evidence.
- Correlation to qBittorrent through torrent hash, download id, or normalized
  title when the issue crosses the handoff boundary.

### qBittorrent

Scope:

- Download client runtime state, torrent lifecycle, queueing, tracker status,
  payload paths, save paths, seeding state, and retained torrents.

Examples:

- Torrent stalled.
- Torrent stopped or paused.
- Queue saturated.
- Completed torrent retained.
- qBittorrent reports missing files or save-path errors.

Evidence required:

- qBittorrent torrent state, queue report, tracker report, content path, save
  path, ratio/time, category/tag, or error state.
- For cleanup attribution, qBittorrent responsibility requires evidence that the
  client retained or could not remove the artifact independent of upstream
  application policy.

### External Dependency

Scope:

- Systems outside Handoffarr and the observed media applications that influence
  lifecycle outcomes.

Examples:

- Tracker outage.
- DNS failure.
- Remote mount unavailable.
- VPN provider outage.
- Indexer API outage when no specific indexer evidence is available.

Evidence required:

- Explicit upstream error messages, repeated failures across applications, or
  environment evidence that points outside the named applications.
- Use this domain when the failure is clearly external but cannot be fairly
  assigned to Network, Filesystem, or a named application.

### Unknown

Scope:

- Insufficient, contradictory, or missing evidence.

Examples:

- Correlation failed.
- Required collector data is absent.
- Multiple domains are plausible and no rule can choose between them.

Evidence required:

- Evidence of uncertainty itself: missing fields, low match confidence,
  conflicting timestamps, or absent upstream observations.
- The recommended action should name the missing evidence needed to raise
  confidence.

## Attribution Categories

Attribution categories are the canonical classes of responsibility assessment.
They are broader than individual dashboard strings and should be reused across
Radarr, Sonarr, Lidarr, qBittorrent, storage, and cleanup observations.

### Selection Failure

The wrong or unhealthy release was selected for download.

Examples:

- Bad release selected.
- Low availability torrent.
- Metadata inconsistency.
- Reported seed count does not match observed peer availability.

Likely responsible domains:

- Indexer.
- Radarr, Sonarr, or Lidarr.

Evidence:

- Selected release name and source application.
- Reported seed count or indexer metadata when available.
- qBittorrent runtime state, actual seeds/peers, tracker state, and stall state.

### Import Failure

The download completed or became available, but the media application did not
successfully import it into the library.

Examples:

- Permission denied.
- Missing destination path.
- Invalid root folder.
- Metadata or file layout prevents import.

Likely responsible domains:

- Filesystem.
- Radarr.
- Sonarr.
- Lidarr.

Evidence:

- Import failure event or queue error from the media application.
- Library file absent or unconfirmed.
- Download artifact present.
- Path, permission, or root folder evidence.

### Cleanup Failure

The content was imported, but the download-side artifact remains without a
confirmed retention requirement.

Examples:

- Imported content retained.
- Remove Imported Downloads disabled or not effective.
- Cleanup never executed.
- Completed torrent remains after library copy exists.

Likely responsible domains:

- Radarr.
- Sonarr.
- Lidarr.
- qBittorrent.
- Cleanup subsystem.

Evidence:

- Import success.
- Library file present.
- Download artifact or torrent payload present.
- No active retention requirement, or cleanup policy evidence contradicts the
  retained state.

Note: Cleanup subsystem is a responsibility label for Handoffarr's derived
cleanup interpretation, not a new service. It means the post-import cleanup
phase is accountable for the storage impact. When evidence names a concrete
application policy, prefer that application domain.

### Storage Failure

Storage pressure is harmful or explained by lifecycle waste.

Examples:

- Disk full.
- Reclaimable storage ignored.
- Download storage growth.
- Completed retained downloads explain a critical free-space condition.

Likely responsible domains:

- Filesystem.
- Cleanup subsystem.

Evidence:

- Disk free-space threshold crossed.
- Reclaimable storage total.
- Cleanup candidates present.
- Large retained artifacts correlated to imported media.

### Runtime Failure

The torrent runtime cannot make progress.

Examples:

- Dead swarm.
- Tracker failures.
- Choking.
- Stalled downloads.
- Metadata download deadlock.

Likely responsible domains:

- qBittorrent.
- Indexer.
- Network.

Evidence:

- qBittorrent state classification.
- Seeds, peers, speed, tracker status, DHT status, and queue state.
- Comparison between reported availability and actual runtime availability.

### Network Failure

Connectivity is preventing discovery or transfer.

Examples:

- VPN disconnected.
- No DHT nodes.
- No tracker connectivity.
- Fleet-wide zero peers or zero throughput.

Likely responsible domains:

- Network.

Evidence:

- qBittorrent connection status.
- DHT node count.
- Tracker status.
- Multiple active torrents affected in the same observation window.

### Configuration Failure

Configured policies or limits cause the observed lifecycle behavior.

Examples:

- Queue limits.
- Ratio limits.
- Import policies.
- Download client settings.
- Remove Imported Downloads policy.

Likely responsible domains:

- User.
- Application configuration for Radarr, Sonarr, Lidarr, or qBittorrent.

Evidence:

- Explicit configuration values.
- Observed behavior matching those values.
- No contradicting runtime or filesystem failure.

## Attribution Confidence

Confidence describes how strongly Handoffarr can assign responsibility. It must
be visible in the dashboard and reflected in wording.

### Certain

Required evidence:

- Explicit API evidence or explicit configuration evidence.
- Direct source-system statement naming the failing condition.
- Strong correlation to the affected lifecycle item.

Acceptable uncertainty:

- Minimal. The source system directly explains the state.

Dashboard language:

- "Responsibility confirmed."

Examples:

- Radarr reports permission denied importing to a specific path.
- qBittorrent reports a torrent is paused because the operator paused it.
- Configuration explicitly disables remove-on-import behavior.

### High

Required evidence:

- Multiple supporting observations.
- Strong correlation across lifecycle stages.
- No credible competing domain with equal evidence.

Acceptable uncertainty:

- Some upstream details may be absent, but the observed lifecycle strongly
  supports one conclusion.

Dashboard language:

- "Very likely responsible."

Examples:

- Imported file exists, library file exists, download artifact exists, torrent is
  stopped, and no retention requirement is observed.
- Disk is critically low, large reclaimable storage is present, and cleanup
  candidates explain the pressure.

### Medium

Required evidence:

- A plausible rule match with at least one important missing or inferred fact.
- Correlation is adequate but not complete.

Acceptable uncertainty:

- Another domain could be responsible if missing evidence were available.

Dashboard language:

- "Likely responsible."

Examples:

- Reported seeds were high, actual peers are zero, and the torrent stalled, but
  tracker or network evidence is incomplete.
- A selected release has poor availability, but Handoffarr cannot observe the
  rejected candidate set.

### Low

Required evidence:

- Circumstantial indicators only.
- Weak correlation, missing fields, or contradictory observations.

Acceptable uncertainty:

- Significant. The assessment should guide investigation, not state a conclusion.

Dashboard language:

- "Needs investigation."

Examples:

- A request cannot be matched to a decision.
- Download storage is growing but import and cleanup evidence is not yet
  collected.
- A stalled torrent lacks both indexer metadata and tracker details.

## Attribution Rules

Attribution rules assign a category, responsible domain, confidence, impact, and
recommended action from already collected evidence. They should be implemented as
pure interpreter logic.

Rules should preserve the evidence that made them fire. The dashboard should be
able to explain the conclusion without re-running mental correlation.

### Imported content retained after successful import

Evidence:

- Imported file exists.
- Library file exists.
- Download artifact exists.
- Torrent is stopped or completed.
- No active retention requirement is observed.

Result:

- Diagnosis: Cleanup Failure.
- Responsible domain: Cleanup subsystem, or the concrete media application if
  policy evidence identifies Radarr, Sonarr, or Lidarr.
- Confidence: High.
- Recommended action: Review remove imported downloads policy, retention policy,
  and download client cleanup behavior.

### Stalled torrent contradicts reported availability

Evidence:

- Reported seeds = 50.
- Actual peers = 0.
- Torrent is stalled.

Result:

- Diagnosis: Selection Failure.
- Responsible domain: Indexer selection.
- Confidence: Medium.
- Recommended action: Review selected release, indexer health, tracker state, and
  whether the media application should choose a different release.

### Disk pressure explained by reclaimable storage

Evidence:

- Disk critically low.
- Large reclaimable storage total.
- Cleanup candidates present.

Result:

- Diagnosis: Storage Failure.
- Responsible domain: Cleanup subsystem.
- Confidence: High.
- Recommended action: Review cleanup candidates and remove-on-import policy in
  the responsible media application.

### Explicit import path failure

Evidence:

- Media application reports import failed.
- Error names missing destination path, invalid root folder, or permission
  denied.
- Download artifact remains.
- Library file is absent or unconfirmed.

Result:

- Diagnosis: Import Failure.
- Responsible domain: Filesystem when the path or permission is the failing
  resource; otherwise Radarr, Sonarr, or Lidarr when configuration is explicit.
- Confidence: Certain when the API error is explicit, High when inferred from
  matching path observations.
- Recommended action: Fix root folder, mount, path mapping, or permissions.

### Fleet-wide peer discovery failure

Evidence:

- Multiple active torrents have zero peers or zero throughput.
- DHT node count is zero, qBittorrent reports disconnected, or trackers are not
  working.
- The issue is not limited to one selected release.

Result:

- Diagnosis: Network Failure.
- Responsible domain: Network.
- Confidence: High, or Certain when qBittorrent explicitly reports disconnected.
- Recommended action: Check VPN, network route, DNS, tracker reachability, and
  qBittorrent connection settings.

### Queue policy blocks progress

Evidence:

- Queueing is enabled.
- Active download slots are full.
- Additional torrents are queued.
- No network, tracker, or disk failure better explains the stall.

Result:

- Diagnosis: Configuration Failure.
- Responsible domain: User or qBittorrent.
- Confidence: High when slot configuration is explicit.
- Recommended action: Review active download limits and queue policy.

## Responsibility Chain

Responsibility can shift as a media item moves through the lifecycle:

```
Request -> Decision -> Runtime -> Import -> Cleanup -> Storage
```

The latest failure is not always the root cause. Handoffarr should distinguish
between root-cause attribution and symptom attribution.

Root-cause attribution identifies the earliest responsible domain that plausibly
created the downstream condition.

Symptom attribution identifies the domain responsible for the currently visible
operational impact.

Example chain:

| Stage | Observed issue | Responsible domain |
|-------|----------------|--------------------|
| Decision | Bad release selected | Indexer or media application |
| Runtime | Download stalled | Network or qBittorrent |
| Import | Import failed | Filesystem or media application |
| Cleanup | Imported content retained | Sonarr, Radarr, Lidarr, qBittorrent, or Cleanup subsystem |
| Storage | Disk full | Cleanup subsystem or Filesystem |

In this chain, "disk full" may be the symptom, while "cleanup never executed" is
the root operational cause. Conversely, a storage issue may be the root cause of
an import issue if imports fail because the destination disk is full.

Responsibility assessments should therefore allow both views:

- Root cause: the earliest high-confidence domain that explains downstream
  effects.
- Current blocker: the latest high-impact domain preventing progress now.

When confidence is weak, the assessment should say which evidence is missing
instead of pretending the chain is complete.

## Dashboard Concepts

The dashboard should present responsibility as an evidence-backed operational
answer, not as a raw rule dump.

### Responsibility Summary

Fleet-level views:

- Top Responsible Domains.
- Failure Counts by Domain.
- Storage Impact by Domain.
- Reclaimable Space by Domain.
- Confidence distribution by domain.
- Current blockers grouped by lifecycle stage.

These summaries should make it obvious whether the operator should look first at
storage, cleanup policy, network connectivity, indexer quality, filesystem
health, or a specific media application.

### Responsibility Detail View

Each issue should show:

- Diagnosis.
- Responsible Domain.
- Confidence.
- Evidence.
- Impact.
- Recommended Action.

The detail view should preserve source observations so the operator can
understand the conclusion without opening qBittorrent, Radarr, Sonarr, Lidarr,
or Seerr first.

Example detail:

| Field | Value |
|-------|-------|
| Diagnosis | Cleanup Failure |
| Responsible Domain | Sonarr |
| Confidence | High |
| Evidence | Imported content present. Library copy exists. Torrent retained. Cleanup not executed. |
| Impact | 535 GB retained across 352 completed torrents. |
| Recommended Action | Review Remove Imported Downloads policy. |

Dashboard wording should follow confidence:

| Confidence | Wording |
|------------|---------|
| Certain | Responsibility confirmed |
| High | Very likely responsible |
| Medium | Likely responsible |
| Low | Needs investigation |

## Operational Goal

The final product goal is that Handoffarr can answer:

- "Why is my disk full?"
- "Who caused it?"

without requiring the operator to open:

- qBittorrent.
- Radarr.
- Sonarr.
- Lidarr.
- Seerr.

Target output:

| Field | Value |
|-------|-------|
| Storage Health | Critical |
| Diagnosis | Cleanup Failure |
| Responsible Domain | Sonarr |
| Confidence | High |
| Evidence | Imported content present. Library copy exists. Torrent retained. Cleanup not executed. |
| Impact | 535 GB retained. 352 completed torrents. |
| Recommended Action | Review Remove Imported Downloads policy. |

The Dashboard should still expose enough evidence for verification. The point is
not to hide qBittorrent, Radarr, Sonarr, Lidarr, or Seerr. The point is to make
the first answer operationally complete:

```
What happened?
Cleanup failed after successful import.

Who is responsible?
Sonarr is very likely responsible for the retained imported downloads.

Why?
The library copy exists, the torrent payload still exists, qBittorrent retained
the completed torrents, and no active retention requirement was observed.

What should I fix?
Review Remove Imported Downloads and related cleanup policy.
```

Responsibility attribution is therefore the canonical bridge from media
lifecycle observability to operator action.

## Layer Placement

Responsibility attribution belongs in the interpreter layer.

Collectors:

- Gather read-only observations from Seerr, Radarr, Sonarr, Lidarr,
  qBittorrent, filesystem, and external APIs when supported.
- Do not assign responsibility.

Persistence:

- Stores raw observations and any derived assessment state in local SQLite.
- Does not fetch and does not interpret.

Interpreters:

- Correlate lifecycle facts.
- Apply attribution rules.
- Produce `ResponsibilityAssessment` records or equivalent derived objects.
- Preserve evidence, impact, confidence, and recommended action.

Dashboard:

- Renders summaries and details.
- Uses confidence-aware language.
- Does not compute responsibility independently.

The architecture remains:

```
Collectors -> Persistence -> Interpreters -> Dashboard
```

