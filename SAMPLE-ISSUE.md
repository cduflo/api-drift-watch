# Sample drift issue

What the probe opens (and updates in place) when a vendor's response schema drifts.
Issue title: `API drift detected: twilio` · label: `api-drift`

---

## API schema drift detected — `twilio`

Checked at 2026-09-27 09:17 UTC (baseline from 2026-09-20 09:17 UTC).

> Only response **shapes** (field names + types) are compared — values like timestamps, IDs and phone numbers can never trigger this alert.

### What changed

| Endpoint | Fields added | Fields removed |
|---|---|---|
| `available-numbers` | 2 | 2 |
| `account` | 0 | 0 |

### Diffs

<details>
<summary><code>available-numbers</code> — GET https://api.twilio.com/2010-04-01/Accounts/ACxxxx/AvailablePhoneNumbers/US/Local.json?PageSize=1</summary>

```diff
--- baseline (2026-09-20 09:17 UTC)
+++ current (2026-09-27 09:17 UTC)
 $.available_phone_numbers[].address_requirements: array<str>
 $.available_phone_numbers[].beta: array<bool>
+$.available_phone_numbers[].beta_voice_intelligence: array<bool>
 $.available_phone_numbers[].capabilities[].MMS: array<bool>
 $.available_phone_numbers[].capabilities[].SMS: array<bool>
 $.available_phone_numbers[].capabilities[].fax: array<bool>
+$.available_phone_numbers[].capabilities[].ip: array<bool>
 $.available_phone_numbers[].capabilities[].voice: array<bool>
 $.available_phone_numbers[].friendly_name: array<str>
 $.available_phone_numbers[].iso_country: array<str>
 $.available_phone_numbers[].lata: array<str>
-$.available_phone_numbers[].latitude: array<str>
 $.available_phone_numbers[].locality: array<str>
-$.available_phone_numbers[].longitude: array<str>
 $.available_phone_numbers[].phone_number: array<str>
 $.available_phone_numbers[].postal_code: array<str>
 $.available_phone_numbers[].rate_center: array<str>
```

</details>

### Is this a false positive?

- If the vendor intentionally changed their API, re-snapshot the baseline: re-run the workflow with `update-baseline: true` and commit the result.
- If the diff looks wrong (e.g. the vendor A/B tests two response shapes), the next scheduled run will confirm or clear it — this issue updates in place.
- 429 / 5xx / timeouts / non-JSON never open issues; only successful (2xx) responses are compared.

_Reported by the API Drift Watch free probe._
<!-- drift-state:9f2c41ab7e00 last-seen:2026-09-27 09:17 UTC -->
