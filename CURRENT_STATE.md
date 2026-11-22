# Current State (handoff)

_Last updated: 2026-11-22. Update this file at the end of every work session._

## 1. Summary

LiveAsk (real-time Q&A and polls, see `PROJECT_REQUIREMENTS.md`) is **built and verified locally**: the app (Day 1), the redesigned UI (the UI track) and Kubernetes on minikube (Day 2). **Nothing has been deployed to AWS and no AWS resources exist.** Day 3 (one billable EKS session) has not started: it needs you (see section 8).

- GitHub: https://github.com/vuongnguyen-se/liveask (public, branch `main`).
- Branch: **`feat/liveask-realtime-qa-app`** holds everything (Day 1, the UI track, Day 2; `ui/redesign` was merged into it with `--no-ff`). It was **pushed to GitHub on 2026-11-22**, and **PR #1** (https://github.com/vuongnguyen-se/liveask/pull/1) targets `main`. **GitHub CI ran on the PR and is green** (all three jobs).
- Local path: this worktree, `C:\Users\Vuong\orca\workspaces\liveask\spookfish`.
- History: the platform skeleton came from https://github.com/vuongnguyen-se/eks-platform-lab (archived).

## 2. What exists

| Path | What it is | Status |
|---|---|---|
| `app/liveask/` | FastAPI app: `rooms.py`, `questions.py`, `polls.py`, `hub.py` (WebSocket hub + one LISTEN connection per process), `landing.py` (`POST /create`, `GET /join`), `cleanup.py` (CronJob entry point), `migrate.py`, `events.py`, `security.py`, `config.py`, `db.py`, `main.py` | ✅ 95 tests pass |
| `app/liveask/static/` | The four pages: landing `/` (`index.html` + `landing.css` + `landing.js`), audience, host, screen (`app.js`, `app.css`), `tokens.css`, self-hosted fonts, `qrcode.js`, icons, and the vendored taste-skill kit in `assets/` (unmodified, checksum-guarded) | ✅ |
| `e2e/` | Browser checks (`playwright-core`, your Edge): `run.js` (19), `reconnect.js` (6), `rollout.js` (6, Kubernetes), `a11y.js` (8), `shots.js` (screenshots). See `e2e/README.md` | ✅ |
| `docker-compose.yml`, `nginx/` | Postgres + migrate + **two** app containers behind nginx on `http://localhost:8000` (`LIVEASK_PORT` to change) | ✅ |
| `k8s/base` | Namespace, ConfigMap, Deployment (migrate initContainer, probes, preStop, `maxUnavailable: 0`), Service, HPA, PDB, CronJob | ✅ verified on minikube |
| `k8s/overlays/local` | Postgres StatefulSet + PVC, throwaway secrets, ingress-nginx Ingress | ✅ verified on minikube |
| `k8s/overlays/aws` | ALB Ingress (idle timeout 3600 s, deregistration delay 30 s, `/readyz` check) | renders; **never applied** |
| `infra/terraform/` | VPC, EKS (Spot nodes), AWS Load Balancer Controller, metrics-server, ECR, RDS (db `liveask`), GitHub OIDC role, Budgets | ✅ `fmt`/`validate` pass; **never applied; `plan` not reviewed** |
| `scripts/` | `create-db-secret.sh`, `load-test.sh`, `load_test.py`, `rolling-update-demo.sh`, `vendor_taste_kit.py` | load test and rolling update verified; secret script untested (needs AWS) |
| `.github/workflows/` | `ci.yml` (ruff, pytest with Postgres, image build, terraform, render both overlays), `deploy.yml` (manual: OIDC, ECR, `kubectl apply -k`) | **never run on GitHub** |
| `docs/` | `ui/` (plan, copy, kit notes), `images/` (architecture + screenshots) | ✅ |

### Pinned versions
Terraform ≥ 1.6 (local 1.17.1) · AWS provider `>= 5.95, < 6.0` · Helm provider `~> 2.17` · modules `vpc ~> 5.21`, `eks ~> 20.37`, `iam ~> 5.55` · Kubernetes `1.35` on EKS (**unverified**: check it is in standard support before the apply; minikube here runs v1.37) · Python 3.13 · nginx 1.27 (`resolve` needs 1.27.3+) · taste-skill kit 2.5.1.

## 3. Verified (2026-11-21 to 2026-11-22, Windows 11 laptop)

- `pytest` 95 passed, `ruff` clean, `terraform fmt`/`validate` pass, both kustomize overlays render.
- Docker Compose: 19/19 browser checks, host and screen on different containers; `reconnect.js` 6/6 (8 of 8 consecutive runs after hardening); `a11y.js` 8/8 at 320 px, light and dark.
- minikube (`-p eks-lab`): 2 app pods + `postgres-0` Ready; deleting `postgres-0` kept the data; `e2e/run.js` 19/19 through ingress-nginx with the host and the screen on **different pods**; `e2e/rollout.js` 6/6 (32 of 32 questions stored during `rollout restart`, replicas never below 2, the screen reconnected to a new pod and caught up); the CronJob run by hand logged "removed 1 expired room".
- Load test, 200 WebSocket clients over 6 pods, through `minikube tunnel`: 18,400 of 18,400 deliveries; the HPA scaled **2 → 4 → 6** pods at CPU 345% of the 60% target. Latency median 298 ms, **p95 1079 ms** (target 1000 ms): the POST alone took a median 289 ms through the Windows tunnel, so this is not a clean verdict on NFR-1. Re-measure on EKS.
- UI: the skill's layout checker reports no findings at 1440, 1024, 820, 768 and 390; `copy-lint` 0 FAIL, 0 WARN; the skill's finish gate (three rounds used) ended **`GATE: OPEN`**: 21 findings in round 1, 6 in round 2, **1 open** at the end and 3 waived. Open: `ui-centre` (the hero window sits 200 px from the left and 480 px from the right of its frame, instead of centred); the skill says to stop and report it. Waived, each with a reason in `.taste-skill/waivers.json`: three `section-gaps` findings at 390 px (the kit sizes sections to whole phone screens). 29 non-blocking WARNs remain.

## 4. Not verified

- **AWS** (EKS, ALB, RDS, the deploy workflow, `create-db-secret.sh`, `terraform plan`). A real phone on mobile data. The NFR-1 latency on EKS. Vietnamese letters in the UI (Host Grotesk has no glyphs for them; the system font fills in).

## 5. Developer machine notes (Windows 11)

- Shells: PowerShell 5.1 and Git Bash. In Git Bash, set `MSYS_NO_PATHCONV=1` for commands that pass Unix paths into containers. Long Git Bash commands with big heredocs sometimes fail to parse: write the file with the editor tool instead.
- Terraform: `C:\Users\Vuong\AppData\Local\Microsoft\WinGet\Packages\Hashicorp.Terraform_Microsoft.Winget.Source_8wekyb3d8bbwe\terraform.exe` (new terminals have it on PATH).
- Docker Desktop must be running. **Port 8080 is used by another project's container (`halora-admin`)**, so LiveAsk uses 8000.
- Python tests: `docker compose up -d db`, then in `app/`: `$env:TEST_DATABASE_URL="postgresql://liveask:liveask-local-only@127.0.0.1:5432/liveask"; ..\.venv\Scripts\python -m pytest -q`. Use `127.0.0.1`, not `localhost` (async pool stalls on Windows). `python -m liveask.run` is the Windows dev server (uvicorn's default loop cannot run psycopg async there).
- minikube: `minikube start -p eks-lab --driver=docker --memory=3072 --cpus=2 --addons=metrics-server,ingress`, `minikube image build -p eks-lab -t liveask:local app`, `kubectl apply -k k8s/overlays/local`, `minikube tunnel -p eks-lab` (keep it running; app on `http://127.0.0.1`). It is **running now** (with a tunnel and a port-forward on 8088): stop with `minikube stop -p eks-lab`.
- The skill's checkers (`gate.mjs`, `consistency.mjs`) take 5 to 15 minutes and drive Chrome; do not run them alongside load tests. Run them from the repo root with `--root app/liveask`; scratch is in `.taste-skill/` (git-ignored, except `waivers.json`).
- kubectl 1.36, AWS CLI 2.35, gh CLI (signed in as `vuongnguyen-se`), Python 3.13, Node 24. No Helm CLI.
- **AWS CLI is not signed in** (`NoCredentials`). Profiles `clouddocs-dev` (SSO) and `cli` exist: `aws sso login --profile clouddocs-dev` if it is the same account.

## 6. AWS account facts

- Region `ap-southeast-1`. A **GitHub OIDC provider already exists** (from Say Coffee) → keep `create_github_oidc_provider = false`.
- Say Coffee uses a permissions boundary on Lambda roles; check whether new IAM roles need one before the apply.
- Domain `vuongdomain.click` (Say Coffee). For optional HTTPS, check that a Route 53 hosted zone exists.

## 7. Known issues and caveats

1. Teardown order: `kubectl delete -k k8s/overlays/aws` **before** `terraform destroy`, or the ALB blocks VPC deletion.
2. `deploy.yml` must not use a GitHub `environment:` unless the IAM trust policy changes (the OIDC `sub` claim would change).
3. nginx (Compose) re-resolves container names (`resolve`); a re-created container is found again after about 30 s. It does not resend a POST that timed out on a stopped container, so a client must retry (the e2e checks do).
4. In Kubernetes, a Kustomize overlay's own files do **not** inherit the base's `namespace`: the local overlay sets `namespace: liveask` itself (found when Postgres landed in `default`).
5. Anyone can `POST /api/rooms` or `POST /create` without limit (rooms expire after 24 h and are cleaned nightly). Rate-limit it before exposing the ALB for long.
6. `window` in the kit has a minimum height, so the hero card is cut by its frame; the checker's `fold-card` rule is satisfied by marking the frame `data-ui-pause-host`.

## 8. Next steps

**Continuing on another computer: start with `RESUME.md`** (install, clone, checks, minikube, the Day 3 steps).

1. **Review and decide** (you): the branch `ui/redesign` (merge into `vuongnguyen-se/spookfish`, then `main`), and whether to **push** so CI runs (I have not pushed anything).
2. **Day 3 needs you** (💰, about USD 1 per 3 to 4 hours, `SECURITY_AND_COST.md`): sign in to AWS, fill `infra/terraform/terraform.tfvars` (`budget_email`, `cluster_endpoint_public_access_cidrs` = your IP), check Kubernetes `1.35` is in standard support (`aws eks describe-cluster-versions`), review `terraform plan`, then approve `terraform apply`. Every session ends with the teardown.
3. Repeat the demos on EKS (D3-04), re-measure NFR-1, take screenshots; optional HTTPS (D3-05); teardown (D3-06); final README numbers (D3-07).
