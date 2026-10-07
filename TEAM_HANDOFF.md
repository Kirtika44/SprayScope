# SprayScope Hackathon Team Handoff

This folder is the working project. Code and demo data are organized into `frontend/`, `backend/`, and `dataset/`. It contains the web app, a Node.js API, a simulated employee VPN portal, detector logic, and four ready-to-use CSV files. Divide work by file ownership so two people do not edit the same files at once.

## Start the website

1. Install Node.js 20 or newer on each teammate's computer.
2. Open PowerShell in this folder and run `npm start`.
3. Open <http://localhost:4173> for the analyst sign-in/dashboard and <http://localhost:4173/?portal=1> for the employee VPN simulation.
4. The dashboard account sign-up is a browser-only prototype. Use a test email and password; it is not production authentication.

The Node server serves both the frontend and the API. `GET /api/health` reports API status. `GET /api/events` returns simulated portal events. `POST /api/events` accepts normalized event batches; passwords are rejected and never stored. Event telemetry is local in `backend/storage/events.json`, which is generated when the portal is used and is intentionally excluded from the teammate package.

## Five-person task split

| Member | Focus | Primary files | Deliverable |
| --- | --- | --- | --- |
| Frontend 1 | Visual design, responsive layout, accessibility, shared components | `frontend/index.html`, `frontend/styles.css` | Polished desktop/mobile screens and accessible controls |
| Frontend 2 | Dashboard workflows, dataset upload/mapping, charts, incident and report interactions | `frontend/src/app.js`, `frontend/src/utils/parse.js`, `frontend/src/services/analystService.js`, `frontend/src/services/metricsService.js` | Reliable user flows from dataset load through analysis and export |
| Backend 1 | API routes, validation, persistence, limits, error responses | `backend/server.js`, API notes in this file | Documented and stable health/events API |
| Backend 2 | Identity provider setup, deployment configuration, environment variables, API integration | `frontend/src/authConfig.js`, root `package.json`, `README.md` | Reproducible deployment and real identity integration plan; do not put client secrets in browser code |
| Dataset / ML | Dataset provenance, cleaning, labels, detector evaluation, benchmark tracking | `dataset/*.csv`, `frontend/src/detectors/detectionService.js`, `dataset/scripts/train_lanl.py`, `dataset/requirements-ml.txt` | Dataset card and honest evaluation report with split and limitations |

**Coordination:** Frontend 2 and the dataset member should agree on the event schema before editing detector or metrics behavior. Both backend members should agree on API request/response fields before changing routes. Use separate branches or copies, then integrate changes into this project folder.

## Included datasets

- `dataset/demo-authentication.csv`: small unlabeled mixed sample for trying upload and analysis.
- `dataset/brute-force-only.csv`: labeled synthetic brute-force fixture.
- `dataset/password-spray-only.csv`: labeled synthetic password-spray fixture.
- `dataset/impossible-travel-only.csv`: labeled synthetic US/UK travel fixture.

The three attack-specific files are generated demo data, not real-world incident logs. Use **Dataset → Attack-specific demo datasets → Load dataset → Continue to column mapping → Confirm & Analyze**. The Metrics page can score the labeled fixtures; do not describe their metrics as real-world model performance. The dashboard detections are transparent rules, not a trained model.

## LANL research benchmark (optional)

`dataset/scripts/train_lanl.py` is separate from the live dashboard. It requires the complete authorized LANL `auth.txt.gz` and the matching `redteam.txt.gz` under `dataset/lanl/`. Do not commit or include LANL archives in the share package. The in-progress auth archive is partial and cannot produce the requested full-window benchmark yet. When the complete files are available, follow the LANL section in `README.md`; record the dataset version, temporal split, and weighted holdout metrics.

## Share package contents

`SPRAYSCOPE_HACKATHON_PACKAGE.zip` contains source code, the four CSVs, and setup notes. It excludes dependencies, generated portal telemetry, credentials, and the large/partial LANL download. Keep this project folder as the source of truth.

