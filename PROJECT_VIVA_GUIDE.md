# SprayScope: project study and viva guide

This guide is based on the files currently in this repository, not on features that were discussed but never implemented. It is a study reference: understand the flows and limits, then explain them in your own words. Line numbers refer to the current files and may shift if code changes.

## Quick truth sheet

- **Project:** SprayScope, a browser-first prototype for exploring VPN/authentication sign-in events and flagging suspicious patterns.
- **Current working detector:** six deterministic JavaScript rules. **No ML model is used by the live dashboard.**
- **Backend:** a small Node.js built-in HTTP server with three API routes. It shares simulated portal events and saves them in a JSON file.
- **Database:** no database server. There is a JSON file plus browser `localStorage`/`sessionStorage`.
- **Real sign-in:** not configured. Email/password accounts are local to each browser; the Microsoft client ID is blank.
- **Real VPN:** not connected. The User VPN Portal simulates form submissions and scenario events.
- **Data:** four small local CSV files. Three are labeled synthetic fixtures; the mixed sample is unlabeled and illustrative.
- **ML experiment:** an offline LANL logistic-regression training script exists, but the LANL auth archive is incomplete (2,489,109,393 of 7,626,505,158 expected bytes at last inspection). No trained artifact or holdout metrics file is present. Do not claim a trained model or real-data accuracy.
- **Deployment:** local Node server (`npm start`), default port 4173, bound to `127.0.0.1`. No production deployment configuration is present.
- **Most defensible innovation:** putting upload/mapping, explainable rules, incident investigation, a portal simulator, and labeled-fixture evaluation into one demo workflow. The rules and UI patterns themselves are not new algorithms.

## 1. Understand the project

### Level 1: simple explanation

SprayScope reads sign-in records. It looks for suspicious patterns such as many failed passwords against one account, one source trying many accounts, or one account appearing to sign in from far-apart countries too close together. It shows the matching events and lets an analyst explore a basic incident report. The supplied files are demonstration data; this app does not watch a real VPN.

### Level 2: technical explanation

The frontend is a vanilla JavaScript single-page application. It parses CSV/JSON in the browser, maps source columns to a normalized event shape, applies time-window rules in `frontend/src/detectors/detectionService.js`, and renders incident details, timelines, tables, SVG charts, and exports. A Node.js HTTP server serves those files and exposes `/api/health` and `/api/events` for the simulated employee portal. Portal events are persisted to `backend/storage/events.json`; uploaded datasets and rule evaluation remain in browser memory.

### Level 3: deep explanation

There are two different data paths:

1. **Analyst dataset path:** a file is selected or dropped → `file.text()` reads it in the browser → `parseCSV` or `JSON.parse` creates row objects → `guessMap` proposes column mappings → `normalize` maps values into event objects and discards rows missing a valid parsed timestamp, username, or source IP → analyst confirms mapping → `runDetection` runs all six heuristics in the browser → incidents are rendered and, only if labels exist, event-level evaluation is calculated. This path does **not** call the backend.
2. **Portal telemetry path:** the portal constructs synthetic events → writes a capped copy into browser storage → POSTs events to `/api/events` → backend validates, de-duplicates by ID, caps its in-memory list at 5,000, and saves it as JSON → dashboard GETs `/api/events` initially and polls every five seconds while signed in → new events are merged and the browser reruns the rules. If POST fails, the portal still says the event was saved in this browser and uses local storage as fallback.

There is no inference service in the backend. No model receives these live events. There is no VPN gateway, sign-in provider, geolocation API, alert destination, SQL database, or external SIEM connection in the current build.

### Problem, users, solution, and workflow

- **Problem statement:** help an analyst inspect authentication logs for common account-abuse patterns and understand why an event group was flagged.
- **Target users:** a SOC/security analyst or a hackathon evaluator. A real production buyer/user is not validated by this code.
- **Solution:** a local web console that accepts structured auth events, normalizes them, applies explainable threshold rules, and displays incidents and evidence.
- **Workflow:** start Node server → open analyst page → create/sign into a local prototype account (or configure Entra first) → load/upload logs → review column mapping → run detection → inspect incident evidence, timeline, source/user relationships, metrics if labels exist → export CSV/JSON/text.
- **Portal workflow:** open `/?portal=1` → submit a simulated attempt or choose a scenario → portal sends event metadata (not the password) → analyst dashboard polls and re-detects.

## 2. Implemented vs proposed

| Feature | Status | Evidence in project | What you can claim | Limitation / honest wording |
|---|---|---|---|---|
| Analyst SPA and dashboard | 🟢 Implemented | `frontend/index.html`, `frontend/src/app.js`, `frontend/styles.css` | “We built a browser-based analyst console.” | Client-side state; not a multi-tenant SaaS. |
| CSV/JSON upload and field mapping | 🟢 Implemented | `loadFile`, `parseCSV`, `guessMap`, `normalize` | “The browser parses supported CSV/JSON and maps authentication fields.” | Entire file is read into memory; NDJSON is advertised in the UI wording but is not explicitly parsed line-by-line. |
| Brute force, spray, impossible travel, credential stuffing, burst, enumeration rules | 🟢 Implemented | `frontend/src/detectors/detectionService.js:1–11` | “Six transparent heuristics run on normalized events.” | Fixed thresholds, not trained or calibrated on production traffic. |
| Rule-based risk/severity/confidence | 🟢 Implemented | detector `incident()`; `analystService.js:4–7` | “The UI derives scores and severity from rule matches.” | “Confidence” is a formula, not a probability or model confidence. |
| Incident investigation, evidence export, timeline, graph view | 🟢 Implemented | `app.js:49–71`, `attackSourceGraph`, `authenticationTimeline` | “Analysts can inspect evidence and relationships.” | SVG relationship diagram, not graph analytics; some actions are previews. |
| Synthetic attack fixtures and test generator | 🟢 Implemented | `dataset/*.csv`; `app.js:54,90–91` | “We provide labeled synthetic fixtures for a repeatable demo.” | Synthetic results are not real-world performance. |
| Metrics on labeled events | 🟢 Implemented | `metricsService.js`; `app.js:53` | “Event-level precision/recall and confusion counts are calculated when labels exist.” | No metrics for unlabeled data. The displayed metrics are fixture results only. |
| Simulated employee VPN portal | 🟢 Implemented | `app.js:73–80` | “The portal generates fictional sign-in telemetry.” | It does not authenticate an employee or connect to any VPN. |
| Local Node event API | 🟢 Implemented | `backend/server.js:107–136` | “A local API accepts/returns simulated portal events.” | No API authentication, TLS, authorization, or production storage. |
| Portal event persistence | 🟢 Implemented | `backend/server.js:75–82`; `backend/storage/events.json` | “Portal metadata is written to a JSON file.” | It is not a database; one local server/process only. |
| Local analyst email/password UI | 🟡 Partial/demo | `app.js:20–30` | “The prototype stores salted password hashes in this browser.” | No server-side account, reset, session security, MFA, or shared account store. It is not production auth. |
| Microsoft identity | 🟡 Scaffold only | `frontend/src/authConfig.js:1–4`; `loadMsal`, `signInMicrosoft` | “There is an MSAL redirect path awaiting tenant/client setup.” | Client ID is empty; do not say Microsoft sign-in works. |
| LANL model training | 🟡 Script exists, experiment incomplete | `dataset/scripts/train_lanl.py`; `dataset/requirements-ml.txt` | “We prepared an offline logistic-regression benchmark script.” | Auth download is incomplete; there is no trained model/report; it is not wired into the app. |
| LogHub dataset | 🔴 Not included | Link/text in dataset page and README | “We link to LogHub as a possible source.” | No LogHub corpus is downloaded or bundled. |
| Real VPN integration, live detection, blocking, MFA actions | 🔴 Future scope | No connector/control-plane code | “This part is future scope; the current implementation focuses on offline log analysis and a safe portal simulator.” | Do not claim active protection or real authentication monitoring. |
| Microsoft Sentinel query/alert delivery | 🔴 Preview only | incident actions in `app.js:50,94` | “We render a KQL example and local alert preview.” | Query is not submitted; no alert is sent. |
| Cloud deployment, scale-out, production DB | 🔴 Not present | No deployment manifests/service config | “Deployment and production hardening are future work.” | Local server only. |

## 3. Feature-by-feature technical map

| Feature/module | Purpose and input | Processing / model / algorithm / technique | Library, API, database | Output and code location |
|---|---|---|---|---|
| Login UI | Email/password or Microsoft button | Local form validation; PBKDF2-HMAC-SHA-256 via Web Crypto with random 16-byte salt and 150,000 iterations; no ML | Browser DOM/Web Crypto; no API/DB | Local user record/hash and browser auth flag; `app.js:20–32`, `authConfig.js` |
| SPA rendering/state | Current page, events, filters, selected incident | Vanilla JS state object `S`, template-string HTML, event handlers | No UI framework; no API except portal sync | Dashboard pages; `app.js:9–17,33–35,81–84` |
| Upload/parser | File bytes as text, CSV/JSON rows | CSV quote-aware field parsing (not multiline CSV); alias-based mapping; normalize date/result and filter incomplete records; no ML | Browser File API, `parse.js:1–7`; no API/DB | `S.raw`, normalized `S.events`, preview; `app.js:86–89` |
| Detection | Normalized events: time, username, IP, result, country, raw fields | Six deterministic thresholds/window rules; grouping + sorting + sliding end indices; no model | JS `Map`/`Set`; no API/DB | Incident objects with evidence, reason, rule-derived risk/severity; `detectionService.js:1–11` |
| Metrics | Events carrying `label` plus incidents | Event-level TP/FP/FN/TN; precision, recall; alert/true-positive-incident ratio; no model | Plain JS sets; no API/DB | `metricsService.js:1`; UI `app.js:53` |
| Analyst summaries | Users/IPs/events/incidents | Counts, sets, per-entity risk/status summaries, top counts; deterministic aggregation | Plain JS; no API/DB | `analystService.js:1–12`, rendered in `app.js:56–71` |
| Overview chart | Event timestamps/result and detected incident events | 24 fixed bins, manually generated SVG polylines | Built-in SVG; no chart library | Activity series; `app.js:42–44` |
| Timeline | Event timestamps/results and incident first-seen times | 48 fixed buckets; marks buckets containing incident starts | HTML/CSS bars + SVG/DOM; no chart library | Event-volume timeline; `app.js:51,69` |
| Attack source graph | Selected incident's IP, users, location/device | Layout positions nodes around a center and draws SVG lines; no graph algorithm | Built-in SVG; no graph library/API/DB | Interactive relationship picture; `app.js:52,68,82` |
| Portal simulator | Form values/scenario choice | Constructs fictional events; password is checked for non-empty but omitted from event object | Browser `crypto.randomUUID`, local storage, Fetch; POST/GET `/api/events` | Local and/or shared portal events; `app.js:73–80` |
| Backend health/events | HTTP request; event JSON | Validate shape, size, IP/date/result/country; de-duplicate IDs; cap event list | Node built-ins `http`, `fs/promises`, `crypto`, `net`; JSON file, not DB | API JSON; `backend/server.js:27–136` |
| Exports/KQL/alert | Current events/incidents | Serialize into CSV/JSON/text; construct KQL string; local alert text | Blob/Object URL; no external API | File download or preview modal; `app.js:50,93–95` |
| LANL offline benchmark | LANL auth/redteam gzip | Feature engineering + sparse vectorization + supervised logistic regression; chronological train/validation/test; weighted evaluation | Python, NumPy, scikit-learn, joblib; no web API/DB | If successfully run: `.joblib` and `metrics.json`; `dataset/scripts/train_lanl.py` |

### Exact live detection rules

All are deterministic rules. They do not learn a baseline from user history.

| Rule | Condition → result | Risk formula in code | Main failure modes |
|---|---|---|---|
| Brute force | Group failures by username; any window of 5 minutes with at least 10 attempts → Brute Force. If the group has at least 3 distinct IPs, title becomes Distributed Brute Force. | `min(99, 45 + 3 × attempts + 8 if distributed)`; MITRE `T1110.001` | Shared accounts, retries, load tests; distinct attackers/accounts outside one user are missed. |
| Password spray | Group failures by source IP; in 10 minutes, at least 10 distinct users and average attempts/user ≤5 → Password Spray. | `min(99, 55 + distinct users)`; `T1110.003` | Distributed sources evade grouping; benign enterprise NATs can look suspicious. |
| Impossible travel | For each user, compare adjacent successful logins; country codes must map to a centroid, IPs differ, distance >500 km, positive time, implied speed >900 km/h. | `min(99, 75 + round(km/1000 × 10))`; `T1078` | Country is supplied by the log, not verified IP geolocation; VPNs, stale country values, centroid approximation, and account sharing affect results. |
| Credential stuffing | Failures from one IP in a 10-minute window; ≥5 users, ≥30 failures, and average >5 attempts/user. | `min(98, 72 + distinct users)`; `T1110.004` | Threshold overlap with brute force/spray; no password-reuse or credential-list evidence is examined. |
| Abnormal login burst | Any outcomes from one IP in a one-minute window; ≥30 events and ≥10 users. | `min(96, 65 + floor(events/3))`; `T1110` | Scheduled batch jobs/shared proxy can trigger; it is a volume rule, not learned normal behavior. |
| Account enumeration | Failure raw fields contain `unknown user`, `user not found`, `invalid username`, or `account does not exist`; ≥5 distinct usernames from one IP. | `min(92, 62 + distinct users)`; `T1087` | Depends on provider error text; matching arbitrary raw fields can false-positive; wording variants are missed. |

`incident()` caps risk at 100 and assigns severity: ≥80 Critical, ≥60 High, ≥30 Medium, otherwise Low. Confidence is `clamp(round(62 + max(0,risk−40)×0.62), 61, 98)`. That number is a display formula based on risk, **not** calibrated confidence. More than one rule can include the same event, so incidents can overlap.

## 4. Data flow: what happens when you click

### Load and analyze a CSV

User selects a file → browser reads the entire file with `file.text()` → parser creates row objects → field aliases suggest timestamp/user/IP/result/country/device mapping → analyst can change mappings → normalizer parses timestamps, infers success/failure, preserves label/raw fields, and drops rows missing timestamp/user/IP → Run Detection invokes `runDetection(events)` → six rules return incident objects → UI builds tables, SVG, timelines, and evidence → if labels exist, the metrics helper compares event object membership against labels → analyst sees incident/evaluation. **There is no API call, backend preprocessing, database write, or ML inference in this flow.**

### Submit a simulated portal login

User fills portal form → browser requires email/password fields, but only uses password to check it is present → `makePortalEvent` creates a UUID, timestamp, username, documentation IP, country, result, device, user-agent, and scenario → `addPortalEvents` writes up to 800 portal records in this origin's local storage and locally updates up to 1,000 current events → POST `/api/events` → server limits body to 256 KiB and batch to 1–500, rejects password keys, validates required values/IP/result/country, de-duplicates, caps at 5,000, serializes JSON via temp file then rename → API returns accepted/total → analyst page GETs and then polls `/api/events` every 5 seconds → new IDs are merged and browser rules are rerun. API failure leaves the browser-local fallback. Password is not part of the POST payload.

### Microsoft button

Currently: client ID is empty → click shows setup message; no identity redirect occurs. If a valid Entra SPA registration/client ID is later supplied, code loads MSAL from a Microsoft CDN and calls `loginRedirect`. That future configured path still does not create a backend account/session in the current server.

### Offline LANL model path

LANL gzip labels are loaded → exact redteam event tuples are matched against auth rows → event types and cumulative entity counts are engineered → categorical fields are sparse one-hot encoded → logistic regression is fit on earlier dates → validation dates select an F1 threshold → final dates evaluate it with inverse-probability weights → joblib and JSON report are saved. This is separate from the browser rules and cannot presently be demonstrated as a trained model because the auth archive is incomplete and no result files exist.

## 5. Innovation and uniqueness (honest framing)

- **Core innovation:** one small, explainable demo connects auth-log exploration, pattern-based triage, evidence review, and repeatable synthetic evaluation in one workflow.
- **Technical innovation:** no novel algorithm is implemented; the technical choice is transparent, hand-coded threshold rules plus a separate planned supervised baseline.
- **Product innovation:** a student/evaluator can generate a pattern through the simulated portal and inspect it on an analyst dashboard without a real VPN or credentials.
- **Combination/workflow innovation:** the project's strongest differentiator is the combination of upload/mapping, rule explanations, incident drill-down, and local portal simulation—not invention of brute-force detection.
- **“This already exists. What is new?”** “The detection concepts already exist in SIEM products. Our prototype focuses on an understandable end-to-end learning/demo workflow: generate or load auth events, see the exact rule evidence, and inspect the resulting incident. We are not claiming a new detection algorithm.”
- **“Why use it instead of an existing solution?”** “For a hackathon, it is a lightweight, low-setup demonstrator. For a real SOC, an existing SIEM may be preferable until we add secure integrations, data retention, and production controls.”
- **20-second answer:** “SprayScope is a browser-based VPN sign-in investigation prototype. It normalizes authentication logs, runs transparent rules for common account-abuse patterns, and shows event evidence and incident context. Its current data and portal are demo/synthetic; production VPN/SIEM integrations are future work.”
- **1-minute answer:** “Analysts receive many login records but need to spot patterns across accounts, sources, time, and location. SprayScope accepts structured CSV or JSON, maps common fields, and applies six explainable time-window rules. The incident view shows the matching events, reason, risk band, and a source-to-user diagram; labeled synthetic fixtures let us compare event-level predictions with known labels. A separate local Node API shares simulated portal events. The live dashboard is rule-based, not ML. Our next step is real, permissioned log integration and a validated holdout study.”
- **Deep answer:** “The prototype splits work between browser-side analysis and a Node event API. The browser normalizes records and groups/sorts events by user or source IP before applying fixed thresholds. The API only persists portal simulator telemetry to JSON. The offline LANL script is a distinct supervised baseline that would use sparse features and chronological evaluation, but it is not trained or integrated yet. The product's current innovation is workflow and transparency, with significant production scope remaining.”

## 6. Exact 6–7 minute demo plan

Prepare the app before the panel: start `npm start`, create/sign into a local prototype account, open Dataset, and confirm the CSV files are reachable. Use the current code's attack-specific fixture plus the visible labels; do not depend on Microsoft sign-in or the incomplete LANL file.

| Time | Click/show | What to say / concept | What evaluator checks |
|---|---|---|---|
| 00:00–00:30 | Show title/sign-in. | “VPN sign-in logs contain patterns that are easy to miss when viewed one row at a time.” | Clear problem and target analyst. |
| 00:30–01:00 | Sign in to the local demo account. State it is browser-local. | “This login is prototype auth. Microsoft Entra is not configured in this copy.” | Honesty; ability to run. |
| 01:00–02:00 | Overview; point out loaded/simulated data badge, event activity, rule engine. | “The overview is a local event view. The default stream is synthetic, not a live VPN feed.” | Data source and product flow. |
| 02:00–03:00 | Dataset → Brute Force fixture → Load → Continue to mapping; show mapped timestamp/user/IP/result. | “The file is read in the browser, aliases propose a mapping, and normalized events stay client-side.” | Ingestion and schema understanding. |
| 03:00–04:00 | Run detection; open the Brute Force incident; show evidence rows and reason. | “The rule groups failed events by account and checks a five-minute window for ten or more attempts.” | Exact algorithm/threshold and evidence. |
| 04:00–05:00 | Show why-detected signals, timeline, source graph, export evidence or KQL preview. | “The graph is an SVG relationship view; KQL and alert are local previews, not sent to Microsoft.” | Implementation depth and limits. |
| 05:00–06:00 | Metrics page on the labeled fixture. State measured values below. | “These are synthetic fixture metrics, not real-world model metrics. The detector is rules.” | Ground truth and metric definition. |
| 06:00–07:00 | Optionally show `/?portal=1` attack scenario and API, then conclude. | “Portal events are fictional and go through a local JSON-backed API; actual VPN enforcement and production identity are future scope.” | End-to-end flow, feasibility, candor. |

### Measured fixture results in this repository

These were calculated by running the repository's own parser, normalizer, detector, and `calculateConfusionMatrix` against the current CSVs. They are reproducible but synthetic.

| Fixture | Rows | Detected incident(s) | TP / FP / FN / TN | Precision | Recall | Alert/TP-incident ratio |
|---|---:|---|---|---:|---:|---:|
| `brute-force-only.csv` | 17 | 1 Brute Force (11 events) | 10 / 1 / 1 / 5 | 90.9% | 90.9% | 1.00 |
| `password-spray-only.csv` | 18 | 1 Password Spray (13 events) | 12 / 1 / 1 / 4 | 92.3% | 92.3% | 1.00 |
| `impossible-travel-only.csv` | 13 | 4 Impossible Travel (2 events each) | 6 / 2 / 2 / 3 | 75.0% | 75.0% | 1.33 |

The travel fixture currently generates four incidents and has two false positives/two false negatives at the **event** level. This is a useful honest limitation to show, not something to hide. The alert/TP ratio is incident-level and differs from event precision/recall. The UI's metric code does not calculate accuracy or F1 for fixture metrics.

### Backup demo

- **Internet fails:** dashboard and local fixtures work without internet once Node is running. Microsoft CDN sign-in may fail; use local prototype account. No LogHub download is required.
- **API fails:** portal falls back to browser-local event storage; say shared persistence is offline and show local fixture instead.
- **Server stops:** restart with `npm start`; if port 4173 is occupied, stop the old Node process first. Do not claim the API works while it is stopped.
- **JSON storage fails:** API returns an error; use a fixture and disclose portal persistence is unavailable. Do not pretend events were saved server-side.
- **Model fails/missing:** the live app has no ML model. Show the deterministic rule flow; don't fabricate model output.
- **Data missing:** use one of the bundled CSV fixtures. If those files are unavailable, stop and explain the blocker; don't create a live-data claim.
- **App crashes:** reload after saving no state assumption; re-run the local fixture. Exports are downloads, and dashboard state is not durable across reloads.

## 7–10. Demonstration depth, important code, and AI/ML

### Must know / should know

| Priority | Code | Be ready to explain |
|---|---|---|
| 🔥 Must know | `frontend/src/detectors/detectionService.js:1–11` | Event grouping, time windows, thresholds, risk score, evidence, overlap, why it is not ML. |
| 🔥 Must know | `frontend/src/utils/parse.js:1–7` and `app.js:86–92` | CSV/JSON input, mapping, normalization, required event fields, filtering, client-side analysis. |
| 🔥 Must know | `backend/server.js:27–136` | API validation, 256-KiB body limit, 500-event batch, 120 requests/IP/minute, de-duplication, JSON persistence, endpoint semantics. |
| 🔥 Must know | `app.js:76–80` | Portal event creation, password omission, POST/fallback, scenario generation. |
| 🔥 Must know | `metricsService.js:1` | Event-level confusion counting and exactly which metrics are/aren't computed. |
| ⭐ Should know | `app.js:20–32`, `authConfig.js` | Local PBKDF2 browser auth; empty Microsoft client ID; no backend identity. |
| ⭐ Should know | `app.js:42,51–55,68–71` | SVG/DOM charts, generated report, local KQL/alert previews, metric gating. |
| ➕ Good to know | `analystService.js:1–12` | Entity summaries, severity display, formula-based confidence. |
| ➕ Good to know | `dataset/scripts/train_lanl.py` | Proposed offline logistic-regression experiment and its current incomplete status. |

### Line-by-line viva explanation for the brute-force rule

`detectionService.js:1` defines `MIN = 60000`, so five minutes is `5 * MIN` milliseconds. In line 3 the function filters to `result === 'failure'`, groups the remaining records by `username`, sorts each account's events by timestamp, and advances an `end` index while events remain within five minutes of the current start. If the window holds at least 10 failures, it creates an incident containing those events. It counts distinct source IPs; three or more changes the incident label to distributed brute force. The rule then assigns a capped score, MITRE tag, and human-readable reason. `incident()` sorts the evidence, derives unique users/IPs, first/last time, risk band, and deterministic incident ID. This is a threshold/pattern rule; no training, feature model, or probability is involved.

### AI/ML: exact current status

**Live app:** “No ML/AI model is used. The live detector uses deterministic/rule-based logic.” No inference model, training endpoint, or model metric appears in the dashboard path.

**Offline script (not yet run successfully):**

- **Model:** scikit-learn `LogisticRegression`, `solver='liblinear'`, `max_iter=500`, `class_weight='balanced'`, fixed `random_state`.
- **Learning/task:** supervised binary classification of exact LANL red-team-labeled auth rows versus sampled non-matches.
- **Features:** one-hot `auth_type`, `logon_type`, `orientation`, `result`; booleans `same_user`, `same_host`, seen-before flags for source/destination users and hosts; `log1p` cumulative counts for those four entities. `DictVectorizer` creates a sparse float32 matrix. Counts are computed before the current event updates the counters.
- **Split:** ordered unique redteam timestamps, roughly first 70% train, next 15% validation, final 15% holdout test. Rejects an auth stream whose timestamps go backward.
- **Negative sampling:** 0.0001 probability with deterministic Python RNG; sampled negatives receive inverse-probability weight 10,000 for evaluation. All positives are retained. Training additionally uses `class_weight='balanced'`.
- **Threshold/metrics:** choose threshold from up to 201 quantiles of validation scores to maximize weighted F1; evaluate the untouched test period with weighted precision, recall, F1, accuracy, average precision, ROC-AUC, and weighted confusion matrix.
- **Outputs:** joblib bundle with vectorizer/model and `metrics.json` under `dataset/models/lanl/`, if the run completes.
- **Actual status:** LANL redteam file exists (749 rows, 715 unique tuples), but auth gzip is truncated/incomplete. No `.joblib` or `metrics.json` is present. No accuracy/precision/recall from LANL can be claimed.
- **Caveat:** unlabeled auth events are treated as negatives, so some truly malicious unlabeled behavior may be mislabeled; labels cover known red-team activity only. LANL anonymized host/user auth events have no public IP/country, so they do not validate VPN impossible-travel behavior.
- **Why logistic regression as baseline:** sparse one-hot features fit a linear, relatively interpretable and lightweight baseline. It establishes a benchmark; it does not prove it outperforms rules.
- **Alternatives (future experiments only):** Random Forest can model nonlinear feature combinations but is heavier and less transparent; Isolation Forest could flag novelty without attack labels but its outlier score is not a calibrated attack probability. Neither is implemented here.

### Rule-based vs ML answer

For the current product, rules were chosen because the demo needs visible, explainable conditions and works without a training corpus. Advantages: easy to audit, quick to run, deterministic. Disadvantages: fixed thresholds can false-positive on shared proxies/batch jobs and false-negative on distributed/low-rate attacks. ML could help rank unusual behavior only after collecting representative, permissioned data and evaluating on a proper time-separated holdout; it should complement, not silently replace, analyst-visible rules.

## 11. Cybersecurity details: signals, decisions, and risk

The analyzed inputs are normalized timestamp, username, source IP, success/failure result, optional country/device/user-agent, optional label, and raw source fields. The rules actually use:

- **Brute force:** username, timestamp, result, source-IP diversity.
- **Password spray:** source IP, timestamp, result, distinct usernames, average attempts/user.
- **Impossible travel:** username, timestamp, result, country code, and whether source IP changed. It computes centroid-to-centroid great-circle distance with a Haversine-style formula; it does not geolocate IPs.
- **Credential stuffing:** source IP, timestamp, result, distinct users, attempts/user.
- **Burst:** source IP, timestamp, distinct users, event count.
- **Enumeration:** source IP, timestamp, failed result, raw text matches, distinct usernames.

There is no full three-class `normal/suspicious/malicious` classifier. Most events absent from an incident are displayed as normal or suspicious using simple event-status heuristics (a failure can display “suspicious”); only incident membership is the detector's positive/suspicious result. “Malicious” is not proven by a rule match.

**Risk score:** hand-coded per-rule arithmetic and cap, then severity thresholds. **Confidence:** formula derived from risk only. No learned weights, feature importance, calibration, feedback loop, or analyst outcome training exists.

## 12–16. Graph, visuals, backend, frontend, and storage

### Graph analysis

The Attack Source Graph is a visualization, not a graph-analysis engine. Nodes represent a detected incident's source IP, up to eight affected usernames, and available country/device/gateway context; lines depict associations. SVG circles and lines are laid out around a center. Users can select incident/nodes, zoom, pan, reset. There is no graph database, adjacency-matrix model, PageRank, shortest-path algorithm, centrality calculation, or graph-based detection. Rendering is O(V+E) for the displayed nodes/edges; there is no graph algorithm complexity to claim.

### Dashboard/visualization inventory

| Visualization | Data / type | Library / technique / purpose |
|---|---|---|
| Overview activity | success/failure/detected events; hand-built SVG polylines with 24 bins | Native SVG, trend preview; no chart package. |
| Event timeline | loaded event counts in 48 buckets; CSS/DOM bars with attack-start flags | Time distribution; no chart package. |
| Attack source graph | incident/IP/users/location/device relations; SVG node-link diagram | Relationship exploration only; no graph-analysis library. |
| Tables, stats, risk bars, geographic counts | in-memory aggregation of current events/incidents | HTML/CSS, not external visualization framework. Geographic counts use logged country values, not a map/IP lookup. |
| Replay | sorted incident events advanced every 750 ms | Timer-driven UI simulation; no video/ML model. |

### Backend API

Language/runtime is JavaScript on Node.js 20+, using Node built-ins—no Express/Fastify and no npm runtime dependencies.

| Endpoint | Method | Request | Processing | Response / purpose |
|---|---|---|---|---|
| `/api/health` | GET | none | Applies per-IP rate limiter; reports event count | `200 {ok, service, events}` health status. |
| `/api/events` | GET | none | Returns current in-memory portal event list | `200 {events:[...]}`; dashboard sync. |
| `/api/events` | POST | JSON array or `{events:[...]}`, 1–500 event objects, max body 256 KiB | Reject passwords; validate timestamp/email-like username nonempty/source IP/country/result; cap field lengths; de-duplicate portal IDs; retain last 5,000; enqueue file write | `201 {accepted,total}`; malformed input `400`, rate-limit `429`. |
| Other `/api/*` | any | route-dependent | No matching route | `404 {error}`. |
| Static app | GET/HEAD | path | Serves `frontend/`; `/dataset/*` and legacy `/data/*` serve safe fixture paths; blocks LANL/model files and traversal | HTML/CSS/JS/CSV, not a JSON API. |

Rate limiting is an in-memory fixed 60-second counter of 120 API calls per remote IP. The backend validates the portal API payload, not arbitrary uploaded CSV rows. It has no login/authorization for the API. No query goes to a database.

### Frontend state and modules

- **Framework:** none; vanilla ES modules, HTML templates, CSS, DOM event handlers.
- **State:** object `S` in `app.js` holds current page, events, mapped columns, incidents, filters, replay state. It is mostly in memory; data/detections disappear on reload.
- **Auth storage:** local browser `localStorage` for account hashes/remembered login and portal events; `sessionStorage` for session login. Not shared between browser profiles/devices.
- **API calls:** Fetch only for portal events (`POST /api/events`, `GET /api/events`); upload and detector are client-side.
- **Forms:** local sign-up/sign-in, dataset file input/drop, column mapping, synthetic generator, portal attempt form. Browser required/type attributes plus some JS checks; backend validation only on event API.
- **Errors:** toast messages for failed login/file load/API fallback; API JSON errors; no global error boundary or centralized logging service.
- **External dependencies:** conditional Microsoft MSAL script from Microsoft CDN if configured. Current blank client ID means it is not loaded for actual sign-in. No charting framework.

### Storage/database reality

There is **no database technology/table/collection/query/index** in this project. The backend loads/writes `backend/storage/events.json` as a JSON array. Important event fields include `portal_event_id`, timestamp, username, source IP, country, result, device, user-agent, action, simulation, scenario. The file is loaded at startup; POST appends fresh IDs; the last 5,000 are retained; writes serialize the full array to a temp file and rename it. Browser local storage also holds portal events (up to 800), and email account salt/hash records. There are no relationships or SQL CRUD. For scale, a real database would need tenant scoping, retention, indexes (time, user, source), and paginated queries.

## 17–19. Load, scalability, and feasibility

### Current load profile

| Area | Current work | Main cost/problem | Practical improvement (future) |
|---|---|---|---|
| File ingest | Browser reads whole file and stores raw + normalized arrays | Peak RAM roughly multiple copies; no upload size cap | Streaming/chunked parser, row limits, progress/cancel, server-side jobs for large data. |
| Rules | Browser filters/groups/sorts and reruns on portal sync | Repeated scans and window slicing; no indexes/caches | Pre-group/index by user/IP/time, deduplicate event scans, benchmark before optimizing. |
| Rendering | Tables and SVG generated from all/current data | Large tables/derivations can block UI | Pagination/virtualized rows, memoize summaries, debounce expensive filters. |
| Portal API | Dashboard polls every 5s; all events returned | N clients create ~N/5 GETs per second; shared NAT clients share a per-IP limit | Backoff or server-sent events later; pagination/tenant filters. Don't add queues/CDN without a need. |
| Persistence | JSON list rewrites to temp file on POST | Full-file serialization per batch, one process, race/scale limits | Database with indexes and transactions when real multi-user workload exists. |
| ML benchmark | If run, parses auth archive and keeps sampled feature rows in Python memory | Large gzip scan, memory/duration; no background job orchestration | Offline batch worker/streaming feature storage and measured resource limits. |

### First bottleneck

For the current multi-user API, the first structural bottleneck is the single-process in-memory event array plus full JSON rewrite and polling of the entire event list. For a large analyst upload, the first bottleneck is likely browser RAM/main-thread work because the whole file and normalized results are held at once. Do not claim to support one million users.

### 10 / 1,000 / 100,000 / 1,000,000 users

| Scale | Honest current behavior | What must change |
|---|---|---|
| 10 demo users | Fine for small controlled fixtures and local API if sharing one server. | Add repeatable smoke tests and clear data reset/retention. |
| 1,000 active users | Not validated. Five-second polling is ~200 GET requests/second at 1,000 clients; same NAT may hit shared 120/minute/IP limit long before that. | Authenticated tenants, event pagination/push, database, per-user quotas, deployment monitoring/load tests. |
| 100,000 | Single JSON file/process and browser-side per-client data processing do not fit. | Horizontally scaled API, durable indexed DB/object storage, queues for heavy analysis, rate limiting and observability. |
| 1,000,000 | No current capability claim. | Multi-region/tenant architecture, partitioned storage, load balancing, cache only derived read-heavy views, background processing, fault tolerance, security reviews, model serving only if evaluated need exists. |

### Feasibility answer

- **20 seconds:** “The concept is feasible using existing web and log-processing technology, and this prototype demonstrates a small local slice. Production feasibility depends on secure identity/log integrations, data governance, and validated detection quality.”
- **1 minute:** “The demo runs on an ordinary Node-capable computer and browser; it needs no GPU. Production use would require a real source of sign-in logs, secure multi-user identity, encrypted transport/storage, durable indexed persistence, monitoring, and a measured false-positive rate. Those integrations and operational controls are not in this build, so we present it as a prototype.”
- **Deep:** “The rules are inexpensive for small sets but current upload work is in the browser, and the shared API returns and rewrites a bounded whole JSON list. The first scale transition is replacing browser-local auth and single-file persistence with tenant-aware identity and indexed storage; then move large file analysis to controlled jobs and avoid full-list polling. Cost and latency depend on log volume, retention, identity/geo providers, and alert SLAs, none of which are measured here.”

## 20–22. Problem fit, security, and edge cases

### Skeptical problem-fit answers

- **Does it solve the problem?** It demonstrates how auth logs can be grouped and rule-flagged. It does not yet protect a live VPN or prove SOC outcomes.
- **Who benefits?** A student/evaluator can inspect explainable examples; a real analyst could benefit only after integrating their log source and validating thresholds.
- **Measurable benefit?** Current measurable values are fixture confusion counts. No analyst-time reduction, incident reduction, latency SLA, or production precision is measured.
- **Why better than doing nothing?** It gives a repeatable triage workflow and explicit evidence, but its detection coverage is limited to the rules and schema supplied.
- **Why not existing SIEM?** A SIEM has production integrations and controls. This prototype is easier to demo/modify in a hackathon; it is not a replacement claim.
- **Unsolved:** distributed low-rate attacks across IPs, identity context, MFA state, device baselines, trusted IP geography, incident response, production-grade auth/data tenancy.

### Security review (only relevant controls)

- Passwords typed into the portal are required by the form but omitted from the generated event and rejected if present in API event JSON. This is good for the simulator, but it is not a real credential flow.
- Local analyst password hashes use per-user random salt and PBKDF2-SHA-256 (150,000 iterations) in Web Crypto. Hash records are in browser local storage; this is not server-side authentication and can be bypassed/modified by the browser owner. No reset, lockout, MFA, session cookie, or shared account authority.
- The Entra/MSAL path is not live because `MICROSOFT_CLIENT_ID` is blank. No client secret is present.
- API has no authentication or authorization. Anyone who can reach it can read/add synthetic event records. Default host is `127.0.0.1`; changing `HOST` for remote access increases exposure. There is no TLS termination in Node.
- Backend validation: body-size/batch limits, valid IP, valid timestamp/result, country format, password-key rejection, string truncation, request rate limiter. It is demo hardening, not complete API security.
- JSON templating uses an `esc` helper in many display locations, but escaping must be reviewed on every output path before real untrusted data. No Content-Security-Policy, HSTS, or production security header suite is configured. Static responses include `X-Content-Type-Options: nosniff`; API responses also use `Cache-Control: no-store`.
- No SQL means SQL injection is not applicable. XSS is still relevant to dynamic HTML. CSRF is not solved by a production session design because there is no authenticated API session; API has no CORS configuration, but that alone is not a complete security architecture.
- Demo emails/IPs and portal events persist locally; define retention, deletion, privacy, audit, and tenant boundaries before real logs.

### Edge cases (observed behavior / expected improvement)

| Scenario | Current behavior | Handled? | Better production behavior |
|---|---|---|---|
| Empty file | Shows “no rows”/load error | Partly | Clear file-level validation and recovery. |
| Missing required mapped field | Mapping UI allows manual choice; normalized rows can be filtered away | Partly | Block analysis and name missing field. |
| Invalid timestamp | Normalizer drops row after invalid date | Partly, silently | Count/report rejected rows. |
| Invalid source IP in uploaded CSV | Client accepts string and rule groups it | No validation | Validate/mark invalid field before analysis. |
| Unknown result word | Normalizes to `unknown`; rules generally ignore it | Partly | Preserve unknown separately in UI and metric denominator. |
| Quoted CSV comma/doubled quote | Parser handles common cases | Partly | Support multiline quoted cells and malformed quote diagnostics. |
| NDJSON file | UI mentions line-delimited JSON; whole-file `JSON.parse` fails then CSV fallback | No | Parse one JSON object per line or remove the claim. |
| Huge upload | Entire text, row array, normalized events retained in memory | No | Size/row limits, chunked parsing, cancellation. |
| Duplicate uploaded rows | They remain duplicated and may inflate rule windows | No | Deduplicate or visibly report exact duplicates. |
| Out-of-order records | Detector groups and sorts before its windows | Mostly | Validate timestamp coverage and explicit timezone. |
| Missing/unknown country | Impossible-travel rule skips unrecognized codes | Yes, conservative | Show “not evaluated” and reason. |
| Wrong country / VPN exit point | Can false-positive or miss travel | No | Trusted geolocation source and known VPN egress context. |
| Overlapping rule matches | Same event may appear in multiple incidents | Partly | Correlate/merge incidents and define metric semantics. |
| Account enumeration wording differs | Regex misses unknown phrases | No | Provider-specific parsers/configurable signatures. |
| Unlabeled dataset | Metrics UI states unavailable | Yes | Keep unavailable; never infer accuracy. |
| Partially labeled file | Any label enables metrics; blank labels are omitted from TN/FP and positive labels drive TP/FN | Risky | Require complete labels or show coverage and exclude/stratify explicitly. |
| API offline | Browser localStorage fallback; portal indicates backend offline | Yes for demo | Retry with backoff and visible sync status. |
| API sends malformed/oversized event | Returns 400; API rate limit 429 | Yes, basic | Structured validation errors, logs, per-tenant quotas. |
| JSON disk/write failure | POST catches and returns 400; old memory may already have been updated | Partly | Transactional durable DB and rollback/error monitoring. |
| Multiple Node instances | Each has separate memory and can race file writes | No | Shared DB/locking/transactions. |
| Unauthorized caller | API has no identity check | No | Entra/OIDC server validation and authorization. |
| User reloads page | in-memory dataset/incidents reset; only limited browser keys persist | No | Explicit saved investigations and data retention. |
| Partial LANL gzip | Training likely errors on truncated gzip; current code has no model output | No | Complete archive checksum/version and preflight validation. |

## 23. Product potential and realistic limits

- **Possible users:** small IT/security teams, a managed service provider, or a training lab that wants to inspect authentication events.
- **Possible product:** a hosted ingestion and triage service with supported identity-provider connectors, tenant-specific rules, an analyst workflow, audit history, and alert delivery.
- **Business model to investigate:** per identity, event volume, or tenant subscription. These are hypotheses for customer interviews, not validated pricing.
- **Why this prototype is not deployable for real security operations yet:** it has no authenticated ingestion, tenant isolation, durable database, production authorization, monitoring, or validated integrations. Its geography uses country centroids and its input may be synthetic.
- **A responsible claim:** “SprayScope demonstrates explainable authentication-event triage and gives a foundation for testing with a real identity provider.” Avoid claiming it prevents attacks or outperforms a SIEM.

## 24. Team contribution and use of AI

Do not invent individual contribution details. Say what you personally built or researched, then describe the rest of the team accurately. A safe answer if asked about AI is:

> “We used coding assistance to accelerate implementation and documentation. The team reviewed the code, ran the demo, and checked the behavior against the fixtures. We are responsible for understanding and presenting it; we do not claim generated code as independent research.”

For team division, explain ownership by deliverable: two frontend contributors, two backend contributors, and one dataset/ML contributor. Replace that description with the actual names and tasks your team completed before the panel.

## 25. Twenty difficult panel questions

| Question | Strong concise answer | Technical follow-up |
|---|---|---|
| 1. What exactly did you build? | A browser dashboard and local Node service that analyze authentication events with six explainable heuristics. | Rules operate on normalized event fields; this is not a production SIEM. |
| 2. What is the core innovation? | An explainable hackathon workflow that lets a user generate or upload auth events and inspect evidence behind alerts. | The prototype's contribution is the workflow and transparent rules, not a new detection algorithm. |
| 3. Is the live system AI/ML? | No. The live dashboard uses deterministic rules. | There is an offline logistic-regression experiment for LANL, but no trained artifact or dashboard integration. |
| 4. Why use rules instead of ML? | Rules are easy to explain and work with small labeled demo fixtures. | ML needs representative, labeled data and careful time-based validation; rules still need tuning. |
| 5. Are your results real? | The current reported fixture metrics are measured on bundled synthetic labeled CSVs. | They validate code behavior on those fixtures, not real-world detection performance. |
| 6. Why is precision below 100%? | A rule can include benign events near the suspicious pattern, and fixtures deliberately include a false alert. | Precision is TP/(TP+FP); the exact counts are in the guide and fixture metrics. |
| 7. How do you calculate recall? | Recall is the share of labeled attack events included in at least one incident. | It is event-level and uses incident event IDs; it is not user- or incident-level recall. |
| 8. Why not report accuracy? | The dashboard reports precision, recall, confusion counts, and alert-to-TP ratio. | Accuracy is not currently shown and can mislead with class imbalance. |
| 9. What is confidence? | A rule-derived ranking score for triage. | It is not a calibrated probability and must not be described as one. |
| 10. What does impossible travel mean here? | Two successful events for a user appear far apart in known-country centroid estimates over a short interval. | It uses coarse country centroids and a speed threshold, so VPNs and bad geo data can produce errors. |
| 11. Why are there multiple incidents? | Each detector emits incidents independently; patterns can overlap. | Correlation/merging and alert-level metric semantics are future work. |
| 12. Where is the database? | The demo persists backend events in a JSON file and browser preferences/accounts locally. | That is not a concurrent multi-instance database or production identity store. |
| 13. How is the API secured? | It has basic input and size limits and binds to localhost by default. | It has no API authentication, authorization, or TLS termination, so it is not for public production exposure. |
| 14. Does the portal test real passwords? | No. It generates training events and does not store or transmit the password. | It is a simulator, not a credential validation service or a real VPN. |
| 15. Does Microsoft sign-in work now? | It needs an Entra SPA client ID to be configured. | Without it the UI explains configuration; no fake Microsoft identity is created. |
| 16. What happens with missing labels? | Metrics are unavailable for an unlabeled dataset. | For partially labeled data, blank labels are excluded from confusion counts; coverage should be made explicit. |
| 17. Why use LANL? | It is a public authentication dataset with red-team annotations for an offline experiment. | The local copy is incomplete and cannot produce a trustworthy benchmark yet; it lacks IP/country fields. |
| 18. What is the biggest technical limitation? | The detectors are heuristics evaluated on small synthetic fixtures. | Large uploads are in-memory, and the API has one-process JSON storage. |
| 19. What would you build next? | Add authenticated ingestion and validate on a complete, representative labeled dataset. | Then establish time-based holdouts, alert deduplication, and operational monitoring. |
| 20. Can this stop an attack? | No. It raises triage signals; it does not block logins or control a VPN. | Response actions need identity-provider integration, authorization, safeguards, and measured false-positive rates. |

## 26. One-minute technical revision sheet

| Topic | Remember this |
|---|---|
| Frontend | Vanilla JavaScript SPA, HTML, CSS, manual SVG/DOM visualizations. |
| Backend | Node.js built-in HTTP/static server; `GET /api/health`, `GET/POST /api/events`. |
| Persistence | JSON event file on server; browser localStorage/sessionStorage for client state. No database. |
| Detection | Six deterministic heuristics: brute force, spray, impossible travel, credential stuffing, burst, enumeration. |
| ML | Offline scikit-learn logistic-regression LANL experiment only; no current trained model artifact or live integration. |
| Metrics | Labeled synthetic fixtures only; event-level TP/FP/FN/TN, precision, recall, alert-to-TP. |
| Auth | Local browser PBKDF2 demo; Microsoft Entra needs SPA client ID; backend is not authenticated. |
| Privacy | Portal omits password from event; never send real credentials or real logs to an exposed demo. |
| Visuals | Hand-built SVG/DOM, no charting library; entity graph is a relationship display, not graph analytics. |
| Deployment | Local hackathon prototype. Real deployment needs identity, access control, TLS, database, monitoring, and data validation. |

**Libraries/frameworks:** Node.js built-ins; browser Web APIs (Fetch, Web Crypto, localStorage, Blob); optional MSAL Browser loaded from CDN if configured; Python scikit-learn, pandas, NumPy, and joblib for the offline experiment. The main website has no framework or chart library. **Database:** none. **Model in live dashboard:** none. **Offline model:** logistic regression.

## 27. Honest current project score

This is a preparation estimate, not an official judge score. A panel may weight categories differently.

| Category | Estimate | Reason |
|---|---:|---|
| Working demo | 21/25 | Local UI, API, portal, fixtures, and investigative actions are demonstrable. |
| Technical depth | 10/15 | Clear rules and data flow; limited production architecture and no live ML. |
| Implementation quality | 13/20 | Modular frontend and a small API, but local storage and edge-case gaps remain. |
| Problem fit | 10/15 | Relevant auth patterns; no real identity-provider or VPN telemetry connection. |
| Product/scalability | 5/15 | Plausible direction, but no validated users, tenant model, database, or deployment. |
| Team clarity | 5/10 | Work split is documented; exact individual ownership and evidence should be prepared by the team. |
| **Estimated total** | **64/100** | Stronger as an explainable prototype than as a production security product. |

## 28. Highest-value improvements

| Priority | Improvement | Impact | Effort |
|---:|---|---|---|
| 1 | Present it explicitly as a prototype; distinguish simulated, synthetic, and measured values in the demo. | High | Low |
| 2 | Fix and document the partially labeled metric behavior; show label coverage and metric unit. | High | Low–medium |
| 3 | Deduplicate/correlate overlapping incidents and define incident-level as well as event-level metrics. | High | Medium |
| 4 | Add upload validation and a rejected-row report; handle NDJSON truthfully. | High | Medium |
| 5 | Run the fixtures live and explain a false positive, not just a headline percentage. | High | Low |
| 6 | Add authenticated API access before any remote demo and keep public deployment disabled meanwhile. | Very high for deployment | High |
| 7 | Replace JSON file persistence with a transactional database and define tenant boundaries. | High for scale | High |
| 8 | Complete LANL download, verify checksums, then report a reproducible chronological holdout result. | Medium | Medium–high |
| 9 | Configure Entra with a test tenant and validate server-side identity if shared access is needed. | Medium | Medium–high |
| 10 | Collect analyst feedback and labeled, consented data to tune thresholds and measure operational value. | High | Ongoing |

## 29. One-minute project script

> “SprayScope is a hackathon prototype for triaging suspicious VPN-style authentication events. An analyst can load a dataset or use a simulated user portal; the frontend normalizes the events and applies six explainable rules for patterns such as brute force, password spray, and impossible travel. Each alert shows its evidence and a rule-derived risk score. We measure precision and recall only when the input has labels; the bundled scores are from small synthetic fixtures, not a real-world benchmark. The live dashboard is rule-based. We have an offline logistic-regression experiment planned for LANL authentication data, but it is not trained into or connected to this app. Today, the Node backend stores demo events in a JSON file and is intended for local demonstration. Production use would require authenticated ingestion, a database, access controls, trusted identity/geography data, and validation on representative real logs.”

## Start practice viva

Answer this in your own words, in 2–4 sentences: **What problem does SprayScope address, and what does the current working prototype actually do?**

