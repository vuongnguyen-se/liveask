# Current State (handoff)

_Last updated: 2026-11-22 (after the EKS session and its teardown). Update this file at the end of every work session._

## 1. Summary

LiveAsk (real-time Q&A and polls, see `PROJECT_REQUIREMENTS.md`) is **built and verified locally**: the app (Day 1), the redesigned UI (the UI track) and Kubernetes on minikube (Day 2). **Two EKS sessions ran on 2026-11-22 and were each destroyed afterwards: no AWS resources of this project exist now (checked after each destroy).** The results, including a phone test on mobile data that passed, are in `docs/eks-session-2026-11-22.md`. **The project was closed on 2026-11-22** (decision D-020): the optional HTTPS task and the Cost Explorer check were dropped, and nothing is running or needs maintaining.

- GitHub: https://github.com/vuongnguyen-se/liveask (public, branch `main`).
- Branch: all work was developed on `feat/liveask-realtime-qa-app` and **merged into `main` through PR #1 on 2026-11-22** (https://github.com/vuongnguyen-se/liveask/pull/1, merge commit `a221cde`). **CI is green on the PR and on `main`.** New work goes on a fresh branch from `main`.
- Local path: wherever the repository is cloned; the machine-specific paths in section 5 and the taste-skill source path in `DECISIONS.md` belong to the original Windows laptop.
- History: the platform skeleton came from https://github.com/vuongnguyen-se/eks-platform-lab (archived).

## 2. What exists

| Path | What it is | Status |
|---|---|---|
| `app/liveask/` | FastAPI app: `rooms.py`, `questions.py`, `polls.py`, `hub.py` (WebSocket hub + one LISTEN connection per process), `landing.py` (`POST /create`, `GET /join`), `ratelimit.py` (room-creation limit), `cleanup.py` (CronJob entry point), `migrate.py`, `events.py`, `security.py`, `config.py`, `db.py`, `main.py` | ✅ 95 tests pass |
| `app/liveask/static/` | The four pages: landing `/` (`index.html` + `landing.css` + `landing.js`), audience, host, screen (`app.js`, `app.css`), `tokens.css`, self-hosted fonts, `qrcode.js`, icons, and the vendored taste-skill kit in `assets/` (unmodified, checksum-guarded) | ✅ |
| `e2e/` | Browser checks (`playwright-core`, your Edge): `run.js` (19), `reconnect.js` (6), `rollout.js` (6, Kubernetes), `a11y.js` (8), `shots.js` (screenshots). See `e2e/README.md` | ✅ |
| `docker-compose.yml`, `nginx/` | Postgres + migrate + **two** app containers behind nginx on `http://localhost:8000` (`LIVEASK_PORT` to change) | ✅ |
| `k8s/base` | Namespace, ConfigMap, Deployment (migrate initContainer, probes, preStop, `maxUnavailable: 0`), Service, HPA, PDB, CronJob | ✅ verified on minikube |
| `k8s/overlays/local` | Postgres StatefulSet + PVC, throwaway secrets, ingress-nginx Ingress | ✅ verified on minikube |
| `k8s/overlays/aws` | ALB Ingress (idle timeout 3600 s, deregistration delay 30 s, `/readyz` check) | applied once on 2026-11-22 (ALB answered from the internet), then destroyed |
| `infra/terraform/` | VPC, EKS (Spot nodes), AWS Load Balancer Controller, metrics-server, ECR, RDS (db `liveask`), GitHub OIDC role, Budgets | ✅ `fmt`/`validate` pass; applied once on 2026-11-22 and destroyed (78 resources); `plan` reviewed |
| `scripts/` | `create-db-secret.sh`, `load-test.sh`, `load_test.py`, `rolling-update-demo.sh`, `vendor_taste_kit.py` | load test and rolling update verified; secret script untested (needs AWS) |
| `.github/workflows/` | `ci.yml` (ruff, pytest with Postgres, image build, terraform, render both overlays), `deploy.yml` (manual: OIDC, ECR, `kubectl apply -k`) | `ci.yml` green on PR #1 and on `main`; `deploy.yml` builds and pushes the image (ran on 2026-11-22); `deploy-from-laptop.sh` applies the manifests |
| `docs/` | `ui/` (plan, copy, kit notes), `images/` (architecture + screenshots) | ✅ |

### Pinned versions
Terraform ≥ 1.6 (local 1.17.1) · AWS provider `>= 5.95, < 6.0` · Helm provider `~> 2.17` · modules `vpc ~> 5.21`, `eks ~> 20.37`, `iam ~> 5.55` · Kubernetes `1.35` on EKS (**unverified**: check it is in standard support before the apply; minikube here runs v1.37) · Python 3.13 · nginx 1.27 (`resolve` needs 1.27.3+) · taste-skill kit 2.5.1.

## 3. Verified (2026-11-21 to 2026-11-22, Windows 11 laptop)

- `pytest` 108 passed, `ruff` clean, `terraform fmt`/`validate` pass, both kustomize overlays render.
- Docker Compose: 19/19 browser checks, host and screen on different containers; `reconnect.js` 6/6 (8 of 8 consecutive runs after hardening); `a11y.js` 8/8 at 320 px, light and dark.
- minikube (`-p eks-lab`): 2 app pods + `postgres-0` Ready; deleting `postgres-0` kept the data; `e2e/run.js` 19/19 through ingress-nginx with the host and the screen on **different pods**; `e2e/rollout.js` 6/6 (32 of 32 questions stored during `rollout restart`, replicas never below 2, the screen reconnected to a new pod and caught up); the CronJob run by hand logged "removed 1 expired room".
- Load test, 200 WebSocket clients over 6 pods, through `minikube tunnel`: 18,400 of 18,400 deliveries; the HPA scaled **2 → 4 → 6** pods at CPU 345% of the 60% target. Latency median 298 ms, **p95 1079 ms** (target 1000 ms): the POST alone took a median 289 ms through the Windows tunnel, so this is not a clean verdict on NFR-1. Re-measure on EKS.
- UI: the skill's layout checker reports no findings at 1440, 1024, 820, 768 and 390; `copy-lint` 0 FAIL, 0 WARN; the skill's finish gate (three rounds used) ended **`GATE: OPEN`**: 21 findings in round 1, 6 in round 2, **1 open** at the end and 3 waived. Open: `ui-centre` (the hero window sits 200 px from the left and 480 px from the right of its frame, instead of centred); the skill says to stop and report it. Waived, each with a reason in `.taste-skill/waivers.json`: three `section-gaps` findings at 390 px (the kit sizes sections to whole phone screens). 29 non-blocking WARNs remain.
- **EKS, 2026-11-22** (Kubernetes 1.35, 2 Spot nodes in 2 zones, RDS, ALB; destroyed afterwards): `e2e/run.js` 19/19 through the ALB with host and screen on different pods; `e2e/rollout.js` 6/6 (12 of 12 questions stored, replicas never below 2, 10 s rollout); load test with 200 clients: 22,600 of 22,600 deliveries, median 235 ms, **p95 733 ms** (target 1,000 ms: met in this one 60 s run); the HPA scaled 2 to 6 pods at CPU 624% of the 60% target; all 6 ALB targets healthy. Details and the problems found: `docs/eks-session-2026-11-22.md`.
- **EKS, session 2 (2026-11-22, clean apply of 78 resources, destroyed afterwards):** `deploy-from-laptop.sh` end to end; `e2e/run.js` 19/19; `e2e/rollout.js` 6/6 (13 of 13 questions stored, 20 s rollout); load test, 200 clients: 22,400 of 22,400 deliveries, median 261 ms, **p95 801 ms**, max 2,959 ms; HPA 2 to 6 pods at CPU 716%; 6 of 6 ALB targets healthy; **a test from real phones on mobile data passed**.

## 4. Not verified

- Screenshots of the AWS console and of the phone (the evidence is terminal output). HTTPS. The NFR-1 latency over a longer or heavier run (two 60 s runs passed, with p95 733 and 801 ms, but one delivery took 2.9 s). Vietnamese letters in the UI (Host Grotesk has no glyphs for them; the system font fills in).

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
5. Room creation is limited to 20 per hour per network address (`ROOMS_PER_HOUR_PER_IP`, in memory, so each pod counts on its own and the ceiling is that times the replicas). It trusts the last `X-Forwarded-For` entry (`TRUSTED_PROXY_HOPS=1`, right for the ALB, ingress-nginx and the Compose nginx); with no proxy in front, set it to 0 or a caller could forge the address. Not yet exercised through a real ALB: the browser checks on Compose and minikube were not re-run after this change, only `pytest`.
6. `window` in the kit has a minimum height, so the hero card is cut by its frame; the checker's `fold-card` rule is satisfied by marking the frame `data-ui-pause-host`.
7. `deploy.yml` only builds and pushes the image, then prints the next command in the run summary. The cluster API is locked to one IP (`cluster_endpoint_public_access_cidrs`), which GitHub-hosted runners are not on, so `scripts/deploy-from-laptop.sh` applies the manifests from the allowed machine (decision D-019). The script ran end to end in the second session.
8. A new GitHub OIDC trust policy needs the repository's real subject. This repository uses immutable subjects (`repo:owner@ID/name@ID`): set `github_oidc_repo_claim` in `terraform.tfvars` from `gh api repos/OWNER/NAME/actions/oidc/customization/sub`. A change to the trust policy can take a minute to take effect.
9. `ap-southeast-1` lists the Hanoi Local Zone first; the VPC uses standard zones only (`providers.tf`), because a Local Zone has no NAT gateway.
10. On this laptop `python3` is a Microsoft Store stub, so `scripts/create-db-secret.sh` needs a `python3` on PATH that points to a real Python. Edge refused the ALB address with `ERR_BLOCKED_BY_CLIENT`; Chrome worked (`BROWSER_PATH`).

## 8. Next steps

**Continuing on another computer: start with `RESUME.md`** (install, clone, checks, minikube, the Day 3 steps).

1. **Done:** the work is merged into `main` (PR #1) and CI is green there. `deploy.yml` assumes `main`, so it can now run.
2. Nothing is required. To run AWS again, follow `RESUME.md` section 4 (about USD 0.27 per hour, always end with the teardown). HTTPS and the other roadmap items are listed in the README.
3. The landing page is about 11.5 phone screens tall: a design choice, left as it is.
