# False-positive controls

A drift alerter that cries wolf gets disabled in a week. Every design choice
below exists to keep the signal clean. Residual risks are listed honestly at
the end.

## 1. Values are never compared

Each response is reduced to a **type tree** — field names + types only.
Timestamps, SIDs, phone numbers, dates, counters and IDs are discarded before
comparison, so volatile data can never trigger an alert. A field changing from
`"2026-09-27"` to `"2026-09-28"` is invisible; a field changing from `str` to
`int` is drift.

## 2. Only 2xx responses are compared

- **401** → the run fails loudly with credential help text (a config error must
  never silently become a "drift").
- **429 / 5xx / timeouts / DNS failures / non-JSON bodies** → the endpoint is
  skipped with a log line. Transient vendor instability is not schema drift.

## 3. Pagination is pinned

List endpoints are probed with `PageSize=1` (Twilio) / `limit=1` (SendGrid), so
page metadata (`page`, `page_size`, `next_page_uri`) is stable run to run.

## 4. One rolling issue per vendor, updated in place

- The first detection opens `API drift detected: <vendor>` (label `api-drift`).
- Re-detections **edit the issue in place**. A comment is added only when the
  drifted shape actually changed since the last report — unchanged re-detections
  just refresh the timestamp. No daily comment spam.
- If the vendor reverts and shapes match the baseline again, the issue is
  **auto-closed** with a "drift cleared" comment. The probe self-heals.

## 5. Baselines are explicit, committed, and reviewable

- The first run **initializes** the baseline (no alert on first run).
- Intentional vendor changes are handled by re-running with
  `update-baseline: true` — a deliberate human action, not silent adaptation.
- Baselines live in `.apidrift/baselines/*.json` in the repo, so every baseline
  change is visible in git history and reviewable in PRs.

## 6. Drift never breaks CI by default

`fail-on-drift` defaults to `false`. Drift is an informational signal delivered
as an issue, not a red build. Teams opt into failing builds explicitly.

## 7. Array elements are merged, not sampled

Object keys are merged across all elements of an array before comparison, so a
single odd element in a list still registers as drift instead of being averaged
away by sampling the first element.

## 8. New endpoints baseline silently

If you add an endpoint to the config, its first observation is baselined
without an alert — you can't "drift" from a baseline that never existed.

---

## Residual risks (honest)

1. **Vendor A/B tests two response shapes.** The probe will flap between
   "drift detected" and "drift cleared". The rolling issue makes the flapping
   visible rather than paging you; confirm over 2–3 runs before acting.
2. **Test-credential canned responses differ from live.** Twilio's test
   credentials return canned shapes that may not match live responses. Baseline
   with the same credential type you intend to monitor with.
3. **Major version cutovers** (`/v1/` → `/v2/`) report as massive drift. That's
   intentional — it's the highest-value signal this tool produces — but pin
   versioned paths in `endpoints-json` so the report is legible.
4. **Semantic drift without shape change** (a field keeps its type but changes
   meaning, e.g. `status` values renamed) is invisible to shape diffing. This
   is a schema monitor, not a semantic monitor.
5. **The probe trusts the vendor's 200.** A vendor returning `200` with an
   error payload shaped like an error object will diff as drift once, then
   become the new normal only after a human re-baselines.
