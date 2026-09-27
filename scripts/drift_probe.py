#!/usr/bin/env python3
"""
API Drift Watch probe.

Scheduled canary: fetch a small set of vendor API endpoints, extract each
response's *shape* (field names + types only -- values are never compared),
diff against the committed baseline, and open/update a single rolling GitHub
issue per vendor when the schema drifts.

Stdlib only. GitHub interaction via the `gh` CLI (preinstalled on
GitHub-hosted runners).

False-positive design (see docs/false-positive-controls.md):
  - type-tree diffing: timestamps, IDs, phone numbers can never trigger
  - only 2xx responses are compared; 429/5xx/timeouts are skipped, never alerts
  - 401 fails loudly with credential help text
  - one deduped rolling issue per vendor; unchanged re-detections don't comment-spam
  - drift never fails CI unless fail-on-drift is explicitly enabled
"""

import base64
import difflib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone

VERSION = "0.1.0"
ISSUE_LABEL = "api-drift"


def log(msg):
    print(f"[drift-probe] {msg}", flush=True)


def die(msg):
    log(f"ERROR: {msg}")
    sys.exit(1)


def env(name, default=""):
    return os.environ.get(name, default)


def flag(name):
    return env(name, "false").strip().lower() in ("1", "true", "yes")


# ---------------------------------------------------------------------------
# Shape extraction: field names + types only. Values are never compared, so
# volatile data (timestamps, SIDs, phone numbers, dates) cannot false-positive.
# ---------------------------------------------------------------------------

def shape_of(node):
    if node is None:
        return "null"
    if isinstance(node, bool):  # check before int: bool subclasses int
        return "bool"
    if isinstance(node, int):
        return "int"
    if isinstance(node, float):
        return "float"
    if isinstance(node, str):
        return "str"
    if isinstance(node, list):
        if not node:
            return "[]"
        parts = sorted({shape_of(e) for e in node})
        return "[" + "|".join(parts) + "]"
    if isinstance(node, dict):
        parts = sorted(f"{k}:{shape_of(v)}" for k, v in node.items())
        return "{" + ",".join(parts) + "}"
    return "?"


def flatten(node, path="$", out=None):
    """Human-readable dotted-path -> type lines.

    Object keys are merged across array elements, so a single odd element in
    a list still registers as drift instead of being silently averaged away.
    """
    out = [] if out is None else out
    if isinstance(node, dict):
        if not node:
            out.append(f"{path}: object(empty)")
        else:
            for key in sorted(node):
                flatten(node[key], f"{path}.{key}", out)
    elif isinstance(node, list):
        if not node:
            out.append(f"{path}: array(empty)")
        else:
            merged = {}
            scalars = set()
            for element in node:
                if isinstance(element, dict):
                    for k, v in element.items():
                        merged.setdefault(k, []).append(v)
                else:
                    scalars.add(shape_of(element))
            if scalars:
                out.append(f"{path}: array<{','.join(sorted(scalars))}>")
            for key in sorted(merged):
                flatten(merged[key], f"{path}[].{key}", out)
    elif isinstance(node, bool):
        out.append(f"{path}: bool")
    elif isinstance(node, int):
        out.append(f"{path}: int")
    elif isinstance(node, float):
        out.append(f"{path}: float")
    elif isinstance(node, str):
        out.append(f"{path}: str")
    elif node is None:
        out.append(f"{path}: null")
    else:
        out.append(f"{path}: ?")
    return out


# ---------------------------------------------------------------------------
# HTTP
# ---------------------------------------------------------------------------

def fetch(name, method, url, headers, timeout=25):
    req = urllib.request.Request(url, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace"), None
    except urllib.error.HTTPError as e:
        try:
            detail = e.read().decode("utf-8", "replace")[:300]
        except Exception:
            detail = ""
        return e.code, "", f"HTTP {e.code}: {detail}"
    except Exception as e:  # timeout, DNS, TLS, ...
        return -1, "", f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------------------
# Vendor endpoint presets
# ---------------------------------------------------------------------------

def twilio_endpoints():
    sid = env("ADW_TWILIO_SID")
    token = env("ADW_TWILIO_TOKEN")
    if not sid or not token:
        die("Twilio vendor selected but twilio-account-sid / twilio-auth-token are empty. "
            "Add TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN as repository secrets. "
            "All canary calls are read-only GETs (free, even on trial accounts).")
    basic = base64.b64encode(f"{sid}:{token}".encode()).decode()
    headers = {"Authorization": f"Basic {basic}"}
    base = "https://api.twilio.com/2010-04-01"
    return [
        {"name": "account",
         "method": "GET",
         "url": f"{base}/Accounts/{sid}.json",
         "headers": headers},
        {"name": "available-numbers",
         "method": "GET",
         "url": f"{base}/Accounts/{sid}/AvailablePhoneNumbers/US/Local.json?PageSize=1",
         "headers": headers},
    ]


def sendgrid_endpoints():
    key = env("ADW_SENDGRID_KEY")
    if not key:
        die("SendGrid vendor selected but sendgrid-api-key is empty. "
            "Create a restricted API key with only 'API Keys: Read' and "
            "'Suppressions: Read' scopes, and store it as the SENDGRID_API_KEY secret.")
    headers = {"Authorization": f"Bearer {key}"}
    return [
        {"name": "api-keys",
         "method": "GET",
         "url": "https://api.sendgrid.com/v3/api_keys?limit=1",
         "headers": headers},
        {"name": "bounces",
         "method": "GET",
         "url": "https://api.sendgrid.com/v3/suppression/bounces?limit=1",
         "headers": headers},
    ]


def load_endpoints(vendor):
    if vendor == "twilio":
        return twilio_endpoints()
    if vendor == "sendgrid":
        return sendgrid_endpoints()
    if vendor == "custom":
        raw = env("ADW_ENDPOINTS_JSON")
        if not raw:
            die("vendor=custom requires endpoints-json: a JSON array of "
                "{name, method, url, headers}.")
        try:
            eps = json.loads(raw)
        except json.JSONDecodeError as e:
            die(f"endpoints-json is not valid JSON: {e}")
        if not isinstance(eps, list) or not eps:
            die("endpoints-json must be a non-empty JSON array.")
        for ep in eps:
            if not isinstance(ep, dict) or "name" not in ep or "url" not in ep:
                die("each custom endpoint needs at least 'name' and 'url'.")
            ep.setdefault("method", "GET")
            ep.setdefault("headers", {})
        return eps
    die(f"unknown vendor '{vendor}' (expected twilio | sendgrid | custom).")


# ---------------------------------------------------------------------------
# GitHub issue reporting via gh CLI
# ---------------------------------------------------------------------------

def gh(*args):
    p = subprocess.run(["gh", *args], capture_output=True, text=True)
    return p.returncode, p.stdout.strip(), p.stderr.strip()


def ensure_label():
    # Fails harmlessly if the label already exists.
    gh("label", "create", ISSUE_LABEL,
       "--description", "Third-party API schema drift (API Drift Watch)",
       "--color", "d73a4a")


def find_open_issue(title):
    rc, out, _ = gh("issue", "list", "--label", ISSUE_LABEL, "--state", "open",
                    "--json", "number,title", "--jq",
                    f'.[] | select(.title == "{title}") | .number')
    if rc != 0 or not out:
        return None
    return out.splitlines()[0].strip()


def write_body_file(body):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False)
    tmp.write(body)
    tmp.close()
    return tmp.name


def build_issue_body(vendor, drifts, checked_at, baseline_at, drift_id):
    lines = [
        f"## API schema drift detected — `{vendor}`",
        "",
        f"Checked at {checked_at} (baseline from {baseline_at}).",
        "",
        "> Only response **shapes** (field names + types) are compared — values like "
        "timestamps, IDs and phone numbers can never trigger this alert.",
        "",
        "### What changed",
        "",
        "| Endpoint | Fields added | Fields removed |",
        "|---|---|---|",
    ]
    for d in drifts:
        lines.append(f"| `{d['name']}` | {d['added']} | {d['removed']} |")
    lines += ["", "### Diffs", ""]
    for d in drifts:
        lines += [
            "<details>",
            f"<summary><code>{d['name']}</code> — {d['method']} {d['url']}</summary>",
            "",
            "```diff",
            *d["diff"],
            "```",
            "",
            "</details>",
            "",
        ]
    lines += [
        "### Is this a false positive?",
        "",
        "- If the vendor intentionally changed their API, re-snapshot the baseline: "
        "re-run the workflow with `update-baseline: true` and commit the result.",
        "- If the diff looks wrong (e.g. the vendor A/B tests two response shapes), "
        "the next scheduled run will confirm or clear it — this issue updates in place.",
        "- 429 / 5xx / timeouts / non-JSON never open issues; only successful (2xx) "
        "responses are compared.",
        "",
        "_Reported by the API Drift Watch free probe._",
        f"<!-- drift-state:{drift_id} last-seen:{checked_at} -->",
    ]
    return "\n".join(lines) + "\n"


def report_drift(vendor, drifts, checked_at, baseline_at):
    title = f"API drift detected: {vendor}"
    drift_id = hashlib.sha1(
        json.dumps(drifts, sort_keys=True, default=str).encode()
    ).hexdigest()[:12]
    body = build_issue_body(vendor, drifts, checked_at, baseline_at, drift_id)
    body_file = write_body_file(body)
    ensure_label()
    num = find_open_issue(title)
    try:
        if num:
            rc, old_body, _ = gh("issue", "view", num, "--json", "body", "--jq", ".body")
            m = re.search(r"drift-state:([0-9a-f]+)", old_body or "")
            gh("issue", "edit", num, "--body-file", body_file)
            if m and m.group(1) == drift_id:
                log(f"drift unchanged since last run; refreshed issue #{num} (no new comment).")
            else:
                summary = "\n".join(
                    f"- `{d['name']}`: +{d['added']} / -{d['removed']} fields" for d in drifts
                )
                gh("issue", "comment", num, "--body",
                   f"Drift re-detected at {checked_at} with a **new** shape:\n{summary}\n\n"
                   f"Full diff is in the issue body above.")
                log(f"drift shape changed; updated issue #{num} and commented.")
        else:
            rc, out, err = gh("issue", "create", "--title", title,
                             "--label", ISSUE_LABEL, "--body-file", body_file)
            if rc != 0:
                die(f"could not create drift issue: {err}")
            log(f"opened drift issue {out}.")
    finally:
        os.unlink(body_file)


def clear_drift(vendor, checked_at):
    """Close the rolling issue when shapes match the baseline again."""
    title = f"API drift detected: {vendor}"
    num = find_open_issue(title)
    if not num:
        return
    gh("issue", "comment", num, "--body",
       f"Drift cleared at {checked_at}: response shapes match the baseline again. Closing.")
    gh("issue", "close", num)
    log(f"drift cleared; closed issue #{num}.")


# ---------------------------------------------------------------------------
# Telemetry (strictly opt-in: only fires when telemetry-endpoint is set)
# ---------------------------------------------------------------------------

def send_telemetry(endpoint, vendor, drift):
    if not endpoint:
        return
    payload = json.dumps({
        "probe": "api-drift-watch",
        "version": VERSION,
        "vendor": vendor,
        "drift": drift,
    }).encode()
    req = urllib.request.Request(endpoint, data=payload, method="POST",
                                 headers={"Content-Type": "application/json",
                                          "User-Agent": f"api-drift-watch/{VERSION}"})
    try:
        with urllib.request.urlopen(req, timeout=10):
            log("telemetry ping sent (opt-in).")
    except Exception as e:
        log(f"telemetry ping failed (non-fatal): {e}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    vendor = env("ADW_VENDOR", "twilio").strip().lower()
    baselines_dir = env("ADW_BASELINES_DIR", ".apidrift/baselines")
    update_baseline = flag("ADW_UPDATE_BASELINE")
    dry_run = flag("ADW_DRY_RUN")
    create_issue = flag("ADW_CREATE_ISSUE")
    fail_on_drift = flag("ADW_FAIL_ON_DRIFT")
    telemetry_endpoint = env("ADW_TELEMETRY_ENDPOINT").strip()

    endpoints = load_endpoints(vendor)
    baseline_path = os.path.join(baselines_dir, f"{vendor}.json")
    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    results = {}
    auth_failed = False
    for ep in endpoints:
        name = ep["name"]
        method = ep.get("method", "GET")
        log(f"probing {name}: {method} {ep['url']}")
        status, body, err = fetch(name, method, ep["url"], ep.get("headers", {}))
        if status == 401:
            log("  -> 401 Unauthorized: check credentials / API key scopes.")
            auth_failed = True
            results[name] = {"skipped": True, "reason": "401 unauthorized"}
            continue
        if status != 200:
            log(f"  -> skipped ({err or status}): non-2xx responses are never treated as drift.")
            results[name] = {"skipped": True, "reason": err or f"HTTP {status}"}
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            log("  -> skipped: response is not JSON.")
            results[name] = {"skipped": True, "reason": "non-JSON response"}
            continue
        lines = flatten(data)
        results[name] = {"status": status, "shape": shape_of(data), "lines": lines}
        log(f"  -> 200 OK, {len(lines)} shape lines")

    if auth_failed:
        die("authentication failed (401). Fix credentials, then re-run. "
            "Nothing was baselined and no issues were opened.")

    if dry_run:
        for name, r in results.items():
            print(f"\n=== {name} ===")
            if r.get("skipped"):
                print(f"SKIPPED: {r['reason']}")
            else:
                print("\n".join(r["lines"]))
        log("dry-run complete: no baselines written, no issues opened.")
        return

    os.makedirs(baselines_dir, exist_ok=True)

    snapshot = {"vendor": vendor, "updated_at": checked_at, "endpoints": {}}
    for name, r in results.items():
        if not r.get("skipped"):
            snapshot["endpoints"][name] = {
                "status": r["status"], "shape": r["shape"], "lines": r["lines"]}

    baseline = None
    if os.path.exists(baseline_path):
        with open(baseline_path) as f:
            baseline = json.load(f)

    if baseline is None or update_baseline:
        with open(baseline_path, "w") as f:
            json.dump(snapshot, f, indent=2)
        log(f"{'re-snapshotted' if update_baseline else 'initialized'} baseline "
            f"at {baseline_path} ({len(snapshot['endpoints'])} endpoints). "
            "Commit this file to the repo.")
        send_telemetry(telemetry_endpoint, vendor, False)
        return

    baseline_at = baseline.get("updated_at", "unknown")
    drifts = []
    for ep in endpoints:
        name = ep["name"]
        snap = snapshot["endpoints"].get(name)
        if snap is None:
            continue  # was skipped this run; never treated as drift
        old = (baseline.get("endpoints") or {}).get(name)
        if old is None:
            log(f"{name}: new endpoint, baselined silently (no alert).")
            baseline["endpoints"][name] = snap
            with open(baseline_path, "w") as f:
                json.dump(baseline, f, indent=2)
            continue
        if old.get("shape") != snap["shape"]:
            diff = list(difflib.unified_diff(
                old.get("lines", []), snap["lines"],
                fromfile=f"baseline ({baseline_at})",
                tofile=f"current ({checked_at})",
                lineterm=""))
            added = sum(1 for l in diff if l.startswith("+") and not l.startswith("+++"))
            removed = sum(1 for l in diff if l.startswith("-") and not l.startswith("---"))
            drifts.append({"name": name, "method": ep.get("method", "GET"),
                           "url": ep["url"], "diff": diff,
                           "added": added, "removed": removed})
            log(f"{name}: DRIFT (+{added}/-{removed} fields)")

    send_telemetry(telemetry_endpoint, vendor, bool(drifts))

    if drifts:
        if create_issue:
            report_drift(vendor, drifts, checked_at, baseline_at)
        else:
            log("drift detected but create-issue is disabled.")
        if fail_on_drift:
            die(f"drift detected in {len(drifts)} endpoint(s).")
        log(f"drift detected in {len(drifts)} endpoint(s); workflow still green "
            "(fail-on-drift is off).")
    else:
        log("no drift: all endpoint shapes match the baseline.")
        if create_issue:
            clear_drift(vendor, checked_at)


if __name__ == "__main__":
    main()
