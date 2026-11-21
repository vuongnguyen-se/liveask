# LiveAsk Task Board (3-day plan)

The single place to track progress. Tick a box only when its **Done when** check has really passed, and add the date. Decisions `D-xxx` are in `DECISIONS.md`.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[-]` dropped (say why) · 💰 creates billable AWS resources (ask first) · 🧹 includes teardown

## Progress overview

| Day | Goal | Status |
|---|---|---|
| 0 | Platform skeleton (Terraform, K8s, CI) carried over into the fresh `liveask` repo | ✅ Done (2026-11-21) |
| 1 | The app: rooms, questions, votes, polls, real-time across pods; runs in Docker Compose | In progress (D1-01 to D1-03 done) |
| 2 | Kubernetes on minikube: all objects, cross-pod real time, zero-downtime update, HPA demo | Not started |
| 3 | One AWS session on EKS, screenshots, teardown; README and diagram final | Not started |

---

## Day 1: The app (local, USD 0)

- [x] **D1-01** (2026-11-21) Restructure `app/` into the `liveask` package (see `ARCHITECTURE.md` §6). `config.py` (env vars), `db.py` (psycopg async pool), `schema.sql`, `migrate.py` with `pg_advisory_lock`. Remove the notes endpoints but keep `/healthz` and the `/burn` load helper.
  - Done when: `python -m liveask.migrate` runs twice against Compose Postgres without errors; tests pass.
- [x] **D1-02** (2026-11-21) Rooms: `POST /api/rooms`, `GET /api/rooms/{code}`, `POST /api/rooms/{code}/close`; code generator; host token hashing; tests.
  - Done when: tests cover create, get, wrong token → 403, and that the token is not stored in plain text.
- [x] **D1-03** (2026-11-21) Questions and votes: create (rate limit), toggle vote (counter updated in the same transaction), host moderation; tests.
  - Done when: tests cover one-vote-per-device, unvote, hidden questions not visible to the audience, and 429.
- [ ] **D1-04** Polls: create, open/close, vote, change vote, counts; tests.
- [ ] **D1-05** Real time: `hub.py` with one LISTEN connection per process; every write calls `pg_notify` in its transaction; `/ws/rooms/{code}` with hello/ping/pong; `/readyz` checks the DB and the LISTEN connection.
  - Done when: an integration test (or script) starts **two app processes** on different ports against the same Postgres; a question posted to process A arrives on a WebSocket connected to process B.
- [ ] **D1-06** Pages: `/`, `/r/{code}`, `/host/{code}#t=…`, `/screen/{code}` in plain HTML/CSS/JS; device UUID in `localStorage`; reconnect with backoff + resync; QR code on the screen view (small JS library vendored into `static/`, no CDN); show "connected to pod …".
  - Done when: in a browser, three tabs (audience, host, screen) update each other live.
- [ ] **D1-07** `docker-compose.yml`: postgres + migrate + **two** api containers behind a tiny nginx (round robin) to mimic two pods.
  - Done when: `docker compose up --build`, open the site through nginx, and tabs on different containers update each other.

## Day 2: Kubernetes on minikube (USD 0)

- [ ] **D2-01** `k8s/base`: rename everything from `notes` to `liveask`; ConfigMap; Deployment with **initContainer `migrate`**, probes, **preStop sleep 10**, `terminationGracePeriodSeconds: 45`, `maxUnavailable: 0`; Service; HPA; PDB; **CronJob `liveask-cleanup`** (`concurrencyPolicy: Forbid`).
- [ ] **D2-02** `k8s/overlays/local`: **Postgres StatefulSet** + headless Service + `volumeClaimTemplates` (PVC); `secretGenerator` for local creds; Ingress for the minikube `ingress` addon.
  - Done when: `kubectl apply -k k8s/overlays/local` gives 2 Ready app pods and 1 Ready postgres pod; deleting the postgres pod keeps the data (PVC).
- [ ] **D2-03** Cross-pod demo: through the Ingress, open tabs until they show **different pod names**; real time still works between them.
- [ ] **D2-04** Zero-downtime demo (`scripts/rolling-update-demo.sh`): keep the screen open, run `kubectl rollout restart deployment/liveask`; clients reconnect automatically, nothing is lost. Record a short GIF or screenshots.
- [ ] **D2-05** Load test (`scripts/load_test.py`): open N WebSockets + post questions/votes; watch `kubectl get hpa,pods -w` scale up. Save a screenshot.
- [ ] **D2-06** Run the CronJob manually (`kubectl create job --from=cronjob/liveask-cleanup …`) with an expired test room; it gets deleted.
- [ ] **D2-07** Update CI: tests for the new package, image build, kustomize render for both overlays. Update `scripts/create-db-secret.sh` (secret `liveask-db`, namespace `liveask`, db `liveask`).
  - Done when: CI green.

## Day 3: AWS session on EKS 💰 🧹 (≈ 3–4 h, ≈ USD 1)

Before starting: `aws login` (or SSO profile), `terraform.tfvars` filled in, check `kubernetes_version` is in standard support (`aws eks describe-cluster-versions`).

- [ ] **D3-01** Terraform edits (no apply yet): RDS `db_name`/`username` → `liveask`, access entry namespace → `liveask`; `terraform fmt`/`validate`; review `terraform plan`.
- [ ] **D3-02** Ingress for ALB: `alb.ingress.kubernetes.io/load-balancer-attributes: idle_timeout.timeout_seconds=3600`, `target-group-attributes: deregistration_delay.timeout_seconds=30`, health check `/readyz`.
- [ ] **D3-03** 💰 `terraform apply`; `aws eks update-kubeconfig`; `scripts/create-db-secret.sh`; set GitHub variables; run **Deploy to EKS**.
  - Done when: the ALB URL works from a phone; two phones on mobile data plus a laptop update live.
- [ ] **D3-04** Repeat the D2-03/04/05 demos on EKS; screenshots of pods spread across AZs (`kubectl get pods -o wide`), HPA scaling, the ALB target group, and the app on a phone.
- [ ] **D3-05** (Optional, if time) HTTPS: ACM certificate + Route 53 record `ask.vuongdomain.click`, Ingress `certificate-arn` + `ssl-redirect`.
- [ ] **D3-06** 🧹 Teardown per `SECURITY_AND_COST.md` §3. Next day: confirm in Cost Explorer.
- [ ] **D3-07** Final README: what it is, screenshots/GIF, architecture diagram, the "why containers" and "multi-pod fan-out" explanations, K8s objects table, how to run locally, real cost of the session, roadmap, CV bullet points.

## Roadmap (not in the 3 days; list it in the README)

HTTPS + custom domain (if not done), Cognito for presenters, NetworkPolicies (minikube `--cni=calico`), Argo CD, Prometheus + Grafana and autoscaling on connection count (KEDA), Redis pub/sub comparison, staging/prod split, WAF.
