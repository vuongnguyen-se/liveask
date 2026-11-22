# Decisions

Each decision has an ID. To change one, add a new entry that says which one it supersedes.

| ID | Decision | Why | Status |
|---|---|---|---|
| D-001 | Project is **LiveAsk** (real-time Q&A and polls), replacing the earlier CloudCost Watch plan | CloudCost Watch overlapped AWS-native tools (Cost Explorer, Budgets, Cost Optimization Hub) and needed 3–4 weeks; LiveAsk has a real reason for containers and fits ~3 days | Accepted (2026-11-21) |
| D-002 | Run on **Amazon EKS**, reusing the existing Terraform platform | Kubernetes is the learning and CV goal; the platform is already written and validated | Accepted |
| D-003 | **WebSockets in FastAPI** (not API Gateway WebSocket + Lambda) | Long-lived connections fit a container; simpler state handling; this is the "why containers" story | Accepted |
| D-004 | Cross-pod fan-out with **PostgreSQL `LISTEN/NOTIFY`**; Redis pub/sub is a roadmap item | Reuses the existing database, notifications fire only after commit, enough for hundreds of clients | Accepted |
| D-005 | **No sticky sessions** | With pub/sub every pod can serve any client; reconnects can land anywhere | Accepted |
| D-006 | **Anonymous audience** (device UUID in `localStorage`) + **secret host link** (hashed token); no accounts | Fits 3 days; Cognito is a roadmap item | Accepted |
| D-007 | **One container image** serves API, WebSocket and static pages; the same image runs `migrate` (initContainer) and `cleanup` (CronJob) | One build, one scan, fewer moving parts | Accepted |
| D-008 | Frontend is **plain HTML/CSS/JS** served by FastAPI | No build step; fastest to finish | Accepted |
| D-009 | Schema in plain SQL applied by an **initContainer under a Postgres advisory lock** (no Alembic) | Small schema; shows the initContainer pattern; safe when several pods start together | Accepted |
| D-010 | **Local Postgres as a StatefulSet + PVC** on minikube; **RDS** on AWS | Learn StatefulSets locally for free; use the managed service in the cloud | Accepted |
| D-011 | Manifests with **Kustomize** overlays `local` and `aws` | Already in place; the same base runs everywhere | Accepted |
| D-012 | Deploy with the existing **GitHub Actions OIDC** workflow (`deploy.yml`, manual); no Argo CD in the 3-day scope | Already written; Argo CD is a roadmap item | Accepted |
| D-013 | HTTP on the ALB DNS name for the demo; **HTTPS + domain optional** on day 3 | ACM + Route 53 add setup time; the README states it | Accepted |
| D-014 | AWS runs **only during one session** on day 3, then is destroyed | ≈ USD 1 per session instead of ≈ USD 190/month | Accepted |
| D-015 | LiveAsk lives in a **fresh repository `liveask`** with a clean history; the earlier repo was renamed back to `eks-platform-lab` and archived. Terraform `project` default is `liveask` | Clean history and README for the CV; the old experiments stay available read-only | Done (2026-11-21) |
| D-016 | Redesign the UI with **taste-skill 2.5.1** (`C:\Users\Vuong\Downloads\taste-skill`). The full workflow (brief, copy, plan, deal, build, check, gate) is used for the **landing page `/`** (kind: software). The three app views (audience, host, screen) take only its **design system** (tokens, type, radius, buttons, 44 px targets, contrast, motion and accessibility rules) | The skill builds company/product websites. Its hero, one-section-per-screen and dealt-moment rules do not fit a phone Q&A view or a projector screen; its tokens and accessibility rules do | Accepted (2026-11-21) |
| D-017 | **Self-host the dealt fonts** (woff2 in `app/liveask/static/fonts/`), no Google Fonts link | The skill loads fonts from Google by default: that sends visitors' IP addresses to Google (NFR-8) and fails offline, on minikube demos and behind strict networks. Same reason as the vendored QR library | Accepted (2026-11-21) |
| D-018 | **Vendor only the kit core** (about 300 KB: `system.css`, `system.js`, `layout`, `motion`, plus the few `ui`/`diagrams` pieces used) **unmodified** under `app/liveask/static/assets/` | The whole skill is 39 MB. Unmodified files can be diffed and updated; the skill forbids editing them anyway. The kit's 3 `innerHTML` uses write constant SVG icons (no user text) and are exempted by path in the guard test | Accepted (2026-11-21) |
| D-019 | The deploy workflow only **builds and pushes the image**; `scripts/deploy-from-laptop.sh` applies the manifests from the machine whose IP is allowed to reach the cluster API. Supersedes the apply step of D-012 | GitHub-hosted runners are not on the API's IP allow-list, and opening the API to `0.0.0.0/0` for a lab deploy is a wider exposure than the lab needs | Accepted (2026-11-22) |
