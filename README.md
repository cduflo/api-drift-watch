# API Drift Watch

**Free GitHub Action: catch silent third-party API changes before they break your integration.**

Uptime monitors return 200 OK while Twilio renames a field or SendGrid nests something one level deeper — and you find out from a customer, not your monitoring. This action makes scheduled read-only canary calls against your vendors, snapshots each response's **shape** (field names + types — values are never compared), diffs against a baseline committed in your repo, and opens a single rolling GitHub issue when something drifts.

No dependencies. No SDK. Stdlib Python + the `gh` CLI already on the runner.

---

## 5-minute setup

**1. Get credentials.**

- **Twilio:** your Account SID + Auth Token from the Twilio console. Every canary call is a read-only GET — free, even on trial accounts.
- **SendGrid:** create a restricted API key with **only** `API Keys: Read` + `Suppressions: Read` scopes (Settings → API Keys → Create API Key → Restricted Access).

**2. Add them as repository secrets:** `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `SENDGRID_API_KEY`.

**3. Add the workflow** (`.github/workflows/api-drift.yml`) — copy [`drift-watch-example.yml`](.github/workflows/drift-watch-example.yml):

```yaml
name: API drift watch
on:
  schedule:
    - cron: "17 9 * * *"
  workflow_dispatch:
    inputs:
      update-baseline: { type: boolean, default: false }
jobs:
  drift-watch:
    runs-on: ubuntu-latest
    permissions:
      issues: write
      contents: write
    steps:
      - uses: actions/checkout@v4
      - uses: <owner>/api-drift-watch@v1   # <-- replace <owner> after publishing
        with:
          vendor: twilio
          twilio-account-sid: ${{ secrets.TWILIO_ACCOUNT_SID }}
          twilio-auth-token: ${{ secrets.TWILIO_AUTH_TOKEN }}
```

**4. Dry-run first** (Actions tab → run workflow → `dry-run: true`). Verifies credentials and endpoints; writes nothing, opens nothing.

**5. Initialize the baseline:** run once with `update-baseline: true`. The workflow commits `.apidrift/baselines/*.json` back to your repo. Review it — it's the contract you're now monitoring.

**6. Done.** Daily runs open/update one issue per vendor when a schema drifts. See [SAMPLE-ISSUE.md](SAMPLE-ISSUE.md) for what it looks like.

---

## Inputs

| Input | Default | What it does |
|---|---|---|
| `vendor` | `twilio` | `twilio` \| `sendgrid` \| `custom` |
| `twilio-account-sid` / `twilio-auth-token` | — | Pass `${{ secrets.… }}` |
| `sendgrid-api-key` | — | Restricted read-only key, pass `${{ secrets.… }}` |
| `endpoints-json` | — | `custom` only: JSON array of `{"name","method","url","headers"}` |
| `baselines-dir` | `.apidrift/baselines` | Where baselines live in the repo |
| `update-baseline` | `false` | Re-snapshot instead of diffing (intentional vendor changes) |
| `dry-run` | `false` | Print shapes; change nothing |
| `create-issue` | `true` | Open/update the drift issue |
| `fail-on-drift` | `false` | Fail the workflow on drift (**off by default — drift never breaks CI**) |
| `telemetry-endpoint` | — | Opt-in anonymous ping; empty = disabled (see below) |
| `github-token` | `${{ github.token }}` | Needs `issues: write` |

## How it works

1. **Probe** — read-only canary calls (Twilio: account fetch + available-number search; SendGrid: API keys + bounces list; or your own `endpoints-json`).
2. **Shape** — each JSON response is reduced to a type tree: field names + types. Values are discarded, so timestamps, SIDs and phone numbers can never false-positive.
3. **Diff** — compared against the committed baseline. Added/removed fields and type changes are drift.
4. **Report** — one rolling issue per vendor, updated in place. Re-detections with an unchanged shape only refresh the timestamp (no comment spam). If the vendor reverts, the issue auto-closes.

## False-positive controls

This is the part that matters — a drift alerter that cries wolf gets disabled. Full writeup: [docs/false-positive-controls.md](docs/false-positive-controls.md). The short version:

- **Values are never compared** — only field names and types.
- **Only 2xx responses are compared.** 429s, 5xx, timeouts and non-JSON are skipped with a log line, never alerts. A 401 fails loudly with credential help.
- **Pagination is pinned** (`PageSize=1`) so list endpoints return stable shapes.
- **One deduped issue per vendor**, updated in place.
- **Baselines are explicit and committed** — first run initializes, intentional changes re-baseline via `update-baseline: true`, and baseline changes are reviewable in git history.

## Custom vendors

```yaml
- uses: <owner>/api-drift-watch@v1
  with:
    vendor: custom
    endpoints-json: |
      [{"name": "status", "method": "GET",
        "url": "https://status.example.com/api/v2/summary.json",
        "headers": {"Authorization": "Bearer ${{ secrets.EXAMPLE_TOKEN }}"} }]
```

Tip: pin versioned paths (`/v1/…`) in your URLs — a vendor's major-version cutover is signal, not noise, and you want it reported as such.

## Telemetry

Off by default. If you set `telemetry-endpoint` to an HTTPS URL, each run POSTs `{probe, version, vendor, drift}` — no repository name, no user data, no response bodies. It exists so we can count real-world usage; leaving it empty disables it entirely.

---

## Want the fix, not just the alert?

This free probe opens an issue when an API drifts. **API Drift Watch Pro** ($99/mo) opens a **verified fix PR** in your repo instead — deterministic codemod + gated fixer, multi-vendor monitoring, and a mock-blind coverage report showing which of your API call sites have no canary.

<!-- CHRIS: create a 2-field waitlist form (Tally/Google Form) and paste the URL below -->
👉 **[Join the Pro waitlist](#)** — email only, no spam.

---

## Endpoint notes (verified 2026-09-27)

- **Twilio test credentials** only work on four resources (buying numbers, sending SMS, making calls, Lookup v2) — every other resource returns `403` with test creds. The default canary endpoints are read-only GETs, so use your **live or trial credentials** (reads are free).
- **SendGrid** has no test credentials; a restricted read-only API key is the correct setup.

## License

MIT — see [LICENSE](LICENSE).
