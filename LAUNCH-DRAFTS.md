# Launch drafts — DO NOT POST. For Chris's approval.

Gate 1 of the kill test: 25 installs in 14 days from one HN Show post +
r/webdev. Nothing below has been posted anywhere.

---

## 1. HN "Show HN" post

**Title:** `Show HN: API Drift Watch – free GitHub Action that catches silent third-party API changes`

**First comment** (post this yourself immediately after submitting — Show HN
convention):

> I built a free GitHub Action that watches your third-party API dependencies
> for silent response-schema changes.
>
> The problem: uptime monitors return 200 OK while your integration quietly
> breaks. Twilio renames a field, SendGrid nests something one level deeper,
> and you find out from a customer, not your monitoring. YC's Fall 2026
> request-for-startups ("Self-Maintaining APIs") cites over 30% of service
> downtime coming from unnoticed external API changes.
>
> What it does: on a schedule, it makes read-only canary calls against
> Twilio/SendGrid (or any API you configure), snapshots each response's
> *shape* — field names + types, values are never compared — diffs against a
> baseline committed in your repo, and opens a single rolling GitHub issue when
> something drifts.
>
> The part I obsessed over is false positives, because a drift alerter that
> cries wolf gets disabled in a week: type-tree diffing ignores all values
> (timestamps/IDs can't trigger); only 2xx responses are compared
> (429s/5xx/timeouts never alert); one deduped issue per vendor updated in
> place; drift never fails your build unless you opt in; and if the vendor
> reverts, the issue auto-closes.
>
> Free, MIT, no dependencies (stdlib Python + the gh CLI on the runner).
>
> If people want it, what's next: verified fix PRs instead of issues
> (deterministic codemod + gated fixer), multi-vendor, and a "mock-blind"
> coverage report showing which of your API call sites have no canary.
>
> Try it: [REPO LINK]. Which vendor should I add next?

**Posting notes:** submit on a weekday morning US Eastern; the repo, release
v1, and Marketplace listing must be live *before* submitting (Show HN
commenters click through immediately). Reply to every substantive comment in
the first 6 hours.

---

## 2. r/webdev post

**Check the subreddit's current self-promotion rules before posting.** r/webdev
polices drive-by promotion; if in doubt, ask the mods first or frame it as a
text post with the repo link at the end rather than a link post. Do not post
from a brand-new account.

**Title:** `I made a free GitHub Action that catches silent Twilio/SendGrid API changes before they break your integration`

**Body:**

> The 2am version of this story: everything is green, uptime is 100%, and a
> customer is telling you the SMS flow broke three days ago because a vendor
> renamed a response field.
>
> I built a free GitHub Action for exactly this. On a schedule it makes
> read-only canary calls against Twilio/SendGrid (or any API), snapshots the
> response *shape* (field names + types — values are never compared, so no
> false positives from timestamps/IDs), diffs against a baseline in your repo,
> and opens one rolling GitHub issue when something drifts. If the vendor
> reverts, the issue auto-closes.
>
> Design details for the skeptics: only 2xx responses are compared (429/5xx
> never alert), one deduped issue per vendor, drift never fails CI unless you
> opt in, baselines are committed so they're reviewable in git history. Full
> false-positive writeup in the repo.
>
> Free, MIT, zero dependencies. If there's interest I'll build the paid
> version: verified fix PRs instead of issues.
>
> Repo: [REPO LINK]
>
> Honest question: which vendor's silent changes have bitten you hardest?

---

## 3. Install-count tracking plan (Gate 1: 25 installs / 14 days)

No dark patterns. Three honest signals, in priority order:

1. **GitHub Marketplace listing** (required step in the checklist). The listing
   shows a public "used by" count, and as repo admin Chris gets
   Insights → Traffic: unique cloners + views on a 14-day window — which maps
   exactly onto the Gate 1 window. This is the primary metric.
2. **Stars + drift issues in the wild.** A repo starring the action and
   configuring it is an install; a `api-drift` issue opened by someone else's
   scheduled run is the strongest possible signal (real usage, real value).
3. **Opt-in telemetry (supplementary only).** The action supports a
   `telemetry-endpoint` input — when set, each run POSTs
   `{probe, version, vendor, drift}` with no repo/user identifiers. It is **off
   by default** and disclosed in the README. For Gate 1 we do **not** rely on
   it; it exists as a secondary signal if Chris wires it to a counter.

**Honest caveats:** "used by" undercounts private-repo usage; traffic insights
require admin access (Chris has it). If the count is ambiguous at day 14,
stars + issues opened break the tie. Below 25 by any honest count → KILL.

**What we will NOT do:** no phone-home by default, no fingerprinting, no
tracking pixels, no nag screens in issues. The trust posture *is* the product
posture here — devs can read the source.
