# AGENTS.md

This file is for coding agents working in `/Users/shawn/Desktop/openclaw-watchboard`.

The goal is not generic repo onboarding. The goal is to preserve the current project-specific context so another agent can safely continue work without prior chat history.

## What This Project Is

OpenClaw Watchboard is a monorepo security dashboard for five current sections:

1. `OpenClaw安全治理总览`
2. `OpenClaw风险漏洞追踪`
3. `OpenClaw公网暴露监测`
4. `Skill生态后门投毒治理`
5. `OpenClaw部署安全检测`

The frontend is the user-facing deliverable. Many pages have been heavily customized for the current stakeholder and should not be “simplified back” to boilerplate Ant Design Pro layouts.

## Monorepo Layout

```text
openclaw-watchboard/
├── frontend/                 # Umi + React + Ant Design Pro
├── backend/                  # Express + TypeScript
├── shared/                   # shared TS types
├── scripts/                  # local data refresh scripts
├── data/                     # CSV inputs + SQLite db files
├── tools/openclaw-scan/      # standalone deployment security CLI
└── package.json
```

## Reality, Not The Original Template

Some older repo text still sounds generic. Do not trust generic statements over the current implementation.

Current project reality:

- SQLite files under `data/` are the actual production data source.
- The repo intentionally does **not** commit the `.db` files.
- The system is currently deployed to Tencent Cloud and Aliyun Ubuntu hosts and served via Nginx + PM2.
- The user wants practical data refresh + sync workflows, not abstract deployment docs.
- The frontend menu labels and page wording have been customized to Chinese stakeholder-facing names.

## Current High-Value Commands

### Install / Build

```bash
npm run install:all
npm run build
npm run build:frontend
npm run build:backend
npm run build:shared
```

### Database Refresh

These are important and should be preserved:

```bash
npm run refresh:databases
npm run refresh:skills-db
npm run refresh:risks-db
npm run refresh:exposure-db
```

Meaning:

- `refresh:databases`
  - runs the full analysis pipeline through `scripts/run_analysis.py`
- `refresh:skills-db`
  - rebuilds skills-related data
- `refresh:risks-db`
  - rebuilds vulnerability/risk data
- `refresh:exposure-db`
  - rebuilds exposure data only

### Remote Sync

```bash
npm run sync:databases
```

This syncs all `.db` files under `data/` to the remote server and restarts the backend.

The sync script is:

- [`scripts/sync_databases_to_server.sh`](/Users/shawn/Desktop/openclaw-watchboard/scripts/sync_databases_to_server.sh)

For Tencent, `npm run sync:databases` is equivalent to running the generic sync script with host `tencent`.

It is expected to:

- upload all local `data/*.db`
- backup previous remote DBs
- restart `pm2` app `openclaw-backend`

Important current usage:

- default target is Tencent because `REMOTE_HOST` defaults to `tencent`
- the same script can be reused for Aliyun by overriding `REMOTE_HOST=aliyun`
- when only database contents changed, prefer DB sync only and do not redeploy code or reinstall dependencies

### Deployment Security Tool

```bash
npm run scan:deployment-security
npm run package:openclaw-scan
```

`scan:deployment-security` runs:

- [`tools/openclaw-scan/scan.py`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-scan/scan.py)

`package:openclaw-scan` generates the downloadable archive exposed by the frontend:

- [`frontend/public/downloads/openclaw-scan.zip`](/Users/shawn/Desktop/openclaw-watchboard/frontend/public/downloads/openclaw-scan.zip)

## Data Sources That Matter

### Exposure Data

The exposure dataset is not just one CSV anymore. It is assembled from:

- deduplicated global instances:
  - [`data/explosure/openclaw_instances_deduped.csv`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/openclaw_instances_deduped.csv)
- liveness probing results:
  - [`data/explosure/endpoint_alive.csv`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/endpoint_alive.csv)
- version probing results:
  - [`data/explosure/endpoint_alive_configs.json`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/endpoint_alive_configs.json)
- China domestic distribution:
  - [`data/explosure/openclaw_instances_cn.csv`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/openclaw_instances_cn.csv)

The main script is:

- [`scripts/analyze_exposure_data.py`](/Users/shawn/Desktop/openclaw-watchboard/scripts/analyze_exposure_data.py)

Important current behavior:

- `health=200` is interpreted as an active instance
- `serverVersion` is written into the exposure DB
- China/domestic metadata is written into exposure records
- domestic vs overseas is shown in the frontend
- China province/city summaries are exposed by the backend for charts

### Exposure Daily Update Workflow

The current daily exposure refresh path is driven by:

- [`scripts/run_openclaw_probe_pipeline.sh`](/Users/shawn/Desktop/openclaw-watchboard/scripts/run_openclaw_probe_pipeline.sh)

Important current behavior:

- FOFA fetch now uses `search/all?page=` only, not `search/next`
- fresh FOFA raw data is cached at:
  - [`data/explosure/fofa_cache/openclaw_latest.csv`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/fofa_cache/openclaw_latest.csv)
- per-run status is written to:
  - [`data/explosure/runs/latest_status.json`](/Users/shawn/Desktop/openclaw-watchboard/data/explosure/runs/latest_status.json)
- default script behavior is now the full daily pipeline:
  - fetch FOFA
  - probe incremental candidates
  - write compatibility exposure CSV/JSON files
  - refresh `data/exposure.db`

Recommended daily commands:

```bash
# Full daily update
FOFA_KEY='your-key' /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# Fetch FOFA only and refresh local cache
FOFA_KEY='your-key' OPENCLAW_PROBE_FETCH_ONLY=1 OPENCLAW_PROBE_WRITE_LIVE=0 OPENCLAW_PROBE_REFRESH_DB=0 /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# Rebuild exposure inputs and exposure.db from local FOFA cache only
OPENCLAW_PROBE_CACHE_ONLY=1 /bin/zsh scripts/run_openclaw_probe_pipeline.sh

# Prefer local cache first, fetch remotely only if cache is missing
FOFA_KEY='your-key' OPENCLAW_PROBE_CACHE_FIRST=1 /bin/zsh scripts/run_openclaw_probe_pipeline.sh
```

Useful performance override for large refreshes:

```bash
FOFA_KEY='your-key' OPENCLAW_PROBE_CONCURRENCY=256 OPENCLAW_PROBE_TIMEOUT=3 /bin/zsh scripts/run_openclaw_probe_pipeline.sh
```

If a full runtime refresh is too slow, a practical fallback is:

1. export the current `probe_instances` state back into the compatibility CSV/JSON inputs
2. run `npm run refresh:exposure-db`

This is acceptable when the user primarily wants the latest cached FOFA/probe state reflected in the frontend DB without waiting for another very large full active-state re-probe.

### Risk / Vulnerability Data

The risks DB is built from the vulnerability CSV workflow.

Important warning:

- [`scripts/setup_database.py`](/Users/shawn/Desktop/openclaw-watchboard/scripts/setup_database.py) was previously dropping vulnerability tables and caused the risks UI to go empty.
- That behavior has already been fixed and should not be reintroduced.

If Dashboard or Risks pages suddenly show no vulnerability data, check:

1. `data/risks.db`
2. whether `refresh:risks-db` actually completed
3. whether `setup_database.py` was modified incorrectly

### Skills Data

Skills data still contains mock-like detail semantics in places, but the current UI expects:

- list filtering on safe / suspicious / malicious sections
- less repetitive label clutter
- ordering that does not cluster identical causes together

Relevant files:

- [`frontend/src/pages/Skills/index.tsx`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/pages/Skills/index.tsx)
- [`backend/src/services/SkillDataService.ts`](/Users/shawn/Desktop/openclaw-watchboard/backend/src/services/SkillDataService.ts)

## Frontend Routes And Menu Names

These are stakeholder-approved current menu labels:

- `menu.dashboard`: `OpenClaw安全治理总览`
- `menu.risks`: `OpenClaw风险漏洞追踪`
- `menu.risks.top10`: `OpenClaw Top 10风险`
- `menu.risks.vulnerabilities`: `OpenClaw已披露漏洞`
- `menu.exposure`: `OpenClaw公网暴露监测`
- `menu.skills`: `Skill生态后门投毒治理`
- `menu.deploymentSecurity`: `OpenClaw部署安全检测`

Relevant files:

- [`frontend/src/locales/zh-CN/menu.ts`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/locales/zh-CN/menu.ts)
- [`frontend/config/routes.ts`](/Users/shawn/Desktop/openclaw-watchboard/frontend/config/routes.ts)

Important route:

- `/tools` is the current route for the deployment security page

Do not change the route back to `/deployment-security` unless explicitly asked.

## Page-Specific Context

### Exposure Page

Relevant files:

- [`frontend/src/pages/Exposure/index.tsx`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/pages/Exposure/index.tsx)
- [`backend/src/services/ExposureDatabaseService.ts`](/Users/shawn/Desktop/openclaw-watchboard/backend/src/services/ExposureDatabaseService.ts)
- [`frontend/src/services/exposureApi.ts`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/services/exposureApi.ts)

Current state expected by the user:

- top summary cards are custom and not template defaults
- “high-risk exposures” was replaced with active-instance-oriented metrics
- China vs overseas exposure is explicit
- service details include domestic/overseas labeling and domestic location columns
- “risk score by region” was removed
- “risk severity” overuse was intentionally removed from exposure detail UX
- global map and China map use different color scales
- China map supports zoom / drag and Chinese labels in tooltips
- province top 5 replaced the old risk distribution chart
- evolution trend chart exists and is placed before the global distribution chart
- download / deployment tooling page exists separately under `/tools`

Do not casually reintroduce:

- severity-heavy exposure framing
- region risk scores
- duplicated province/city labels like `北京 / 北京`

### Skills Page

Relevant file:

- [`frontend/src/pages/Skills/index.tsx`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/pages/Skills/index.tsx)

Current expectations:

- suspicious and malicious tabs have filter controls too
- repetitive mock-like warning boxes were intentionally removed
- suspicious list should not show random-looking badge counts
- ordering should not group identical issues too tightly

### Deployment Security Page

Relevant files:

- [`frontend/src/pages/DeploymentSecurity/index.tsx`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/pages/DeploymentSecurity/index.tsx)
- [`frontend/src/pages/DeploymentSecurity/sampleReport.json`](/Users/shawn/Desktop/openclaw-watchboard/frontend/src/pages/DeploymentSecurity/sampleReport.json)
- [`tools/openclaw-scan/`](/Users/shawn/Desktop/openclaw-watchboard/tools/openclaw-scan)

Current expectations:

- this page is stakeholder-facing, not an internal engineering doc page
- it offers a direct download link to `/downloads/openclaw-scan.zip`
- wording should stay concise and polished
- the route is `/tools`

## Deployment Context

The current production-like deployment pattern is:

- Tencent Cloud Ubuntu host
- Aliyun Ubuntu host
- Node + PM2 for backend
- Nginx serving frontend static files
- `/api` proxied to backend

The PM2 app name is:

- `openclaw-backend`

The application has been both deployed on Tencent and Aliyun under:

- `/var/www/openclaw-watchboard`

Nginx host routing matters.

Important verification detail:

- direct `curl http://127.0.0.1/...` on the server may hit the default Nginx site
- for site verification use the correct virtual host header, for example:

```bash
curl -I -H "Host: clawsec.com.cn" http://127.0.0.1/tools
curl -I -H "Host: clawsec.com.cn" http://127.0.0.1/downloads/openclaw-scan.zip
```

If `/tools` or the download file seem missing but build succeeded, verify the request is reaching the intended Nginx vhost before assuming deployment failed.

## How Deployments Were Recently Done

The current working deployment approach used in this repo:

1. create a tarball locally
2. upload it to the target server
3. extract into `/var/www/openclaw-watchboard`
4. only if dependencies changed or the target host is not already in a good state, run `npm install`
5. build what is actually needed
6. restart `pm2 restart openclaw-backend`
7. verify health and key routes

Practical deployment rules learned from recent remote pushes:

- do not assume every code push needs a full remote `npm install`
- if only application code changed and remote `node_modules` is already healthy, prefer just syncing code, rebuilding, and restarting pm2
- if only `data/*.db` changed, prefer `npm run sync:databases` and do not redeploy code
- avoid packaging or copying any local `node_modules` to Linux servers
- for cross-platform safety, deployment archives should exclude all `node_modules` and all build outputs
- if remote dependencies are already valid, reinstalling them is unnecessary risk and slows deployment
- reinstall dependencies only when one of these is true:
  - `package.json` or lockfile changed
  - native module bindings are broken
  - the remote `node_modules` tree is missing/corrupted
  - the target host is being initialized or normalized

Important Tencent-specific lesson:

- building the frontend directly on Tencent may fail with `mako` / Rust bundler runtime issues such as `Bus error (core dumped)`
- if backend build is fine but Tencent frontend build fails at `max build`, build `frontend/dist` locally and upload that static output instead of repeatedly forcing remote frontend builds

Important native dependency lesson:

- backend depends on `sqlite3`
- if Tencent backend starts failing with `Could not locate the bindings file`, the issue is usually `sqlite3` native bindings, not the application code
- Tencent needed `build-essential` installed before `npm rebuild sqlite3 --build-from-source` could succeed
- after rebuilding `sqlite3`, restart pm2 and recheck `/health`

Safe default deployment order:

1. Decide whether this is a DB-only change, code-only change, or dependency-changing release.
2. For DB-only change: sync only `data/*.db`.
3. For code-only change with healthy remote deps: upload code, rebuild required targets, restart pm2.
4. For dependency-changing release: upload code, run remote `npm install`, rebuild, restart pm2.
5. Verify backend health first, then Nginx routes with the correct `Host` header.

The backend health check:

```bash
curl http://127.0.0.1:3005/health
```

Common API checks:

```bash
curl http://127.0.0.1:3005/api/risks/vulnerabilities
curl http://127.0.0.1:3005/api/exposure/overview
```

## Editing Guidance For Future Agents

- Prefer preserving the current UX decisions. Many were requested explicitly by the stakeholder.
- Do not revert “odd” page choices unless they are clearly accidental. Several were deliberate.
- If changing data scripts, verify they do not wipe existing DB tables unintentionally.
- If changing exposure or skills filtering/order, test both backend behavior and visible frontend results.
- After frontend changes, always run:

```bash
npm run build:frontend
```

- After backend changes, run:

```bash
npm run build:backend
```

## If You Need To Re-Sync Production

Typical sequence:

```bash
npm run refresh:databases
npm run sync:databases
```

For code changes, rebuild and deploy the repo contents to the Tencent host, then validate:

- `/health`
- `/tools`
- `/downloads/openclaw-scan.zip`
- key API routes used by Dashboard / Exposure / Risks

If both Tencent and Aliyun need the same release:

- keep both servers on `/var/www/openclaw-watchboard`
- prefer the same archive layout and pm2 app name on both servers
- validate each host independently; do not assume one host's successful build proves the other host is healthy

## In Short

If a future agent has to continue work quickly, the highest-risk misunderstandings are:

1. assuming the repo docs are still generic and current
2. not realizing data refresh + DB sync scripts are the real operating model
3. accidentally breaking the custom Exposure page behavior
4. forgetting that `/tools` and the download ZIP are part of the current public-facing site
5. verifying Nginx without the correct `Host` header and misdiagnosing a 404
