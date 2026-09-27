# Launch checklist — Gate 1 kill test

Thesis: API drift detection ("Dependabot for third-party API changes"),
$125/mo × 24 teams = $3,000 MRR. Full context:
`~/workspace/business-research/devtools-aiinfra-hunt-2026-09-27.md`

**Binding gate:** 25 installs in 14 days from one HN Show post + r/webdev,
else KILL. Nothing has been published or posted yet.

## Steps (in order)

- [ ] **1. Create the repo.** Public GitHub repo named `api-drift-watch`.
      Push the contents of `~/workspace/api-drift-probe/`.
- [ ] **2. Pro waitlist form.** Create a 2-field form (Tally or Google Form:
      email + "which vendors do you depend on?"). Paste its URL into
      `README.md` where marked `CHRIS:`, replacing the `#` placeholder.
- [ ] **3. Twilio credentials for dogfooding.** Free Twilio account (trial
      credits are fine — all canary calls are read-only GETs). Add
      `TWILIO_ACCOUNT_SID` + `TWILIO_AUTH_TOKEN` as repo secrets.
      (Optional: `SENDGRID_API_KEY` — restricted key, Read scopes only.)
- [ ] **4. Dry-run.** Actions tab → run "API drift watch" with
      `dry-run: true`. Confirm both endpoints return 200 and shapes print.
      If a 401: fix secrets. If a 403: see README "Endpoint notes".
- [ ] **5. Initialize baseline.** Run with `update-baseline: true`.
      The workflow commits `.apidrift/baselines/*.json` — review the diff.
- [ ] **6. Cut release `v1`.** GitHub → Releases → tag `v1` (and `v1.0.0`).
      Marketplace listings require a release.
- [ ] **7. Publish to GitHub Marketplace.** Repo → the "publish to
      Marketplace" flow (or https://github.com/marketplace/new — follow
      GitHub's current flow). Category: Monitoring (or Utilities).
      Verify the listing renders with the README.
- [ ] **8. Approve the launch posts.** Read `LAUNCH-DRAFTS.md` — the Show HN
      post/comment and the r/webdev post. Edit or approve as-is.
- [ ] **9. Post Show HN.** Weekday morning US Eastern. Title:
      `Show HN: API Drift Watch – free GitHub Action that catches silent
      third-party API changes`. Paste the prepared first comment immediately.
      Reply to substantive comments for the first 6 hours.
- [ ] **10. Post r/webdev.** Check current self-promo rules first; don't use a
      brand-new account. Same day or next day is fine.
- [ ] **11. Start the 14-day clock.** Day 0 = Show HN post date.
      Track: Marketplace "used by" + repo Insights → Traffic (14-day window)
      + stars + third-party drift issues.
- [ ] **12. Day-14 decision.**
      - ≥25 installs → **Gate 1 PASSES.** Proceed to Gate 2: the Pro waitlist
        CTA in the README needs ≥10 emails + ≥3 refundable $99 deposits in
        30 days, else KILL.
      - <25 installs → **KILL.** Archive the repo. The lane is exhausted.

## Kill conditions (recap, all binding)

- <25 installs in 14 days → KILL
- Gate 2: <10 waitlist emails or <3 refundable $99 deposits in 30 days → KILL
- Demand collapses to the SDK-bump use case ("just watch my Stripe SDK
  version") → KILL (Dependabot owns that territory)

## Files in this package

| File | What it is |
|---|---|
| `action.yml` | The Marketplace action definition (composite, stdlib-only) |
| `scripts/drift_probe.py` | The probe: fetch → shape → diff → issue |
| `.github/workflows/drift-watch-example.yml` | Copy-paste consumer workflow (also dogfoods here) |
| `README.md` | 5-min setup, inputs, false-positive summary, Pro CTA |
| `SAMPLE-ISSUE.md` | What a drift issue looks like |
| `docs/false-positive-controls.md` | Full false-positive design + residual risks |
| `LAUNCH-DRAFTS.md` | Show HN + r/webdev posts (unposted), tracking plan |
| `LAUNCH-CHECKLIST.md` | This file |
| `LICENSE` | MIT |
