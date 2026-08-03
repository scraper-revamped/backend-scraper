# Etimad Tender Scraper (backend)

A Flask service that scrapes active government tenders for the main activity
**الاتصالات وتقنية المعلومات** (Communications & IT) from the Etimad portal
(`tenders.etimad.sa`) using Selenium, cleans them into a spreadsheet, and uploads
that spreadsheet to a Google Cloud Storage (GCS) bucket. A **separate** Cloud
Function then reads the bucket and emails matching tenders to subscribers.

Hitting the service's `/` endpoint triggers one full scrape. In production it is
invoked on a schedule (twice daily) via an HTTP request to the Cloud Run service.

---

## 1. Architecture

```
Cloud Scheduler (2x/day)
        │  HTTP GET /
        ▼
   app.py (Flask)  ──►  scrape_n_store_tst.py
                             │  Selenium (headless Chrome)
                             │  → drives tenders.etimad.sa
                             │  → parses tender cards
                             ▼
                        save_to_bucket.py ──► GCS bucket "scraping_revamped_4"
                             │                 path: الاتصالات_وتقنية_المعلومات/…xlsx
                             │
                        alerting.py (emails you if a run fails)

        ── downstream, SEPARATE Cloud Function (send_email.py, not in this repo) ──►
           reads the bucket, fuzzy-matches each subscriber's keywords,
           emails them the matching tenders.
```

### Files

| File | Role |
|------|------|
| `app.py` | Flask entry point. `GET /` runs one scrape. Returns **HTTP 500** on failure so monitoring can see it. |
| `scrape_n_store_tst.py` | The scraper. Driver setup, the Etimad click-through, parsing, cleaning, and the safety nets. **This is the file that runs in production.** |
| `save_to_bucket.py` | Uploads the resulting `.xlsx` to GCS (deletes the previous one first). |
| `secret_getter.py` | Loads GCP service-account JSON from the `SERVICE_ACCOUNT_JSON` env var (used by some helpers). |
| `xpath.py` | Helper mapping activity names → dropdown XPaths (kept for reference). |
| `alerting.py` | Sends a failure email (SMTP) when a run fails or returns zero tenders. |
| `run_local.py` | Convenience runner for local debugging (see §7). |
| `Dockerfile` | Installs Google Chrome + deps, runs `flask run`. |
| `cloudbuild.yaml` | Cloud Build → builds the image and deploys to Cloud Run (`scraper-app`). |
| `templates/index.html` | The page rendered by `/`. |

> **Legacy / unused** (safe to delete later): `schedule.py`, `test_conn.py`,
> `test.ipynb`, `filtered_csv`. They are not part of the deployed path
> (`app.py → scrape_n_store_tst.py`).

---

## 2. How the scrape works (step by step)

`setup_search()` in `scrape_n_store_tst.py`:

1. **Launch Chrome** (`build_driver()`) — headless by default.
2. **Navigate** to `AllTendersForVisitor` and wait `INITIAL_WAIT` seconds for the
   page + its lookups to settle.
3. **Open the search panel** (`searchBtnColaps`). This is what triggers the
   site's AJAX lookups (`Tender.loadLookups()`).
4. **Set the status filter** → المنافسات النشطة (active competitions).
5. **Open the main-activity dropdown** and **wait for it to actually populate**
   (`WebDriverWait` on `#activitiesList` options). If it never fills, the run
   **fails loudly** (see §4) instead of searching with no filter.
6. **Type + select** الاتصالات وتقنية المعلومات and click **بحث** (search).
7. **Wait for results to render** (`wait_for_results`) — the result cards are
   AJAX-injected into `#cardsresult`; we wait for them instead of a fixed sleep.
8. **Parse** every page (`start_parsing` → `get_tenders_from_page`), following
   pagination via `#cardsresult ul.pagination`.
9. **Enrich** each tender with its "purpose" from the detail page
   (`extract_purpose_from_url`).
10. **Clean → DataFrame → upload** (`post_process_results` → `save_to_storage`).

### Why the selectors are class/id-based
The results and pagination are rendered by Etimad's front-end bundle
(`bundle.js` + `vue-app/pagination.js`). The scraper targets **stable
class/id selectors** (`#cardsresult`, `ul.pagination`) rather than positional
`div[N]` paths, which broke in the past when the site's layout shifted.

---

## 3. Environment variables

| Var | Where | Default | Purpose |
|-----|-------|---------|---------|
| `INITIAL_WAIT` | scraper | `180` | Seconds to wait after page load before interacting. Lower it (e.g. `15`) for local debugging. |
| `HEADLESS` | scraper | headless | Set `HEADLESS=0` to launch a **visible** browser locally. Any other value / unset = headless. |
| `SKIP_UPLOAD` | scraper | off | Set `SKIP_UPLOAD=1` to stop before the GCS upload (local debugging, no GCP creds needed). |
| `SERVICE_ACCOUNT_JSON` | GCS | — | Service-account JSON for GCS (on Cloud Run the default service account is used). |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_FROM`, `ALERT_TO` | alerting | — | Optional. Enables failure-alert emails. If `SMTP_HOST`/`ALERT_TO` are unset, alerting is skipped (never crashes the run). |

---

## 4. Safety nets (why they exist)

In July 2026 the scraper silently stopped producing data for days, but kept
logging "success" — so subscribers received **empty emails** and nobody noticed.
These guards make that impossible to repeat:

- **Fail loud, not silent.** If the activity dropdown never populates, or results
  never render, or zero tenders are parsed, the run raises `NoTendersError`
  instead of "succeeding" with nothing. `app.py` returns **HTTP 500**.
- **Debug snapshots.** On any failure, `save_debug_snapshot()` writes the live
  page **HTML + a screenshot** to `gs://scraping_revamped_4/debug/`. This is the
  first place to look when a run fails — it shows exactly what Etimad served.
- **Failure alert email** (`alerting.py`) — emails you the moment a run fails
  (best-effort; needs the SMTP env vars).
- **Downstream freshness guard** (in the separate email function): if the
  scraper's output file is stale, it **skips** the subscriber emails and alerts
  the admin instead of sending empties.

---

## 5. Deployment

Build + deploy is via `cloudbuild.yaml` (Cloud Build → Cloud Run service
`scraper-app`, region `us-central1`).

Notes:
- The scrape takes a few minutes (`INITIAL_WAIT` + pagination), so the Cloud Run
  **request timeout must be generous** (see the timeout note in `cloudbuild.yaml`).
- Headless Chrome needs memory — keep the service at **≥ 1–2 GiB**.
- The runtime service account needs **Storage** access to the bucket, and (if you
  want alerts) the SMTP env vars set.

---

## 6. Downstream email function (separate service)

Not in this repo, but relevant: a Cloud Function reads
`gs://scraping_revamped_4/الاتصالات_وتقنية_المعلومات/…xlsx`, fuzzy-matches each
subscriber's keywords against the tender "purpose", filters out already-seen
tenders, and emails the rest. It also has the **freshness guard** described in §4.
If subscribers get empty or stale emails, check **both** the scraper (did it
upload a fresh file?) and that function.

---

## 7. Local development / debugging

```powershell
# from the backend-scraper folder
pip install -r requirements.txt

$env:HEADLESS   = "0"    # visible browser
$env:INITIAL_WAIT = "15" # don't wait the full 180s
$env:SKIP_UPLOAD  = "1"  # don't upload to GCS

python run_local.py
```

Watch the النشاط الأساسي (main activity) step — if the dropdown populates and the
run parses tenders, you're good. On failure, check the console logs and (in
production) the `debug/` snapshots in the bucket.

---

## 8. Known issues & likely causes of future errors

**This section is the most important for whoever maintains this.** Etimad is
actively defended, so most future breakage falls into these buckets:

### (a) The WAF starts blocking again — *the big one*
Etimad sits behind an **F5 BIG-IP ASM** web application firewall. It allows
normal page navigation but can **reject the AJAX lookup/data calls**
(`/Tender/GetMainActivitiesAsync`, `/Tender/AllSupplierTendersForVisitorAsync`)
when it decides the browser is automated.

- **Symptom:** run fails with `NoTendersError: Main-activity dropdown never
  populated`; the `debug/` snapshot's HTML contains
  `"Request Rejected … Your support ID is: …"`, and the activity dropdown is empty.
- **This already happened once** (mid-July 2026) and blocked the automated browser
  even locally. It was later observed working again — the WAF's behavior is not
  constant, and can differ between a **residential IP (your laptop)** and the
  **Cloud Run datacenter IP**. So a run that works locally can still be blocked in
  production.
- **If it blocks and stays blocked, escalation options (in order):**
  1. Run Chrome **headful under Xvfb** (harder to detect than headless).
  2. Switch to **undetected-chromedriver**.
  3. **Best long-term fix:** use Etimad's official **Tenders Inquiry API**
     (`apiportal.etimad.sa`) instead of scraping the UI — no WAF. It is
     access-gated (request it via the portal / support line 19990). If granted,
     the whole Selenium layer can be replaced with simple API calls while keeping
     the GCS/email pipeline unchanged.
  - Note: a **proxy will not help** — the block is browser-fingerprint based, not
    purely IP based (a residential IP was rejected too).

### (b) Chrome version drift
`google-chrome-stable` auto-updates when the image is rebuilt. Selenium Manager
auto-matches the ChromeDriver, so version mismatches are usually handled — but:
- The **user-agent is pinned** in `build_driver()` (`USER_AGENT`, currently
  Chrome/151). **Bump it** when Chrome jumps a major version, or it becomes a bot
  signal again.

### (c) Etimad changes its front-end / DOM
- The result/pagination selectors (`#cardsresult`, `ul.pagination`) are robust,
  but the **filter-panel XPaths** (`searchBtnColaps`, `#basicInfo/div/div[N]/…`)
  are still positional and can break if Etimad restructures the search form.
- **Symptom:** `NoSuchElement`/click-intercepted errors early in the run.
- **Diagnose** with the `debug/` snapshot and update the affected XPath.

### (d) Timing / slow loads
`page_load_strategy='none'` plus fixed `time.sleep()`s drive the click-through.
`wait_for_results` / the dropdown wait absorb most slowness, but if Etimad gets
much slower you may need to raise `INITIAL_WAIT` or the per-step sleeps.

### (e) Cloud Run resource limits
If the run OOMs or times out: raise **memory** (headless Chrome is hungry) and the
**request timeout**. Symptom: the revision is killed mid-run with no clean error.

### (f) GCS / credentials
If the upload fails: check the runtime service account has Storage write access to
`scraping_revamped_4`, and that `secret_getter`'s `SERVICE_ACCOUNT_JSON` (where
used) is set.

### First things to check when a run fails
1. **Cloud Run logs** — the scraper logs each step (`pressing …`, `activity
   lookup populated OK`, `post processing results`, `Uploaded …`).
2. **`gs://scraping_revamped_4/debug/`** — HTML + screenshot of the failure.
3. **Was the bucket file refreshed today?** If not, the scraper is the problem; if
   yes, look downstream at the email function.
